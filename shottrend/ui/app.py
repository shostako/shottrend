"""アプリ本体。after() ループと各パネルの配線だけを持つ。

判断ロジックは shottrend.core.monitor.MonitorService にあり、ここには置かない。
"""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from shottrend.core.config import AppConfig, config_path, load_config, save_config
from shottrend.core.discovery import DataRootScanner
from shottrend.core.history import ShotHistory
from shottrend.core.models import Session
from shottrend.core.monitor import (
    STATUS_ERROR,
    STATUS_IDLE,
    STATUS_NODATA,
    STATUS_NOROOT,
    STATUS_RUNNING,
    MonitorService,
)
from shottrend.core.stats import window_stats
from shottrend.core.version import __version__
from shottrend.i18n import current as current_language
from shottrend.i18n import detect_language, set_language, t

from . import theme
from .chart import ShotChart
from .control_bar import ControlBar
from .header_panel import HeaderPanel
from .shot_table import ShotTable
from .widgets import StatusStrip

log = logging.getLogger(__name__)

#: 状態帯の色。本体アプリの「モニタモード」帯の色彩言語に合わせる。
#: 文言は言語で変わるので持たない（`status.<状態>` を引く）。
_STATUS_COLORS = {
    STATUS_RUNNING: (theme.ACCENT_BAR, "#00323C"),
    STATUS_IDLE: ("#FFD54F", "#4A3800"),
    STATUS_NODATA: ("#D8DEE9", "#3A4552"),
    STATUS_NOROOT: (theme.ALERT_BAR, "#FFFFFF"),
    STATUS_ERROR: (theme.ALERT_BAR, "#FFFFFF"),
}


