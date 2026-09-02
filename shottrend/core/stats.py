"""統計と合成値の計算。"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from .metrics import DEFAULT_METRIC
from .models import Shot

#: テーブルの合成値列のモード。default は "max"。
COMPOSITE_MODES = ("max", "min", "avg", "diff")
COMPOSITE_LABELS = {"max": "最大", "min": "最小", "avg": "平均", "diff": "差"}


def composite(
    shot: Shot,
    mode: str,
    channels: Sequence[int] | None = None,
    metric: str = DEFAULT_METRIC,
) -> float:
    """1 ショット内の使用中チャンネルから代表値を作る。

    channels を渡さない場合は全チャンネルを対象にする。diff は最大と最小の
    差（= レンジ）。2ch なら従来どおり 2 本の差と一致する。metric で対象の
    項目を選ぶ（既定はピーク）。
    """
    if channels is None:
        values = list(shot.values.get(metric, ()))
    else:
        values = [shot.value(metric, i) for i in channels]
    if not values:
        return 0.0
    if mode == "min":
        return min(values)
    if mode == "avg":
        return statistics.fmean(values)
    if mode == "diff":
        return max(values) - min(values)
    return max(values)


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
