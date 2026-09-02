"""最新ショットの値と、表示中 N 件の統計を出すヘッダ。

このアプリの存在理由がここに集約されている。純正トレンドビューアは値を
クリックしないと読めないので、常時大きく出す。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.models import Session, Shot
from core.monitor import STATUS_ERROR, STATUS_IDLE, STATUS_NODATA, STATUS_NOROOT, STATUS_RUNNING
from core.stats import ChannelStats

from . import theme

_STATUS_TEXT = {
    STATUS_RUNNING: ("● 監視中", theme.OK),
    STATUS_IDLE: ("● 停止中", theme.WARN),
    STATUS_NODATA: ("○ データなし", theme.DIM),
    STATUS_NOROOT: ("● フォルダ未設定", theme.ERR),
    STATUS_ERROR: ("● 読み取り異常", theme.ERR),
}


class HeaderPanel(ttk.Frame):
    def __init__(self, parent: tk.Misc, on_session_change) -> None:
        super().__init__(parent, style="Panel.TFrame", padding=(14, 10))
        self._on_session_change = on_session_change
        self._sessions: list[Session] = []
        self._suppress = False

        top = ttk.Frame(self, style="Panel.TFrame")
        top.pack(fill="x")

        self.shot_label = ttk.Label(top, text="Shot ----", style="Panel.TLabel", font=theme.F_BIG)
        self.shot_label.pack(side="left")

        self.time_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.time_label.pack(side="left", padx=(12, 0))

        self.session_box = ttk.Combobox(top, state="readonly", width=30, font=theme.F_SMALL)
        self.session_box.pack(side="right")
        self.session_box.bind("<<ComboboxSelected>>", self._session_selected)

        self.status_label = ttk.Label(top, text="", style="Panel.TLabel", font=theme.F_SMALL)
        self.status_label.pack(side="right", padx=(0, 14))

        values = ttk.Frame(self, style="Panel.TFrame")
        values.pack(fill="x", pady=(8, 0))
        self._ch_value: list[ttk.Label] = []
        self._ch_stats: list[ttk.Label] = []
        for name, color in zip(theme.CH_NAMES, theme.CH_COLORS, strict=True):
            col = ttk.Frame(values, style="Panel.TFrame")
            col.pack(side="left", padx=(0, 40))
            ttk.Label(col, text=f"{name}  [MPa]", style="Panel.TLabel", foreground=color).pack(
                anchor="w"
            )
            v = ttk.Label(
                col, text="--.-", style="Panel.TLabel", font=theme.F_HUGE, foreground=color
            )
            v.pack(anchor="w")
            s = ttk.Label(col, text="", style="Stat.TLabel")
            s.pack(anchor="w")
            self._ch_value.append(v)
            self._ch_stats.append(s)

        self.window_label = ttk.Label(self, text="", style="Muted.TLabel")
        self.window_label.pack(anchor="w", pady=(4, 0))

    # ------------------------------------------------------------------ update

    def set_latest(self, shot: Shot | None) -> None:
        if shot is None:
            self.shot_label.config(text="Shot ----")
            self.time_label.config(text="")
            for label in self._ch_value:
                label.config(text="--.-")
            return
        self.shot_label.config(text=f"Shot {shot.shot_no}")
        self.time_label.config(text=shot.dt.strftime("%Y/%m/%d %H:%M:%S"))
        self._ch_value[0].config(text=f"{shot.ch01:.1f}")
        self._ch_value[1].config(text=f"{shot.ch02:.1f}")

    def set_stats(self, window_size: int, stats: list[ChannelStats]) -> None:
        shown = stats[0].n if stats else 0
        self.window_label.config(text=f"直近 {window_size} 件指定 / 表示 {shown} 件")
        for label, st in zip(self._ch_stats, stats, strict=True):
            if st.empty:
                label.config(text="")
            else:
                label.config(
                    text=f"max {st.max:.2f}  min {st.min:.2f}  avg {st.avg:.2f}  σ {st.sd:.2f}"
                )

    def set_status(self, status: str, message: str) -> None:
        text, color = _STATUS_TEXT.get(status, ("", theme.MUTED))
        if message:
            text = f"{text}  {message}"
        self.status_label.config(text=text, foreground=color)

    # ---------------------------------------------------------------- sessions

    def set_sessions(self, sessions: list[Session], current: Session | None) -> None:
        self._sessions = sessions
        labels = [s.label for s in sessions]
        self._suppress = True
        self.session_box.config(values=labels)
        if current is not None:
            for i, s in enumerate(sessions):
                if s.csv == current.csv:
                    self.session_box.current(i)
                    break
        self._suppress = False

    def _session_selected(self, _event) -> None:
        if self._suppress:
            return
        i = self.session_box.current()
        if 0 <= i < len(self._sessions):
            # 先頭 (= 最新) を選び直したら自動追従に戻す
            self._on_session_change(self._sessions[i], i == 0)
