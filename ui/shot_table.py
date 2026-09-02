"""ショット履歴の数値テーブル（最新が上）。

列は 2 段構え。既定では素の値だけを出し、前ショットとの差や ch 間の差は
トグルで出す。列が増えるとぱっと見の認識が鈍るため、常時は出さない。

幅はウィンドウに合わせて全列が均等に伸びる。右端には余白列を置いて、
最後の数値が枠に張り付かないようにしている。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.models import Shot
from core.stats import COMPOSITE_LABELS, composite

from . import theme

# (key, 見出し, 最小幅, 寄せ)
_BASE_COLUMNS = (
    ("shot", "Shot", 70, "e"),
    ("time", "Time", 92, "center"),
    ("ch01", "CH01", 84, "e"),
    ("ch02", "CH02", 84, "e"),
    ("comp", "最大", 84, "e"),
    ("interval", "interval", 92, "e"),
)
_DELTA_COLUMNS = (
    ("d01", "ΔCH01", 84, "e"),
    ("d02", "ΔCH02", 84, "e"),
    ("diff", "CH01−CH02", 100, "e"),
)
#: 右端の余白。最後の数値が枠に張り付くのを防ぐためだけの列
_PAD_COLUMN = ("pad", "", 16, "center")

ALL_COLUMNS = (*_BASE_COLUMNS, *_DELTA_COLUMNS, _PAD_COLUMN)

#: 差分列を出すときの並び順
_ORDER_WITH_DELTA = (
    "shot",
    "time",
    "ch01",
    "d01",
    "ch02",
    "d02",
    "comp",
    "diff",
    "interval",
    "pad",
)
_ORDER_PLAIN = ("shot", "time", "ch01", "ch02", "comp", "interval", "pad")

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

        self.tree = ttk.Treeview(
            self,
            columns=[c[0] for c in ALL_COLUMNS],
            show="headings",
            selectmode="browse",
            height=VISIBLE_ROWS,
        )
        for key, title, width, anchor in ALL_COLUMNS:
            self.tree.heading(key, text=title, anchor=anchor)
            # 余白列だけは伸ばさない。それ以外はウィンドウ幅を均等に分け合う
            stretch = key != "pad"
            self.tree.column(key, width=width, minwidth=width, anchor=anchor, stretch=stretch)

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

        self._apply_display_columns()

    # ----------------------------------------------------------------- config

    def set_show_delta(self, show: bool) -> None:
        if show == self._show_delta:
            return
        self._show_delta = show
        self._apply_display_columns()

    def _apply_display_columns(self) -> None:
        order = _ORDER_WITH_DELTA if self._show_delta else _ORDER_PLAIN
        self.tree.configure(displaycolumns=order)

    # ------------------------------------------------------------------ rows

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
                    f"{s.ch02:.2f}",
                    f"{composite(s, composite_mode):.2f}",
                    f"{s.interval:.2f}",
                    _delta_text(s.ch01, prev01),
                    _delta_text(s.ch02, prev02),
                    f"{s.ch01 - s.ch02:+.2f}",
                    "",
                ),
                tags=tags,
            )
