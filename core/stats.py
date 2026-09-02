"""統計と合成値の計算。"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from .models import Shot

#: テーブルの合成値列のモード。default は "max"。
COMPOSITE_MODES = ("max", "min", "avg", "diff")
COMPOSITE_LABELS = {"max": "最大", "min": "最小", "avg": "平均", "diff": "差"}


def composite(shot: Shot, mode: str) -> float:
    """1 ショット内の CH01 / CH02 から代表値を作る。"""
    a, b = shot.ch01, shot.ch02
    if mode == "min":
        return min(a, b)
    if mode == "avg":
        return (a + b) / 2.0
    if mode == "diff":
        return abs(a - b)
    return max(a, b)


@dataclass(frozen=True, slots=True)
class ChannelStats:
    n: int
    max: float
    min: float
    avg: float
    sd: float

    @property
    def empty(self) -> bool:
        return self.n == 0


EMPTY_STATS = ChannelStats(n=0, max=0.0, min=0.0, avg=0.0, sd=0.0)


def window_stats(values: Sequence[float]) -> ChannelStats:
    """表示中の窓に対する統計。sd は母標準偏差 (n<2 なら 0)。"""
    if not values:
        return EMPTY_STATS
    return ChannelStats(
        n=len(values),
        max=max(values),
        min=min(values),
        avg=statistics.fmean(values),
        sd=statistics.pstdev(values) if len(values) > 1 else 0.0,
    )
