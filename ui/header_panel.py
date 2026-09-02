"""最新ショットの値と統計を出すヘッダ。

このアプリの存在理由がここに集約されている。純正トレンドビューアは値を
クリックしないと読めないので、常時大きく出す。加えて「前ショットからどう
動いたか」を ▲▼ で見せる（純正にはこれが無い）。

使用中の ch 数でカードの形を変える。MPS08B は 32ch まで計測できるので、
大きいカードを固定で並べる作りにすると破綻する。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.models import Session, Shot
from core.stats import ChannelStats

from . import theme
from .widgets import ChannelCard, CompactChannelCard, InfoCard

#: これを超える ch 数になったら小型カードに切り替える
LARGE_CARD_LIMIT = 3
#: 小型カードを 1 段に並べる枚数
COMPACT_PER_ROW = 5
#: スパークラインに使う直近ショット数
SPARK_POINTS = 30


class HeaderPanel(ttk.Frame):
    def __init__(self, parent: tk.Misc, on_session_change) -> None:
        super().__init__(parent, style="TFrame", padding=(14, 10, 14, 4))
        self._on_session_change = on_session_change
        self._sessions: list[Session] = []
        self._suppress = False
        self._channels: list[int] = []
        self._cards: list[tk.Canvas] = []

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

        row = ttk.Frame(self, style="TFrame")
        row.pack(fill="x")
        self._card_area = ttk.Frame(row, style="TFrame")
        self._card_area.pack(side="left")
        self.info = InfoCard(row, "ショット情報")
        self.info.pack(side="left", padx=(10, 0))

    # ---------------------------------------------------------------- channels

    def _rebuild_cards(self, channels: list[int]) -> None:
        """ch の顔ぶれが変わったときだけカードを作り直す。"""
        for card in self._cards:
            card.destroy()
        self._cards = []
        self._channels = list(channels)

        compact = len(channels) > LARGE_CARD_LIMIT
        for pos, ch in enumerate(channels):
            name = theme.ch_name(ch)
            color = theme.ch_color(ch)
            text_color = theme.ch_text_color(ch)
            if compact:
                card = CompactChannelCard(self._card_area, name, color, text_color)
                card.grid(
                    row=pos // COMPACT_PER_ROW,
                    column=pos % COMPACT_PER_ROW,
                    padx=(0, 8),
                    pady=(0, 6),
                )
            else:
                card = ChannelCard(self._card_area, name, color, text_color)
                card.grid(row=0, column=pos, padx=(0, 10))
            self._cards.append(card)

    # ------------------------------------------------------------------ update

    def set_data(
        self,
        shots: list[Shot],
        channels: list[int],
        stats: list[ChannelStats],
        window_size: int,
        total: int,
    ) -> None:
        """表示中のショット列から、ヘッダの全要素を作り直す。"""
        if channels != self._channels:
            self._rebuild_cards(channels)

        latest = shots[-1] if shots else None
        prev = shots[-2] if len(shots) >= 2 else None

        if latest is None:
            self.shot_label.config(text="Shot ----")
            self.time_label.config(text="")
            for card in self._cards:
                card.set_data(None, None, [], None)
            self.info.set_rows([])
            return

        self.shot_label.config(text=f"Shot {latest.shot_no}")
        self.time_label.config(text=latest.dt.strftime("%Y/%m/%d  %H:%M:%S"))

        recent = shots[-SPARK_POINTS:]
        for pos, ch in enumerate(channels):
            value = latest.peak(ch)
            delta = None if prev is None else value - prev.peak(ch)
            series = [s.peak(ch) for s in recent]
            self._cards[pos].set_data(value, delta, series, stats[pos])

        self.info.set_rows(self._info_rows(latest, channels, window_size, len(shots), total))

    def _info_rows(
        self, latest: Shot, channels: list[int], window_size: int, shown: int, total: int
    ) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        if len(channels) >= 2:
            values = [latest.peak(c) for c in channels]
            spread = max(values) - min(values)
            label = (
                f"{theme.ch_name(channels[0])} − {theme.ch_name(channels[1])}"
                if len(channels) == 2
                else "ch 間のばらつき"
            )
            value = (
                f"{latest.peak(channels[0]) - latest.peak(channels[1]):+.2f} MPa"
                if len(channels) == 2
                else f"{spread:.2f} MPa"
            )
            rows.append((label, value, theme.FG))
        rows.append(("サイクル", f"{latest.interval:.2f} s", theme.MUTED))
        rows.append(("表示", f"{shown} / {total} 件", theme.MUTED))
        rows.append(("使用 ch", f"{len(channels)} 本", theme.DIM))
        return rows

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
