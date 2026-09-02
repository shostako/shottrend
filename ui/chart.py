"""tk.Canvas 直描きのショット推移グラフ。

横軸は等間隔のカテゴリ軸。ショット番号は目盛ラベルにのみ出す。
理由 (罠2): ショット番号は中断で飛ぶ。実数軸にすると 1087 と 1109 の間に
巨大な空白ができて、直近 10 件を見たいのに 1 点しか見えない事故になる。
"""

from __future__ import annotations

import math
import tkinter as tk

from core.history import find_gaps
from core.models import Shot

from . import theme

PAD_LEFT = 58
PAD_RIGHT = 26
PAD_TOP = 18
PAD_BOTTOM = 34

RESIZE_DEBOUNCE_MS = 120

#: 最新値ラベルが重ならないための最小間隔[px]
LABEL_MIN_SEP = 15

#: 中断ラベルを段違いにする条件と段数
GAP_LABEL_MIN_DX = 46
GAP_LABEL_ROWS = 3
GAP_LABEL_ROW_H = 13


def _nice_step(span: float, target_lines: int = 5) -> float:
    """1 / 2 / 5 × 10^k の中から手頃な目盛間隔を選ぶ。"""
    if span <= 0:
        return 1.0
    raw = span / max(1, target_lines)
    mag = 10.0 ** math.floor(math.log10(raw))
    for mult in (1.0, 2.0, 5.0, 10.0):
        if raw <= mult * mag:
            return mult * mag
    return 10.0 * mag


