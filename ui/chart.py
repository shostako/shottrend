"""tk.Canvas 直描きのショット推移グラフ。

横軸は等間隔のカテゴリ軸。ショット番号は目盛ラベルにのみ出す。
理由 (罠2): ショット番号は中断で飛ぶ。実数軸にすると 1087 と 1109 の間に
巨大な空白ができて、直近 10 件を見たいのに 1 点しか見えない事故になる。

描画するチャンネルは呼び出し側が渡す（使用中の ch だけ）。MPS08B は 32ch まで
計測できるため、2ch 決め打ちにしない。
"""

from __future__ import annotations

import math
import tkinter as tk

from core.history import find_gaps
from core.models import Shot

from . import theme

PAD_LEFT = 58
PAD_RIGHT = 26
PAD_TOP = 26
PAD_BOTTOM = 40

RESIZE_DEBOUNCE_MS = 120

#: 最新値ラベルが重ならないための最小間隔[px]
LABEL_MIN_SEP = 15

#: 中断ラベルを段違いにする条件と段数
GAP_LABEL_MIN_DX = 46
GAP_LABEL_ROWS = 3
GAP_LABEL_ROW_H = 13

#: これを超える ch 数では最新値ラベルを出さない（重なって読めなくなる）
LABEL_MAX_CHANNELS = 4


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


def _spread_labels(ys: list[float], min_sep: float) -> list[float]:
    """近すぎるラベルを縦に押し広げる。上下の順序は保つ。"""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    out = list(ys)
    for k in range(1, len(order)):
        prev, cur = order[k - 1], order[k]
        if out[cur] - out[prev] < min_sep:
            out[cur] = out[prev] + min_sep
    return out


class ShotChart(tk.Canvas):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            background=theme.PLOT_BG,
            highlightthickness=0,
            bd=0,
        )
        self._shots: list[Shot] = []
        self._channels: list[int] = []
        self._kind = "line"
        self._resize_job: str | None = None
        self.bind("<Configure>", self._on_configure)

    # ------------------------------------------------------------------ public

    def set_data(self, shots: list[Shot], channels: list[int], kind: str) -> None:
        self._shots = shots
        self._channels = channels
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

    def _values(self) -> list[float]:
        return [s.peak(c) for s in self._shots for c in self._channels]

    def _y_domain(self) -> tuple[float, float]:
        values = self._values()
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

        if n == 0 or not self._channels:
            self.create_text(
                (left + right) // 2,
                (top + bottom) // 2,
                text="データなし",
                fill=theme.ON_PLOT_DIM,
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
            self._draw_bars(x_at, y_at, y_min, slot_w)
        else:
            self._draw_lines(x_at, y_at, gaps)
        self._draw_gap_marks(gaps, x_at, slot_w, top, bottom)
        self._draw_x_labels(x_at, bottom, n)
        self._draw_latest(x_at, y_at, n, right)

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
                fill=theme.ON_PLOT_DIM,
                font=theme.F_SMALL,
            )
            v += step
        self.create_line(left, top, left, bottom, fill=theme.AXIS)
        self.create_line(left, bottom, right, bottom, fill=theme.AXIS)
        self.create_text(
            left - 8, top - 14, text="MPa", anchor="e", fill=theme.ON_PLOT_DIM, font=theme.F_SMALL
        )

    def _draw_lines(self, x_at, y_at, gaps: set[int]) -> None:
        n = len(self._shots)
        radius = 3 if n <= 50 else 2
        for ch in self._channels:
            color = theme.ch_color(ch)
            # 中断をまたいで線を繋がない。繋ぐと連続した変化に見えてしまう。
            segment: list[float] = []
            for i, shot in enumerate(self._shots):
                if i in gaps and segment:
                    self._flush_segment(segment, color)
                    segment = []
                segment.extend((x_at(i), y_at(shot.peak(ch))))
            self._flush_segment(segment, color)

            for i, shot in enumerate(self._shots):
                x, y = x_at(i), y_at(shot.peak(ch))
                self.create_oval(
                    x - radius, y - radius, x + radius, y + radius, fill=color, outline=""
                )

    def _flush_segment(self, coords: list[float], color: str) -> None:
        if len(coords) >= 4:
            self.create_line(*coords, fill=color, width=2, smooth=False)

    def _draw_bars(self, x_at, y_at, y_min, slot_w) -> None:
        m = len(self._channels)
        usable = slot_w * 0.72
        bar_w = max(1.5, usable / m)
        base_y = y_at(max(y_min, 0.0))
        for i, shot in enumerate(self._shots):
            x0_group = x_at(i) - usable / 2
            for k, ch in enumerate(self._channels):
                x0 = x0_group + bar_w * k
                self.create_rectangle(
                    x0,
                    y_at(shot.peak(ch)),
                    x0 + bar_w * 0.86,
                    base_y,
                    fill=theme.ch_color(ch),
                    outline="",
                )

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
                fill=theme.ON_PLOT_DIM,
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
                fill=theme.ON_PLOT if is_last else theme.ON_PLOT_DIM,
                font=theme.F_SMALL,
            )
        self.create_text(
            x_at(n - 1) if n else 0,
            bottom + 20,
            text="shot",
            anchor="n",
            fill=theme.ON_PLOT_DIM,
            font=theme.F_SMALL,
        )

    def _draw_latest(self, x_at, y_at, n: int, right: int) -> None:
        """最新ショットを強調し、数値を併記する。

        純正トレンドビューアの最大の欠点が「グラフに数値が出ない」ことなので、
        ここは意地でも出す。ただし ch が多いとラベルだけで埋まるため、
        本数が増えたらマーカーの強調だけに留める。
        """
        last = self._shots[-1]
        x = x_at(n - 1)
        ys = [y_at(last.peak(ch)) for ch in self._channels]

        for ch, y in zip(self._channels, ys, strict=True):
            self.create_oval(
                x - 5, y - 5, x + 5, y + 5, fill=theme.ch_color(ch), outline="#FFFFFF", width=1
            )

        if len(self._channels) > LABEL_MAX_CHANNELS:
            return

        label_ys = _spread_labels(ys, LABEL_MIN_SEP)
        # 右端にはみ出すなら左側へ回す（最新点は必ず右端付近に来る）
        anchor, dx = ("e", -11) if x + 56 > right else ("w", 11)
        for ch, ly in zip(self._channels, label_ys, strict=True):
            self.create_text(
                x + dx,
                ly,
                text=f"{last.peak(ch):.2f}",
                anchor=anchor,
                fill=theme.ch_color(ch),
                font=theme.F_STAT,
            )
