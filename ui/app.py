"""アプリ本体。after() ループと各パネルの配線だけを持つ。

判断ロジックは core.MonitorService にあり、ここには置かない。
"""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk

from core.config import AppConfig, load_config, save_config
from core.discovery import DataRootScanner
from core.history import ShotHistory
from core.models import Session
from core.monitor import (
    STATUS_ERROR,
    STATUS_IDLE,
    STATUS_NODATA,
    STATUS_NOROOT,
    STATUS_RUNNING,
    MonitorService,
)
from core.stats import window_stats

from . import theme
from .chart import ShotChart
from .control_bar import ControlBar
from .header_panel import HeaderPanel
from .shot_table import ShotTable
from .widgets import StatusStrip

log = logging.getLogger(__name__)

TITLE = "shot-monitor — MPS08B ピーク値トレンド"

#: 状態帯の見え方。本体アプリの「モニタモード」帯の色彩言語に合わせる。
_STATUS_STYLE = {
    STATUS_RUNNING: ("監視中", theme.ACCENT_BAR, "#00323C"),
    STATUS_IDLE: ("停止中", "#FFD54F", "#4A3800"),
    STATUS_NODATA: ("データなし", "#D8DEE9", "#3A4552"),
    STATUS_NOROOT: ("データフォルダ未設定", theme.ALERT_BAR, "#FFFFFF"),
    STATUS_ERROR: ("読み取り異常", theme.ALERT_BAR, "#FFFFFF"),
}


class MonitorApp:
    def __init__(self, root: tk.Tk, cfg: AppConfig | None = None) -> None:
        self.root = root
        self.cfg = cfg or load_config()

        self.history = ShotHistory()
        self.scanner = DataRootScanner(Path(self.cfg.mms_data_dir or "."))
        self.service = MonitorService(self.scanner, self.history)

        self._after_id: str | None = None
        self._ticks = 0
        self._sessions: list[Session] = []

        root.title(TITLE)
        root.configure(background=theme.BG)
        root.geometry(self.cfg.geometry)
        root.minsize(1000, 700)

        style = ttk.Style(root)
        theme.apply_ttk_theme(style)

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
        filemenu.add_command(label="MMS_DATA フォルダを選ぶ...", command=self.choose_data_dir)
        filemenu.add_separator()
        filemenu.add_command(label="終了", command=self.on_close)
        menubar.add_cascade(label="ファイル", menu=filemenu)
        self.root.config(menu=menubar)

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
        )
        self.controls.pack(fill="x")

        body = ttk.Frame(self.root, style="TFrame")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        # 先に下段（テーブル）の領域を確保してから、残り全部をグラフに与える。
        # 逆順に pack すると、ウィンドウが縮んだときにテーブルが先に切られる。
        self.table = ShotTable(body)
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
        chosen = filedialog.askdirectory(
            title="MPS08B の MMS_DATA フォルダを選んでください", initialdir=initial
        )
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
            self._set_status(STATUS_NOROOT, "ファイル > MMS_DATA フォルダを選ぶ")
            return
        result = self.service.poll(now=datetime.now(), rescan=rescan)
        if result.session_changed:
            self._refresh_sessions()
        if result.new_shots or result.session_changed or result.reloaded:
            self._refresh_views()
        self._set_status(result.status, result.message)

    def _set_status(self, status: str, message: str) -> None:
        text, color, fg = _STATUS_STYLE.get(status, ("", theme.ACCENT_BAR, "#00323C"))
        self.status.set_state(text, message, color, fg)

    def _refresh_views(self) -> None:
        shots = self.history.tail(self.cfg.window_size)
        stats = [
            window_stats([s.ch01 for s in shots]),
            window_stats([s.ch02 for s in shots]),
        ]
        self.header.set_data(shots, stats, self.cfg.window_size, len(self.history))
        self.chart.set_data(shots, self.cfg.chart_kind)
        self.table.update_rows(shots, self.cfg.composite_mode)

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

    def _on_composite(self, mode) -> None:
        self.cfg.composite_mode = str(mode)
        save_config(self.cfg)
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
