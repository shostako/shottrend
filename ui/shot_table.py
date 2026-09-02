"""ショット履歴の数値テーブル（最新が上）。

前ショットとの差を Δ 列に出す。純正トレンドビューアには無い情報で、
「上がったのか下がったのか」がテーブルだけで追える。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.models import Shot
from core.stats import COMPOSITE_LABELS, composite

from . import theme

# (key, 見出し, 幅, 寄せ, 伸縮)
_COLUMNS = (
    ("shot", "Shot", 78, "e", False),
    ("time", "Time", 100, "center", False),
    ("ch01", "CH01", 92, "e", False),
    ("d01", "Δ", 84, "e", False),
    ("ch02", "CH02", 92, "e", False),
    ("d02", "Δ", 84, "e", False),
    ("comp", "最大", 92, "e", False),
    ("diff", "CH01−CH02", 106, "e", False),
    ("interval", "interval", 100, "e", True),
)

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
        self.tree = ttk.Treeview(
            self,
            columns=[c[0] for c in _COLUMNS],
            show="headings",
            selectmode="browse",
            height=VISIBLE_ROWS,
        )
        for key, title, width, anchor, stretch in _COLUMNS:
            self.tree.heading(key, text=title, anchor=anchor)
            self.tree.column(key, width=width, anchor=anchor, stretch=stretch)

        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")

        # 最新行を目立たせる。交互行は本体アプリのチャンネル一覧に倣う
        self.tree.tag_configure(
            "latest", background=theme.SEL_BG, foreground=theme.FG, font=(theme.MONO, 10, "bold")
        )
        self.tree.tag_configure("odd", background=theme.PANEL_ALT)
        self.tree.tag_configure("gap", foreground=theme.ERR)

    def update_rows(self, shots: list[Shot], composite_mode: str) -> None:
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

            prev01 = older.ch01 if contiguous else None
            prev02 = older.ch02 if contiguous else None
            self.tree.insert(
                "",
                "end",
                values=(
                    s.shot_no,
                    s.time_text,
                    f"{s.ch01:.2f}",
                    _delta_text(s.ch01, prev01),
                    f"{s.ch02:.2f}",
                    _delta_text(s.ch02, prev02),
                    f"{composite(s, composite_mode):.2f}",
                    f"{s.ch01 - s.ch02:+.2f}",
                    f"{s.interval:.2f}",
                ),
                tags=tags,
            )
