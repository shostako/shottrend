"""ショット履歴の保持。

shot_no をキーにした dict で持つことが冪等性の要。差分読みのオフセットが
何らかの理由で巻き戻って同じ行を二度読んでも、履歴は変わらない。

実データで確認済みの前提 (罠2):
  ショット番号は中断で飛ぶが、巻き戻らず重複もしない。
  → 到着順 = ショット番号の昇順。dict の挿入順がそのまま時系列になる。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .models import Shot


class ShotHistory:
    def __init__(self) -> None:
        self._by_no: dict[int, Shot] = {}

    def __len__(self) -> int:
        return len(self._by_no)

    def add_many(self, shots: Iterable[Shot]) -> list[Shot]:
        """新規ショットだけを取り込み、実際に追加された分を返す。"""
        added: list[Shot] = []
        for s in shots:
            if s.shot_no in self._by_no:
                continue
            self._by_no[s.shot_no] = s
            added.append(s)
        return added

    def clear(self) -> None:
        self._by_no.clear()

    def latest(self) -> Shot | None:
        if not self._by_no:
            return None
        return next(reversed(self._by_no.values()))

    def all(self) -> list[Shot]:
        return list(self._by_no.values())

    def channel_count(self) -> int:
        """CSV から取れているチャンネル数（未接続の 0.0 も含む）。"""
        latest = self.latest()
        return len(latest.peaks) if latest else 0

    def used_channels(self) -> list[int]:
        """実際にセンサが繋がっている ch の番号（0 始まり）。

        履歴の中で一度でも非ゼロなら使用中とみなす。MPS08B は未接続の ch も
        0.00 で書き続けるため、列の有無では判別できない。
        """
        n = self.channel_count()
        if n == 0:
            return []
        used = [False] * n
        for shot in self._by_no.values():
            for i, v in enumerate(shot.peaks):
                if v != 0.0:
                    used[i] = True
        found = [i for i, flag in enumerate(used) if flag]
        # 全部ゼロ（計測直後など）のときは先頭 2ch を仮に出す
        return found if found else [0, 1][:n]

    def tail(self, n: int) -> list[Shot]:
        """直近 n 件を古い順で返す。"""
        if n <= 0:
            return []
        values = list(self._by_no.values())
        return values[-n:]


def find_gaps(shots: Sequence[Shot]) -> list[int]:
    """ショット番号が飛んでいる箇所のインデックスを返す。

    返すのは「その位置と 1 つ前の間で中断があった」を意味する i のリスト。
    グラフで折れ線を切って区切り線を引くために使う。
    """
    gaps: list[int] = []
    for i in range(1, len(shots)):
        if shots[i].shot_no != shots[i - 1].shot_no + 1:
            gaps.append(i)
    return gaps
