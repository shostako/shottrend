"""ショット履歴の数値テーブル（最新が上）。

列は使用中の ch に合わせて組み直す。差分（前ショットとの差、ch 間のばらつき）
は既定では出さない。列が増えるとぱっと見の認識が鈍るため。

数値列は内容に合わせた固定幅で左に詰め、余った幅は右端の余白列に吸わせる。
全列を均等に伸ばすと 5 桁の数値が 150px 幅の列に散らばり、行を横に読む
目の移動が大きくなって却って読みにくい。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.models import Shot
from core.stats import COMPOSITE_LABELS, composite

from . import theme

#: 右端の余白列。余った幅を全部引き受けて、数値列を左に詰めたまま保つ
PAD_KEY = "pad"
PAD_WIDTH = 16

#: 表示する行数。ウィンドウが画面からはみ出さないよう固定する。
VISIBLE_ROWS = 8


def _delta_text(cur: float, prev: float | None) -> str:
    if prev is None:
        return "—"
    d = cur - prev
    if abs(d) < 0.005:
        return "→ 0.00"
    return f"{'▲' if d > 0 else '▼'} {abs(d):.2f}"


class ShotTable(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, style="TFrame")
        self._show_delta = False
        self._channels: list[int] = []
        self._composite_mode = "max"

        # 行を選んでも何も起きないので選択自体を切る。選択色と最新行の色が同系で、
        # クリックすると「最新」が 2 行あるように見えていた
        self.tree = ttk.Treeview(
            self, columns=(), show="headings", selectmode="none", height=VISIBLE_ROWS
        )
        vscroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        # ch が増えると列が画面幅に収まらない (8ch + 差分列で 20 列になる)
        self._hscroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self._hscroll_shown = False
        self.tree.configure(yscrollcommand=vscroll.set, xscrollcommand=self._on_xscroll)

        self.tree.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="left", fill="y")

        # 最新行を目立たせる。交互行は本体アプリのチャンネル一覧に倣う
        self.tree.tag_configure(
            "latest", background=theme.SEL_BG, foreground=theme.FG, font=(theme.MONO, 10, "bold")
        )
        self.tree.tag_configure("odd", background=theme.PANEL_ALT)
        self.tree.tag_configure("gap", foreground=theme.ERR)

        self._rebuild_columns()

    def _on_xscroll(self, first: str, last: str) -> None:
        """横スクロールバーは列が入りきらないときだけ出す。

        2ch なら常に収まるので、出しっぱなしにすると場所を食うだけになる。
        """
        self._hscroll.set(first, last)
        needed = float(first) > 0.0 or float(last) < 1.0
        if needed and not self._hscroll_shown:
            self._hscroll.pack(side="bottom", fill="x", before=self.tree)
            self._hscroll_shown = True
        elif not needed and self._hscroll_shown:
            self._hscroll.pack_forget()
            self._hscroll_shown = False

    # ---------------------------------------------------------------- columns

    def set_channels(self, channels: list[int]) -> None:
        if channels == self._channels:
            return
        self._channels = list(channels)
        self._rebuild_columns()

    def set_show_delta(self, show: bool) -> None:
        if show == self._show_delta:
            return
        self._show_delta = show
        self._rebuild_columns()

    def _column_spec(self) -> list[tuple[str, str, int, str]]:
        """(key, 見出し, 最小幅, 寄せ) の並びを作る。"""
        spec: list[tuple[str, str, int, str]] = [
            ("shot", "Shot", 64, "e"),
            ("time", "Time", 88, "center"),
        ]
        for ch in self._channels:
            name = theme.ch_name(ch)
            spec.append((f"ch{ch}", name, 80, "e"))
            if self._show_delta:
                spec.append((f"d{ch}", f"Δ{name}", 80, "e"))
        spec.append(("comp", COMPOSITE_LABELS.get(self._composite_mode, "最大"), 80, "e"))
        if self._show_delta and len(self._channels) >= 2:
            spec.append(("spread", "ばらつき", 84, "e"))
        spec.append(("interval", "interval", 84, "e"))
        spec.append((PAD_KEY, "", PAD_WIDTH, "center"))
        return spec

    def _rebuild_columns(self) -> None:
        spec = self._column_spec()
        keys = [c[0] for c in spec]
        self.tree.configure(columns=keys, displaycolumns=keys)
        for key, title, width, anchor in spec:
            self.tree.heading(key, text=title, anchor=anchor)
            # 伸びるのは余白列だけ。数値列は固定幅で左に詰める
            self.tree.column(
                key, width=width, minwidth=width, anchor=anchor, stretch=key == PAD_KEY
            )

    # ------------------------------------------------------------------ rows

    def update_rows(self, shots: list[Shot], composite_mode: str) -> None:
        if composite_mode != self._composite_mode:
            self._composite_mode = composite_mode
            self.tree.heading("comp", text=COMPOSITE_LABELS.get(composite_mode, "最大"), anchor="e")
        self.tree.delete(*self.tree.get_children())

        # 最新を上にするので逆順で回す
        ordered = list(reversed(shots))
        for i, s in enumerate(ordered):
            older = ordered[i + 1] if i + 1 < len(ordered) else None
            contiguous = older is not None and older.shot_no == s.shot_no - 1

            tags: list[str] = ["latest"] if i == 0 else (["odd"] if i % 2 else [])
            # 中断直後の行は差分が意味を持たないので色を変えて示す
            if older is not None and not contiguous and i != 0:
                tags.append("gap")

            values: list[object] = [s.shot_no, s.time_text]
            for ch in self._channels:
                values.append(f"{s.peak(ch):.2f}")
                if self._show_delta:
                    prev = older.peak(ch) if contiguous else None
                    values.append(_delta_text(s.peak(ch), prev))
            values.append(f"{composite(s, composite_mode, self._channels):.2f}")
            if self._show_delta and len(self._channels) >= 2:
                peaks = [s.peak(c) for c in self._channels]
                values.append(f"{max(peaks) - min(peaks):.2f}")
            values.append(f"{s.interval:.2f}")
            values.append("")

            self.tree.insert("", "end", values=tuple(values), tags=tags)
