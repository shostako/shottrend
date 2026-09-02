"""項目・表示件数・グラフ形式・合成値モード・差分列のコントロール。

三択以上は SegmentedControl（Canvas 自前描画）で揃える。ttk のボタンだと
「今どれが選ばれているか」が弱くて、離れた位置から読めない。

色の凡例は置かない。すぐ上の ch カードに色チップと名前があり、それが凡例を
兼ねる。置くと最小幅 1000 で右端が切れた。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.config import CHART_KINDS, WINDOW_SIZES
from core.metrics import METRICS
from core.stats import COMPOSITE_LABELS, COMPOSITE_MODES

from . import theme
from .widgets import SegmentedControl

_KIND_LABELS = {"line": "折れ線", "bar": "棒"}


class ControlBar(ttk.Frame):
    def __init__(
        self, parent: tk.Misc, cfg, on_window, on_kind, on_composite, on_delta, on_metric
    ) -> None:
        super().__init__(parent, style="TFrame", padding=(14, 6, 14, 6))

        # 項目（ピーク／積分値／…）。11 択なのでセグメントでなくドロップダウン。
        # 全 ch 共通で 1 つ。ch ごとに変えると縦軸が 1 本のグラフに載らないし、
        # 合成値も意味を失う
        ttk.Label(self, text="項目", style="MutedBg.TLabel").pack(side="left", padx=(0, 6))
        self._metric_keys = [m.key for m in METRICS]
        self.metric_box = ttk.Combobox(
            self,
            state="readonly",
            width=11,
            font=theme.F_LABEL,
            values=[f"{m.label} [{m.unit}]" for m in METRICS],
        )
        self.metric_box.current(
            self._metric_keys.index(cfg.metric) if cfg.metric in self._metric_keys else 0
        )
        self.metric_box.bind(
            "<<ComboboxSelected>>",
            lambda _e: on_metric(self._metric_keys[self.metric_box.current()]),
        )
        self.metric_box.pack(side="left", padx=(0, 22))

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

        # 差分列は「出す／出さない」の二値なのでチェックボックス。セグメント型に
        # すると他の三択と同列に見えて、選択肢が 2 つしかない理由が伝わらない
        self._delta_var = tk.BooleanVar(value=bool(cfg.show_delta_columns))
        ttk.Checkbutton(
            self,
            text="差分列",
            variable=self._delta_var,
            command=lambda: on_delta(self._delta_var.get()),
            style="TCheckbutton",
        ).pack(side="left", padx=(0, 22))

    def _group(self, label: str, options, initial, callback, seg_width: int):
        ttk.Label(self, text=label, style="MutedBg.TLabel").pack(side="left", padx=(0, 6))
        ctrl = SegmentedControl(self, options, initial, callback, seg_width=seg_width)
        ctrl.pack(side="left", padx=(0, 22))
        return ctrl
