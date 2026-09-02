"""表示件数・グラフ形式・合成値モードのコントロール。

すべて SegmentedControl（Canvas 自前描画）で揃える。ttk のボタンだと
「今どれが選ばれているか」が弱くて、離れた位置から読めない。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.config import CHART_KINDS, WINDOW_SIZES
from core.stats import COMPOSITE_LABELS, COMPOSITE_MODES

from . import theme
from .widgets import SegmentedControl

_KIND_LABELS = {"line": "折れ線", "bar": "棒"}


class _Legend(tk.Canvas):
    """使用中 ch の色見本。本体アプリのチャンネル一覧の色チップに倣う。"""

    HEIGHT = 28
    ITEM_W = 68
    #: これを超えたら個別に並べず「n ch」とだけ出す
    MAX_ITEMS = 6

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            width=self.ITEM_W * 2,
            height=self.HEIGHT,
            background=theme.BG,
            highlightthickness=0,
            bd=0,
        )
        self._channels: list[int] = []

    def set_channels(self, channels: list[int]) -> None:
        if channels == self._channels:
            return
        self._channels = list(channels)
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        cy = self.HEIGHT / 2
        chs = self._channels
        if len(chs) > self.MAX_ITEMS:
            self.configure(width=self.ITEM_W * 2)
            x = 6
            for ch in chs[: self.MAX_ITEMS - 1]:
                self.create_rectangle(
                    x, cy - 5, x + 9, cy + 5, fill=theme.ch_color(ch), outline=theme.CHIP_EDGE
                )
                x += 13
            self.create_text(
                x + 4,
                cy,
                text=f"計 {len(chs)} ch",
                anchor="w",
                fill=theme.MUTED,
                font=theme.F_SMALL,
            )
            return

        self.configure(width=max(self.ITEM_W, self.ITEM_W * len(chs)))
        x = 6
        for ch in chs:
            self.create_rectangle(
                x, cy - 5, x + 10, cy + 5, fill=theme.ch_color(ch), outline=theme.CHIP_EDGE
            )
            self.create_text(
                x + 16,
                cy,
                text=theme.ch_name(ch),
                anchor="w",
                fill=theme.MUTED,
                font=theme.F_SMALL,
            )
            x += self.ITEM_W


class ControlBar(ttk.Frame):
    def __init__(self, parent: tk.Misc, cfg, on_window, on_kind, on_composite, on_delta) -> None:
        super().__init__(parent, style="TFrame", padding=(14, 6, 14, 6))

        self.window_group = self._group(
            "表示数", [(n, str(n)) for n in WINDOW_SIZES], cfg.window_size, on_window, 46
        )
        self.kind_group = self._group(
            "形式",
            [(k, _KIND_LABELS[k]) for k in CHART_KINDS],
            cfg.chart_kind,
            on_kind,
            58,
        )
        self.composite_group = self._group(
            "合成値",
            [(m, COMPOSITE_LABELS[m]) for m in COMPOSITE_MODES],
            cfg.composite_mode,
            on_composite,
            48,
        )

        self.delta_group = self._group(
            "差分列",
            [(False, "隠す"), (True, "出す")],
            cfg.show_delta_columns,
            on_delta,
            46,
        )

        self.legend = _Legend(self)
        self.legend.pack(side="right")

    def set_channels(self, channels: list[int]) -> None:
        self.legend.set_channels(channels)

    def _group(self, label: str, options, initial, callback, seg_width: int):
        ttk.Label(self, text=label, style="MutedBg.TLabel").pack(side="left", padx=(0, 6))
        ctrl = SegmentedControl(self, options, initial, callback, seg_width=seg_width)
        ctrl.pack(side="left", padx=(0, 22))
        return ctrl
