"""項目・表示件数・グラフ形式・合成値モード・差分列のコントロール。

三択以上は SegmentedControl（Canvas 自前描画）で揃える。ttk のボタンだと
「今どれが選ばれているか」が弱くて、離れた位置から読めない。

色の凡例は置かない。すぐ上の ch カードに色チップと名前があり、それが凡例を
兼ねる。

コントロールは「ラベル＋操作部」を 1 単位として横に並べ、ウィンドウ幅に
収まらなくなった単位から次の行へ折り返す。1 行に固定していた頃はバーの幅が
そのままウィンドウの最小幅になり、日本語で 1092px、英語で 1233px あった。
1920px の画面を Win+← で左半分（960px）にしても最小幅で止まり、「半分より
少し大きい」窓になる。折り返せば最小幅は最も広い単位の分だけで済む。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from shottrend.core.config import CHART_KINDS, WINDOW_SIZES
from shottrend.core.metrics import METRICS
from shottrend.core.stats import COMPOSITE_MODES
from shottrend.i18n import composite_label, metric_label, t

from . import theme
from .flow import pack_rows, single_row_width
from .widgets import SegmentedControl

#: バーの左右の内側余白（`padding` の左右）。折り返し判定の使える幅を出すのに使う
PAD_X = 14
#: 単位と単位の間隔
GAP = 22
#: 折り返した行と行の間隔
ROW_GAP = 6


class ControlBar(ttk.Frame):
    def __init__(
        self, parent: tk.Misc, cfg, on_window, on_kind, on_composite, on_delta, on_metric
    ) -> None:
        super().__init__(parent, style="TFrame", padding=(PAD_X, 6, PAD_X, 6))
        self._units: list[ttk.Frame] = []
        self._rows: list[list[int]] = []

        # 項目（ピーク／積分値／…）。11 択なのでセグメントでなくドロップダウン。
        # 全 ch 共通で 1 つ。ch ごとに変えると縦軸が 1 本のグラフに載らないし、
        # 合成値も意味を失う
        unit = self._unit(t("control.metric"))
        self._metric_keys = [m.key for m in METRICS]
        values = [f"{metric_label(m.key)} [{m.unit}]" for m in METRICS]
        self.metric_box = ttk.Combobox(
            unit,
            state="readonly",
            width=theme.text_cells(values, theme.F_LABEL),
            font=theme.F_LABEL,
            values=values,
        )
        self.metric_box.current(
            self._metric_keys.index(cfg.metric) if cfg.metric in self._metric_keys else 0
        )
        self.metric_box.bind(
            "<<ComboboxSelected>>",
            lambda _e: on_metric(self._metric_keys[self.metric_box.current()]),
        )
        self.metric_box.pack(side="left")

        # セグメント幅は SegmentedControl がラベルを実測して決める。46/58/48 と
        # いった数字は日本語の字面に合わせたもので、他言語では必ず外れる
        self.window_group = self._group(
            t("control.window"), [(n, str(n)) for n in WINDOW_SIZES], cfg.window_size, on_window
        )
        self.kind_group = self._group(
            t("control.kind"),
            [(k, t(f"chart_kind.{k}")) for k in CHART_KINDS],
            cfg.chart_kind,
            on_kind,
        )
        self.composite_group = self._group(
            t("control.composite"),
            [(m, composite_label(m)) for m in COMPOSITE_MODES],
            cfg.composite_mode,
            on_composite,
        )

        # 差分列は「出す／出さない」の二値なのでチェックボックス。セグメント型に
        # すると他の三択と同列に見えて、選択肢が 2 つしかない理由が伝わらない
        unit = self._unit(None)
        self._delta_var = tk.BooleanVar(value=bool(cfg.show_delta_columns))
        ttk.Checkbutton(
            unit,
            text=t("control.delta"),
            variable=self._delta_var,
            command=lambda: on_delta(self._delta_var.get()),
            style="TCheckbutton",
        ).pack(side="left")

        # 最初は 1 行で置く。実際の幅は配置後に <Configure> で分かるので、
        # そこで折り返しを決め直す
        self._place(pack_rows(self._unit_widths(), GAP, 10**9))
        self.bind("<Configure>", self._on_configure)

    # ---------------------------------------------------------------- building

    def _unit(self, label: str | None) -> ttk.Frame:
        """「ラベル＋操作部」の入れ物。折り返しはこの単位で行う。"""
        unit = ttk.Frame(self, style="TFrame")
        if label:
            ttk.Label(unit, text=label, style="MutedBg.TLabel").pack(side="left", padx=(0, 6))
        self._units.append(unit)
        return unit

    def _group(self, label: str, options, initial, callback):
        unit = self._unit(label)
        ctrl = SegmentedControl(unit, options, initial, callback)
        ctrl.pack(side="left")
        return ctrl

    # ----------------------------------------------------------------- layout

    def _unit_widths(self) -> list[int]:
        self.update_idletasks()
        return [u.winfo_reqwidth() for u in self._units]

    def min_width(self) -> int:
        """このバーが必要とする最小幅。最も広い単位が 1 行に収まればよい。"""
        return max(self._unit_widths(), default=0) + PAD_X * 2

    def single_row_width(self) -> int:
        """全部を 1 行に並べたときの幅。"""
        return single_row_width(self._unit_widths(), GAP) + PAD_X * 2

    def _place(self, rows: list[list[int]]) -> None:
        if rows == self._rows:
            return
        self._rows = rows
        for u in self._units:
            u.grid_forget()
        for r, row in enumerate(rows):
            for c, i in enumerate(row):
                self._units[i].grid(
                    row=r,
                    column=c,
                    sticky="w",
                    padx=(0, GAP if c < len(row) - 1 else 0),
                    pady=(ROW_GAP if r > 0 else 0, 0),
                )

    def _on_configure(self, event: tk.Event) -> None:
        # 配置前の幅 1 で折り返しを決めると全部縦一列になる
        if event.widget is not self or event.width <= 1:
            return
        avail = event.width - PAD_X * 2
        self._place(pack_rows(self._unit_widths(), GAP, avail))