class MonitorApp:
    def __init__(self, root: tk.Tk, cfg: AppConfig | None = None) -> None:
        self.root = root
        self.cfg = cfg or load_config()
        # 設定が空 (= 自動) なら OS の表示言語から推測する。翻訳表の無い言語に
        # なっても set_language が既定へ倒すので、ここで検査はしない
        set_language(self.cfg.language or detect_language())

        self.history = ShotHistory()
        self.scanner = DataRootScanner(Path(self.cfg.mms_data_dir or "."))
        self.service = MonitorService(self.scanner, self.history)

        self._after_id: str | None = None
        self._ticks = 0
        self._sessions: list[Session] = []

        root.title(t("app.title"))
        root.configure(background=theme.BG)
        root.geometry(self.cfg.geometry)
        root.minsize(1000, 700)

        # 言語を切り替えるとフォントが変わり、ttk のスタイルを作り直す必要が
        # あるので参照を持っておく（ttk はスタイル生成時にフォントを取り込む）
        self.style = ttk.Style(root)
        # フォントの解決はスタイルを組む前。ここを飛ばすと F_* が既定のまま
        # 固定され、ウィジェットの幅も「実際には使われないフォント」で測られる
        theme.set_language_font(current_language(), tkfont.families(root))
        theme.apply_ttk_theme(self.style)

        self._build_menu()
        self._build_layout()

        root.protocol("WM_DELETE_WINDOW", self.on_close)

        if not self._data_root_valid():
            self.root.after(200, self.choose_data_dir)
        else:
            self._bootstrap()
        self._schedule()

    # ------------------------------------------------------------------ layout

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root, tearoff=0)
        filemenu = tk.Menu(menubar, tearoff=0)
        # 末尾の "..." は「押すとダイアログが出る」を示す UI の記号なので訳さない
        filemenu.add_command(label=t("menu.choose_dir") + "...", command=self.choose_data_dir)
        filemenu.add_separator()
        filemenu.add_command(label=t("menu.about"), command=self.show_about)
        filemenu.add_separator()
        filemenu.add_command(label=t("menu.quit"), command=self.on_close)
        menubar.add_cascade(label=t("menu.file"), menu=filemenu)
        self.root.config(menu=menubar)

    def show_about(self) -> None:
        messagebox.showinfo(
            "ShotTrend",
            f"ShotTrend {__version__}\n"
            + t("about.subtitle")
            + "\n\n"
            + t("about.config", path=config_path())
            + "\n"
            + t("about.data", path=self.cfg.mms_data_dir or t("about.unset")),
            parent=self.root,
        )

    def _build_layout(self) -> None:
        # 本体アプリの上部モード帯に相当。離れた位置からでも状態が読める
        self.status = StatusStrip(self.root)
        self.status.pack(fill="x")

        self.header = HeaderPanel(self.root, on_session_change=self._on_session_change)
        self.header.pack(fill="x")

        self.controls = ControlBar(
            self.root,
            self.cfg,
            on_window=self._on_window_size,
            on_kind=self._on_kind,
            on_composite=self._on_composite,
            on_delta=self._on_delta,
            on_metric=self._on_metric,
        )
        self.controls.pack(fill="x")

        body = ttk.Frame(self.root, style="TFrame")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        # 先に下段（テーブル）の領域を確保してから、残り全部をグラフに与える。
        # 逆順に pack すると、ウィンドウが縮んだときにテーブルが先に切られる。
        self.table = ShotTable(body)
        self.table.set_show_delta(self.cfg.show_delta_columns)
        self.table.pack(side="bottom", fill="x", expand=False, pady=(10, 0))

        # 黒いグラフが明るい地に浮くので、細い縁で囲んでカードに見せる
        chart_frame = tk.Frame(body, background=theme.PANEL_EDGE, bd=0, highlightthickness=0)
        chart_frame.pack(side="top", fill="both", expand=True)
        self.chart = ShotChart(chart_frame)
        self.chart.pack(fill="both", expand=True, padx=1, pady=1)

    # ------------------------------------------------------------------- data

    def _data_root_valid(self) -> bool:
        return bool(self.cfg.mms_data_dir) and Path(self.cfg.mms_data_dir).is_dir()

    def _bootstrap(self) -> None:
        self.scanner = DataRootScanner(Path(self.cfg.mms_data_dir))
        self.service = MonitorService(self.scanner, self.history)
        self.history.clear()
        self._refresh_sessions()
        self._tick_once(rescan=True)

    def choose_data_dir(self) -> None:
        initial = self.cfg.mms_data_dir or str(Path.home())
        chosen = filedialog.askdirectory(title=t("dialog.choose_dir_title"), initialdir=initial)
        if not chosen:
            return
        self.cfg.mms_data_dir = chosen
        save_config(self.cfg)
        self._bootstrap()

    def _refresh_sessions(self) -> None:
        self._sessions = self.scanner.list_sessions()
        self.header.set_sessions(self._sessions, self.service.session)

    # ------------------------------------------------------------------- loop

    def _schedule(self) -> None:
        # 多重登録を防ぐ。既存の予約は必ず消してから入れ直す。
        self._cancel_scheduled()
        self._after_id = self.root.after(self.cfg.poll_interval_ms, self._tick)

    def _cancel_scheduled(self) -> None:
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _tick(self) -> None:
        try:
            self._tick_once(rescan=(self._ticks % self.cfg.session_rescan_ticks == 0))
        except Exception:
            # 1 回の失敗でループを止めない。常駐アプリで黙って死ぬのが最悪。
            log.exception("tick failed")
        finally:
            self._ticks += 1
            self._schedule()

    def _tick_once(self, *, rescan: bool) -> None:
        if not self._data_root_valid():
            # 案内文はメニューの訳語から組み立てる。固定文にするとメニューだけ
            # 訳を直したときに案内が古いまま取り残される
            self._set_status(
                STATUS_NOROOT,
                "msg.hint_choose_dir",
                {"menu": t("menu.file"), "item": t("menu.choose_dir")},
            )
            return
        result = self.service.poll(now=datetime.now(), rescan=rescan)
        if result.session_changed:
            self._refresh_sessions()
        if result.new_shots or result.session_changed or result.reloaded:
            self._refresh_views()
        self._set_status(result.status, result.message_key, result.message_params)

    def _set_status(
        self, status: str, message_key: str = "", message_params: dict | None = None
    ) -> None:
        if status in _STATUS_COLORS:
            color, fg = _STATUS_COLORS[status]
            text = t(f"status.{status}")
        else:
            color, fg, text = theme.ACCENT_BAR, "#00323C", ""
        self.status.set_state(text, t(message_key, **(message_params or {})), color, fg)

    def _refresh_views(self) -> None:
        shots = self.history.tail(self.cfg.window_size)
        # 実際にセンサが繋がっている ch だけを扱う。MPS08B は未接続 ch も
        # 0.00 で書き続けるので、列の有無では判別できない。
        channels = self.history.used_channels()
        metric = self.cfg.metric
        stats = [window_stats([s.value(metric, c) for s in shots]) for c in channels]

        self.header.set_data(
            shots, channels, stats, self.cfg.composite_mode, metric, len(self.history)
        )
        self.chart.set_data(shots, channels, self.cfg.chart_kind, metric)
        self.table.set_channels(channels)
        self.table.update_rows(shots, self.cfg.composite_mode, metric)

    # --------------------------------------------------------------- handlers

    def _on_session_change(self, session: Session, follow: bool) -> None:
        self.service.select_session(session, follow=follow)
        self._tick_once(rescan=False)
        self._refresh_views()

    def _on_window_size(self, size) -> None:
        self.cfg.window_size = int(size)
        save_config(self.cfg)
        self._refresh_views()

    def _on_kind(self, kind) -> None:
        self.cfg.chart_kind = str(kind)
        save_config(self.cfg)
        self._refresh_views()

    def _on_metric(self, key) -> None:
        self.cfg.metric = str(key)
        save_config(self.cfg)
        self._refresh_views()

    def _on_composite(self, mode) -> None:
        self.cfg.composite_mode = str(mode)
        save_config(self.cfg)
        self._refresh_views()

    def _on_delta(self, show) -> None:
        self.cfg.show_delta_columns = bool(show)
        save_config(self.cfg)
        self.table.set_show_delta(self.cfg.show_delta_columns)
        # 列を組み替えたら行も入れ直す。片方だけだと値が 1 列ずれる
        self._refresh_views()

    # ------------------------------------------------------------------ close

    def on_close(self) -> None:
        self._cancel_scheduled()
        try:
            self.cfg.geometry = self.root.winfo_geometry()
            save_config(self.cfg)
        except tk.TclError:
            pass
        self.root.destroy()
