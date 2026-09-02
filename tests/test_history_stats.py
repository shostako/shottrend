from __future__ import annotations

from datetime import datetime

from core.history import ShotHistory, find_gaps
from core.models import Shot
from core.stats import composite, window_stats


def mk(no: int, ch01: float = 10.0, ch02: float = 20.0) -> Shot:
    return Shot(no, datetime(2026, 9, 1, 10, 0, 0), 21.9, ch01, ch02)


def test_duplicate_shot_no_is_ignored():
    """冪等性の要。同じ行を二度読んでも履歴は変わらない。"""
    h = ShotHistory()
    assert len(h.add_many([mk(1), mk(2)])) == 2
    assert h.add_many([mk(1), mk(2)]) == []
    assert len(h) == 2


def test_add_many_returns_only_new():
    h = ShotHistory()
    h.add_many([mk(1), mk(2)])
    added = h.add_many([mk(2), mk(3)])
    assert [s.shot_no for s in added] == [3]


def test_latest_and_tail_keep_arrival_order():
    h = ShotHistory()
    h.add_many([mk(n) for n in (5, 6, 9, 10)])
    assert h.latest().shot_no == 10
    assert [s.shot_no for s in h.tail(2)] == [9, 10]
    assert [s.shot_no for s in h.tail(99)] == [5, 6, 9, 10]
    assert h.tail(0) == []


def test_clear():
    h = ShotHistory()
    h.add_many([mk(1)])
    h.clear()
    assert len(h) == 0
    assert h.latest() is None


def test_find_gaps_detects_interruptions():
    """罠2: 中断で番号が飛ぶ。折れ線を切る位置を出す。"""
    shots = [mk(n) for n in (1084, 1085, 1086, 1087, 1109, 1110)]
    assert find_gaps(shots) == [4]
    assert find_gaps([mk(1), mk(2), mk(3)]) == []
    assert find_gaps([]) == []
    assert find_gaps([mk(1)]) == []


def test_composite_modes():
    s = mk(1, ch01=62.74, ch02=61.90)
    assert composite(s, "max") == 62.74
    assert composite(s, "min") == 61.90
    assert composite(s, "avg") == (62.74 + 61.90) / 2
    assert round(composite(s, "diff"), 2) == 0.84
    assert composite(s, "unknown") == 62.74  # 未知のモードは max にフォールバック


def test_window_stats():
    st = window_stats([1.0, 2.0, 3.0, 4.0])
    assert st.n == 4
    assert st.max == 4.0
    assert st.min == 1.0
    assert st.avg == 2.5
    assert round(st.sd, 4) == 1.1180  # 母標準偏差

    assert window_stats([]).empty
    single = window_stats([7.0])
    assert single.sd == 0.0 and single.avg == 7.0
