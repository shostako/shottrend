"""ショット履歴の数値テーブル（最新が上）。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.models import Shot
from core.stats import COMPOSITE_LABELS, composite

from . import theme

_COLUMNS = (
    ("shot", "Shot", 100, "e"),
    ("time", "Time", 130, "center"),
    ("ch01", "CH01", 140, "e"),
    ("ch02", "CH02", 140, "e"),
    ("comp", "最大", 140, "e"),
    ("interval", "interval", 130, "e"),
)

#: 表示する行数。ウィンドウが画面からはみ出さないよう固定する。
VISIBLE_ROWS = 9


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
        for key, title, width, anchor in _COLUMNS:
            self.tree.heading(key, text=title, anchor=anchor)
            self.tree.column(key, width=width, anchor=anchor, stretch=False)

        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="y", expand=False)
        scroll.pack(side="left", fill="y")

        # 最新行を目立たせる
        self.tree.tag_configure("latest", background="#22303C", foreground="#FFFFFF")
        self.tree.tag_configure("gap", foreground=theme.MUTED)

    def update_rows(self, shots: list[Shot], composite_mode: str) -> None:
        self.tree.heading("comp", text=COMPOSITE_LABELS.get(composite_mode, "最大"))
        self.tree.delete(*self.tree.get_children())

        # 最新を上にするので逆順で回す
        ordered = list(reversed(shots))
        for i, s in enumerate(ordered):
            tags: list[str] = ["latest"] if i == 0 else []
            # 1 つ古い側 (= 1 つ下の行) との間に欠番があれば中断直後の行として示す
            older = ordered[i + 1] if i + 1 < len(ordered) else None
            gap = older.shot_no != s.shot_no - 1 if older is not None else False
            if gap and i != 0:
                tags.append("gap")
            values = (
                s.shot_no,
                s.time_text,
                f"{s.ch01:.2f}",
                f"{s.ch02:.2f}",
                f"{composite(s, composite_mode):.2f}",
                f"{s.interval:.2f}",
            )
            self.tree.insert("", "end", values=values, tags=tags)