class ShotChart(tk.Canvas):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            background=theme.PLOT_BG,
            highlightthickness=0,
            bd=0,
        )
        self._shots: list[Shot] = []
        self._kind = "line"
        self._resize_job: str | None = None
        self.bind("<Configure>", self._on_configure)

    # ------------------------------------------------------------------ public

    def set_data(self, shots: list[Shot], kind: str) -> None:
        self._shots = shots
        self._kind = kind if kind in ("line", "bar") else "line"
        self.redraw()

    # ----------------------------------------------------------------- resize

    def _on_configure(self, _event) -> None:
        # ドラッグ中に数百回描き直さないよう遅延させる
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(RESIZE_DEBOUNCE_MS, self._resize_fire)

    def _resize_fire(self) -> None:
        self._resize_job = None
        self.redraw()

    # ------------------------------------------------------------------ layout

    def _plot_box(self) -> tuple[int, int, int, int]:
        w = self.winfo_width()
        h = self.winfo_height()
        return (
            PAD_LEFT,
            PAD_TOP,
            max(PAD_LEFT + 10, w - PAD_RIGHT),
            max(PAD_TOP + 10, h - PAD_BOTTOM),
        )

    def _y_domain(self) -> tuple[float, float]:
        values = [v for s in self._shots for v in (s.ch01, s.ch02)]
        if not values:
            return 0.0, 1.0
        lo, hi = min(values), max(values)
        if self._kind == "bar":
            # 棒グラフは 0 起点でないと長さの比が嘘になる
            lo = min(0.0, lo)
        span = hi - lo
        if span < 1e-9:
            return lo - 1.0, hi + 1.0
        margin = span * 0.08
        return lo - margin, hi + margin

    # ------------------------------------------------------------------ redraw

    def redraw(self) -> None:
        self.delete("all")
        left, top, right, bottom = self._plot_box()
        n = len(self._shots)

        if n == 0:
            self.create_text(
                (left + right) // 2,
                (top + bottom) // 2,
                text="データなし",
                fill=theme.DIM,
                font=theme.F_LABEL,
            )
            return

        y_min, y_max = self._y_domain()
        y_span = y_max - y_min
        slot_w = (right - left) / n

        def x_at(i: int) -> float:
            return left + (i + 0.5) * slot_w

        def y_at(v: float) -> float:
            return top + (bottom - top) * (y_max - v) / y_span

        self._draw_grid(left, top, right, bottom, y_min, y_max, y_at)

        gaps = set(find_gaps(self._shots))
        if self._kind == "bar":
            self._draw_bars(x_at, y_at, y_min, slot_w, bottom)
        else:
            self._draw_lines(x_at, y_at, gaps)
        self._draw_gap_marks(gaps, x_at, slot_w, top, bottom)
        self._draw_x_labels(x_at, bottom, n)
        self._draw_latest(x_at, y_at, n, right, top)

    # ------------------------------------------------------------------ pieces

    def _draw_grid(self, left, top, right, bottom, y_min, y_max, y_at) -> None:
        step = _nice_step(y_max - y_min)
        v = math.ceil(y_min / step) * step
        while v <= y_max + 1e-9:
            y = y_at(v)
            self.create_line(left, y, right, y, fill=theme.GRID)
            self.create_text(
                left - 8,
                y,
                text=f"{v:g}",
                anchor="e",
                fill=theme.MUTED,
                font=theme.F_SMALL,
            )
            v += step
        self.create_line(left, top, left, bottom, fill=theme.AXIS)
        self.create_line(left, bottom, right, bottom, fill=theme.AXIS)
        self.create_text(
            left - 8, top - 8, text="MPa", anchor="e", fill=theme.MUTED, font=theme.F_SMALL
        )

    def _draw_lines(self, x_at, y_at, gaps: set[int]) -> None:
        n = len(self._shots)
        radius = 3 if n <= 50 else 2
        for ch_index, color in enumerate(theme.CH_COLORS):
            # 中断をまたいで線を繋がない。繋ぐと連続した変化に見えてしまう。
            segment: list[float] = []
            for i, shot in enumerate(self._shots):
                if i in gaps and segment:
                    self._flush_segment(segment, color)
                    segment = []
                value = shot.ch01 if ch_index == 0 else shot.ch02
                segment.extend((x_at(i), y_at(value)))
            self._flush_segment(segment, color)

            for i, shot in enumerate(self._shots):
                value = shot.ch01 if ch_index == 0 else shot.ch02
                x, y = x_at(i), y_at(value)
                self.create_oval(
                    x - radius, y - radius, x + radius, y + radius, fill=color, outline=""
                )

    def _flush_segment(self, coords: list[float], color: str) -> None:
        if len(coords) >= 4:
            self.create_line(*coords, fill=color, width=2, smooth=False)
        elif len(coords) == 2:
            # 1 点だけの区間。マーカーだけ後で打たれるので線は引かない。
            pass

    def _draw_bars(self, x_at, y_at, y_min, slot_w, bottom) -> None:
        bar_w = max(2.0, slot_w * 0.30)
        gap = slot_w * 0.06
        base_y = y_at(max(y_min, 0.0))
        for i, shot in enumerate(self._shots):
            cx = x_at(i)
            for ch_index, color in enumerate(theme.CH_COLORS):
                value = shot.ch01 if ch_index == 0 else shot.ch02
                if ch_index == 0:
                    x0 = cx - gap / 2 - bar_w
                    x1 = cx - gap / 2
                else:
                    x0 = cx + gap / 2
                    x1 = cx + gap / 2 + bar_w
                self.create_rectangle(x0, y_at(value), x1, base_y, fill=color, outline="")

    def _draw_gap_marks(self, gaps: set[int], x_at, slot_w, top, bottom) -> None:
        """中断箇所に破線を引き、欠けたショット数を添える。

        中断が近接するとラベルが重なって読めなくなるので、直前のラベルと
        近い場合は段を下げる。
        """
        last_label_x = -1e9
        row = 0
        for i in sorted(gaps):
            x = x_at(i) - slot_w / 2
            self.create_line(x, top, x, bottom, fill=theme.GAP_LINE, dash=(3, 3))
            missing = self._shots[i].shot_no - self._shots[i - 1].shot_no - 1
            if x - last_label_x < GAP_LABEL_MIN_DX:
                row = (row + 1) % GAP_LABEL_ROWS
            else:
                row = 0
            self.create_text(
                x + 3,
                top + 2 + row * GAP_LABEL_ROW_H,
                text=f"{missing}欠",
                anchor="nw",
                fill=theme.DIM,
                font=theme.F_SMALL,
            )
            last_label_x = x

    def _draw_x_labels(self, x_at, bottom, n: int) -> None:
        step = max(1, math.ceil(n / 8))
        for i, shot in enumerate(self._shots):
            is_last = i == n - 1
            if i % step != 0 and not is_last:
                continue
            self.create_text(
                x_at(i),
                bottom + 6,
                text=str(shot.shot_no),
                anchor="n",
                fill=theme.FG if is_last else theme.MUTED,
                font=theme.F_SMALL,
            )
        self.create_text(
            x_at(n - 1) if n else 0,
            bottom + 20,
            text="shot",
            anchor="n",
            fill=theme.DIM,
            font=theme.F_SMALL,
        )

    def _draw_latest(self, x_at, y_at, n: int, right: int, top: int) -> None:
        """最新ショットを強調し、数値を併記する。

        純正トレンドビューアの最大の欠点が「グラフに数値が出ない」ことなので、
        ここは意地でも出す。
        """
        last = self._shots[-1]
        x = x_at(n - 1)
        values = (last.ch01, last.ch02)
        ys = [y_at(v) for v in values]

        # CH01 と CH02 が近い値だとラベルが重なって読めなくなる。
        # 近すぎる場合だけ上下へ振り分ける（値の大小関係は保つ）。
        label_ys = list(ys)
        if abs(ys[0] - ys[1]) < LABEL_MIN_SEP:
            mid = (ys[0] + ys[1]) / 2
            half = LABEL_MIN_SEP / 2
            if ys[0] <= ys[1]:
                label_ys = [mid - half, mid + half]
            else:
                label_ys = [mid + half, mid - half]

        # 右端にはみ出すなら左側へ回す（最新点は必ず右端付近に来る）
        anchor, dx = ("e", -11) if x + 56 > right else ("w", 11)

        for ch_index, color in enumerate(theme.CH_COLORS):
            y = ys[ch_index]
            self.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color, outline="#FFFFFF", width=1)
            self.create_text(
                x + dx,
                label_ys[ch_index],
                text=f"{values[ch_index]:.2f}",
                anchor=anchor,
                fill=color,
                font=theme.F_STAT,
            )
