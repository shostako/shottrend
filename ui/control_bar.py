"""表示件数・グラフ形式・合成値モードのコントロール。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.config import CHART_KINDS, WINDOW_SIZES
from core.stats import COMPOSITE_LABELS, COMPOSITE_MODES

from . import theme

_KIND_LABELS = {"line": "折れ線", "bar": "棒"}


class _ToggleGroup(ttk.Frame):
    """1 つだけ選べるボタン列。ttk.Radiobutton より見た目を制御しやすい。"""

    def __init__(self, parent: tk.Misc, options: list[tuple[str, str]], initial, on_change) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self._on_change = on_change
        self._buttons: dict[object, ttk.Button] = {}
        for value, label in options:
            b = ttk.Button(
                self,
                text=label,
                style="Toggle.TButton",
                width=6,
                command=lambda v=value: self._select(v),
            )
            b.pack(side="left", padx=1)
            self._buttons[value] = b
        self._value = initial
        self._refresh()

    @property
    def value(self):
        return self._value

    def _select(self, value) -> None:
        if value == self._value:
            return
        self._value = value
        self._refresh()
        self._on_change(value)

    def _refresh(self) -> None:
        for value, button in self._buttons.items():
            button.config(style="ToggleOn.TButton" if value == self._value else "Toggle.TButton")


class ControlBar(ttk.Frame):
    def __init__(self, parent: tk.Misc, cfg, on_window, on_kind, on_composite) -> None:
        super().__init__(parent, style="Panel.TFrame", padding=(14, 8))

        ttk.Label(self, text="表示数", style="Muted.TLabel").pack(side="left", padx=(0, 6))
        self.window_group = _ToggleGroup(
            self, [(n, str(n)) for n in WINDOW_SIZES], cfg.window_size, on_window
        )
        self.window_group.pack(side="left")

        ttk.Label(self, text="形式", style="Muted.TLabel").pack(side="left", padx=(20, 6))
        self.kind_group = _ToggleGroup(
            self, [(k, _KIND_LABELS[k]) for k in CHART_KINDS], cfg.chart_kind, on_kind
        )
        self.kind_group.pack(side="left")

        ttk.Label(self, text="合成値", style="Muted.TLabel").pack(side="left", padx=(20, 6))
        self._composite = ttk.Combobox(
            self,
            state="readonly",
            width=6,
            font=theme.F_SMALL,
            values=[COMPOSITE_LABELS[m] for m in COMPOSITE_MODES],
        )
        self._composite.current(COMPOSITE_MODES.index(cfg.composite_mode))
        self._composite.pack(side="left")
        self._on_composite = on_composite
        self._composite.bind("<<ComboboxSelected>>", self._composite_changed)

        # 凡例（本体アプリの波形色と一致させてあることが一目で分かるように）
        legend = ttk.Frame(self, style="Panel.TFrame")
        legend.pack(side="right")
        for name, color in zip(theme.CH_NAMES, theme.CH_COLORS, strict=True):
            tk.Label(legend, text="■", fg=color, bg=theme.PANEL, font=theme.F_SMALL).pack(
                side="left", padx=(10, 2)
            )
            ttk.Label(legend, text=name, style="Muted.TLabel").pack(side="left")

    def _composite_changed(self, _event) -> None:
        self._on_composite(COMPOSITE_MODES[self._composite.current()])
