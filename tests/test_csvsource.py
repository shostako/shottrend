"""SummaryCsvReader の差分読み。実データで確認した癖を全部ここで殴る。"""

from __future__ import annotations

from core.csvsource import SummaryCsvReader

from .conftest import HEADER_LINE, data_line


def test_full_read(summary_csv):
    p = summary_csv(
        [
            HEADER_LINE,
            data_line(1260, "2026/09/01 13:55:46", 62.74, 61.90),
            data_line(1261, "2026/09/01 13:56:08", 62.47, 62.01),
        ]
    )
    r = SummaryCsvReader(p).read_new()
    assert r.ok
    assert [s.shot_no for s in r.shots] == [1260, 1261]
    assert r.shots[0].ch01 == 62.74
    assert r.shots[0].ch02 == 61.90
    assert r.shots[0].dt.hour == 13
    assert r.skipped == 0


def test_incremental_read_returns_only_new_rows(summary_csv):
    p = summary_csv([HEADER_LINE, data_line(1, "2026/09/01 10:00:00", 50.0, 51.0)])
    reader = SummaryCsvReader(p)
    assert len(reader.read_new().shots) == 1

    # 何も増えていなければ何も返らない
    assert reader.read_new().shots == []

    with open(p, "ab") as fh:
        fh.write((data_line(2, "2026/09/01 10:00:22", 52.0, 53.0) + "\r\n").encode("cp932"))
    r = reader.read_new()
    assert [s.shot_no for s in r.shots] == [2]


def test_partial_line_is_held_until_terminated(summary_csv):
    """罠6: 書き込み途中の行は完結するまで採用しない。"""
    p = summary_csv([HEADER_LINE, data_line(1, "2026/09/01 10:00:00", 50.0, 51.0)])
    reader = SummaryCsvReader(p)
    assert len(reader.read_new().shots) == 1

    # 改行なしで途中まで書く
    partial = data_line(2, "2026/09/01 10:00:22", 52.0, 53.0)
    head, tail = partial[:40], partial[40:]
    with open(p, "ab") as fh:
        fh.write(head.encode("cp932"))
    r = reader.read_new()
    assert r.shots == []
    assert r.skipped == 0  # 「壊れた行」ではなく「まだ来ていない行」

    # 残りと改行が来たら 1 件として読める
    with open(p, "ab") as fh:
        fh.write((tail + "\r\n").encode("cp932"))
    r = reader.read_new()
    assert [s.shot_no for s in r.shots] == [2]
    assert r.shots[0].ch01 == 52.0


def test_header_reinserted_midfile(summary_csv):
    """罠1: 中断→再開でヘッダが途中に挟まる。実データでは 247 行中 6 回。"""
    p = summary_csv(
        [
            HEADER_LINE,
            data_line(966, "2026/08/31 09:16:46", 60.0, 61.0),
            HEADER_LINE,
            data_line(970, "2026/08/31 09:39:20", 62.0, 63.0),
            HEADER_LINE,
            data_line(1026, "2026/08/31 10:26:57", 64.0, 65.0),
        ]
    )
    r = SummaryCsvReader(p).read_new()
    assert r.ok
    assert [s.shot_no for s in r.shots] == [966, 970, 1026]
    assert r.skipped == 0


def test_header_arriving_incrementally(summary_csv):
    """差分読みの途中で新しいヘッダが来ても壊れない。"""
    p = summary_csv([HEADER_LINE, data_line(1, "2026/09/01 10:00:00", 50.0, 51.0)])
    reader = SummaryCsvReader(p)
    reader.read_new()
    with open(p, "ab") as fh:
        fh.write((HEADER_LINE + "\r\n").encode("cp932"))
        fh.write((data_line(9, "2026/09/01 11:00:00", 55.0, 56.0) + "\r\n").encode("cp932"))
    r = reader.read_new()
    assert [s.shot_no for s in r.shots] == [9]


def test_truncated_file_triggers_full_reload(summary_csv):
    p = summary_csv(
        [
            HEADER_LINE,
            data_line(1, "2026/09/01 10:00:00", 50.0, 51.0),
            data_line(2, "2026/09/01 10:00:22", 52.0, 53.0),
        ]
    )
    reader = SummaryCsvReader(p)
    assert len(reader.read_new().shots) == 2

    # ファイルが短く書き直された（＝別の計測に差し替わった）
    p.write_bytes(
        (
            "\r\n".join([HEADER_LINE, data_line(7, "2026/09/02 08:00:00", 40.0, 41.0)]) + "\r\n"
        ).encode("cp932")
    )
    r = reader.read_new()
    assert r.reloaded is True
    assert [s.shot_no for s in r.shots] == [7]


def test_broken_rows_are_skipped_not_raised(summary_csv):
    p = summary_csv(
        [
            HEADER_LINE,
            data_line(1, "2026/09/01 10:00:00", 50.0, 51.0),
            "これは,壊れた,行",
            "2026/09/01 10:00:44,21.9,NOT_A_NUMBER," + ",".join([""] * 99),
            data_line(3, "2026/09/01 10:01:06", 54.0, 55.0),
        ]
    )
    r = SummaryCsvReader(p).read_new()
    assert r.ok
    assert [s.shot_no for s in r.shots] == [1, 3]
    assert r.skipped == 2


def test_header_only_file_yields_nothing(summary_csv):
    """罠5: データ 0 行のサマリ CSV が実データに 10 本ある。"""
    p = summary_csv([HEADER_LINE])
    r = SummaryCsvReader(p).read_new()
    assert r.ok
    assert r.shots == []


def test_empty_file(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_bytes(b"")
    r = SummaryCsvReader(p).read_new()
    assert r.ok
    assert r.shots == []


def test_missing_file_reports_error_without_raising(tmp_path):
    reader = SummaryCsvReader(tmp_path / "nope.csv")
    r = reader.read_new()
    assert not r.ok
    assert r.shots == []
    assert reader.fail_count == 1
    assert reader.offset == 0  # 失敗しても位置を進めない


def test_missing_file_then_recovers(summary_csv, tmp_path):
    path = tmp_path / "late.csv"
    reader = SummaryCsvReader(path)
    assert not reader.read_new().ok

    path.write_bytes(
        (
            "\r\n".join([HEADER_LINE, data_line(5, "2026/09/01 12:00:00", 30.0, 31.0)]) + "\r\n"
        ).encode("cp932")
    )
    r = reader.read_new()
    assert r.ok
    assert [s.shot_no for s in r.shots] == [5]
    assert reader.fail_count == 0


def test_reset_is_idempotent(summary_csv):
    p = summary_csv(
        [
            HEADER_LINE,
            data_line(1, "2026/09/01 10:00:00", 50.0, 51.0),
            data_line(2, "2026/09/01 10:00:22", 52.0, 53.0),
        ]
    )
    reader = SummaryCsvReader(p)
    first = reader.read_new().shots
    reader.reset()
    second = reader.read_new().shots
    assert first == second


def test_data_before_any_header_uses_fallback_colmap(summary_csv):
    """途中から読み始めてヘッダを見ていない場合の保険。"""
    p = summary_csv([data_line(42, "2026/09/01 10:00:00", 12.5, 13.5)])
    r = SummaryCsvReader(p).read_new()
    assert [s.shot_no for s in r.shots] == [42]
    assert r.shots[0].ch01 == 12.5
