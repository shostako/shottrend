"""最新ショットの値と統計を出すヘッダ。

このアプリの存在理由がここに集約されている。純正トレンドビューアは値を
クリックしないと読めないので、常時大きく出す。加えて「前ショットからどう
動いたか」を ▲▼ で見せる（純正にはこれが無い）。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.models import Session, Shot
from core.stats import ChannelStats

from . import theme
from .widgets import ChannelCard, InfoCard


class HeaderPanel(ttk.Frame):
    def __init__(self, parent: tk.Misc, on_session_change) -> None:
        super().__init__(parent, style="TFrame", padding=(14, 10, 14, 4))
        self._on_session_change = on_session_change
        self._sessions: list[Session] = []
        self._suppress = False

        top = ttk.Frame(self, style="TFrame")
        top.pack(fill="x", pady=(0, 8))

        self.shot_label = ttk.Label(top, text="Shot ----", font=theme.F_BIG)
        self.shot_label.pack(side="left")

        self.time_label = ttk.Label(top, text="", style="MutedBg.TLabel")
        self.time_label.pack(side="left", padx=(12, 0))

        self.session_box = ttk.Combobox(top, state="readonly", width=28, font=theme.F_SMALL)
        self.session_box.pack(side="right")
        self.session_box.bind("<<ComboboxSelected>>", self._session_selected)
        ttk.Label(top, text="表示中のデータ", style="MutedBg.TLabel").pack(
            side="right", padx=(0, 8)
        )

        cards = ttk.Frame(self, style="TFrame")
        cards.pack(fill="x")
        self.cards: list[ChannelCard] = []
        for name, color, text_color in zip(
            theme.CH_NAMES, theme.CH_COLORS, theme.CH_TEXT, strict=True
        ):
            c = ChannelCard(cards, name, color, text_color)
            c.pack(side="left", padx=(0, 10))
            self.cards.append(c)

        self.info = InfoCard(cards, "ショット情報")
        self.info.pack(side="left")

    # ------------------------------------------------------------------ update

    def set_data(
        self,
        shots: list[Shot],
        stats: list[ChannelStats],
        window_size: int,
        total: int,
    ) -> None:
        """表示中のショット列から、ヘッダの全要素を作り直す。"""
        latest = shots[-1] if shots else None
        prev = shots[-2] if len(shots) >= 2 else None

        if latest is None:
            self.shot_label.config(text="Shot ----")
            self.time_label.config(text="")
            for card in self.cards:
                card.set_data(None, None, [], None)
            self.info.set_rows([])
            return

        self.shot_label.config(text=f"Shot {latest.shot_no}")
        self.time_label.config(text=latest.dt.strftime("%Y/%m/%d  %H:%M:%S"))

        values = (latest.ch01, latest.ch02)
        prevs = (prev.ch01, prev.ch02) if prev else (None, None)
        series = ([s.ch01 for s in shots[-30:]], [s.ch02 for s in shots[-30:]])
        for i, card in enumerate(self.cards):
            delta = None if prevs[i] is None else values[i] - prevs[i]
            card.set_data(values[i], delta, series[i], stats[i])

        diff = latest.ch01 - latest.ch02
        self.info.set_rows(
            [
                ("CH01 − CH02", f"{diff:+.2f} MPa", theme.FG),
                ("サイクル", f"{latest.interval:.2f} s", theme.MUTED),
                ("表示", f"{len(shots)} / {total} 件", theme.MUTED),
                ("指定", f"直近 {window_size} 件", theme.DIM),
            ]
        )

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
