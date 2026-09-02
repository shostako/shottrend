"""SummaryCsvReader の差分読み。実データで確認した癖を全部ここで殴る。"""

from __future__ import annotations

from shottrend.core.csvsource import SummaryCsvReader

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
    assert r.shots[0].peak(0) == 62.74
    assert r.shots[0].peak(1) == 61.90
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
    assert r.shots[0].peak(0) == 52.0


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
    assert r.shots[0].peak(0) == 12.5


def test_reads_all_eight_channels(summary_csv):
    """MPS08B はセンサが 2 本でも 8ch 分の列を書く。全部読めること。"""
    p = summary_csv(
        [
            HEADER_LINE,
            data_line(1, "2026/09/01 10:00:00", peaks=(50.0, 51.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
        ]
    )
    r = SummaryCsvReader(p).read_new()
    assert len(r.shots[0].peaks) == 8
    assert r.shots[0].peaks[:2] == (50.0, 51.0)
    assert r.shots[0].peak(0) == 50.0
    assert r.shots[0].peak(1) == 51.0


def test_reads_channels_beyond_two(summary_csv):
    """アンプを増やして 3ch 目以降が使われても読める。"""
    p = summary_csv(
        [
            HEADER_LINE,
            data_line(7, "2026/09/01 10:00:00", peaks=(10.0, 20.0, 30.0, 40.0, 0.0, 0.0, 0.0, 0.0)),
        ]
    )
    r = SummaryCsvReader(p).read_new()
    assert r.shots[0].peaks[:4] == (10.0, 20.0, 30.0, 40.0)
    assert r.shots[0].peak(3) == 40.0
    assert r.shots[0].peak(99) == 0.0  # 範囲外は 0.0


def test_reads_other_metrics_by_column_name(summary_csv):
    """ピーク以外の項目も列名で拾う。"""
    p = summary_csv(
        [
            HEADER_LINE,
            data_line(
                1,
                "2026/09/01 10:00:00",
                peaks=(65.27, 68.06),
                extra={"integral": (146.11, 150.2), "peak_time": (1.425, 1.5)},
            ),
        ]
    )
    r = SummaryCsvReader(p).read_new()
    s = r.shots[0]
    assert s.value("integral", 0) == 146.11
    assert s.value("peak_time", 1) == 1.5
    assert len(s.values["integral"]) == 8
    # 書いていない項目は 0.0 で埋まる
    assert s.value("RisingTime", 0) == 0.0
    # error 列は項目として持たない
    assert "error" not in s.values


def test_fallback_colmap_covers_other_metrics(summary_csv):
    """ヘッダ無しで途中から読んでも、ピーク以外の項目が正しい列から取れる。"""
    p = summary_csv(
        [data_line(3, "2026/09/01 10:00:00", peaks=(1.0, 2.0), extra={"eject_Monitor": (28.47,)})]
    )
    r = SummaryCsvReader(p).read_new()
    assert r.shots[0].value("eject_Monitor", 0) == 28.47


def test_header_without_optional_metric_columns(summary_csv):
    """ピークさえあれば、他の項目の列が無いヘッダでも読める。"""
    header = "DateTime,interval,Shot,CH01_peak,CH02_peak,"
    row = "2026/09/01 10:00:00,21.90,5,60.00,61.00,"
    p = summary_csv([header, row])
    r = SummaryCsvReader(p).read_new()
    assert r.skipped == 0
    assert r.shots[0].peaks == (60.0, 61.0)
    assert r.shots[0].value("integral", 0) == 0.0


def test_unparsable_optional_metric_does_not_drop_the_row(summary_csv):
    """ピークが読めていれば、他の項目が壊れていても行を捨てない。"""
    header = "DateTime,interval,Shot,CH01_peak,CH01_peak_time,"
    row = "2026/09/01 10:00:00,21.90,5,60.00,abc,"
    p = summary_csv([header, row])
    r = SummaryCsvReader(p).read_new()
    assert r.skipped == 0
    assert r.shots[0].peak(0) == 60.0
    assert r.shots[0].value("peak_time", 0) == 0.0


#: PPSB v1.3.0.5 の実機が書くヘッダ行そのもの（成形条件は含まないので置いてよい）。
#: conftest の合成ヘッダとは独立したオラクル。2026-02-16〜09-02 の全 36 ファイルで
#: このヘッダ 1 種類しか観測されていない
REAL_HEADER_1_3_0_5 = "DateTime,interval,Shot,Result,Error,MT_State,MD,CH01_error,CH02_error,CH03_error,CH04_error,CH05_error,CH06_error,CH07_error,CH08_error,CH01_integral,CH02_integral,CH03_integral,CH04_integral,CH05_integral,CH06_integral,CH07_integral,CH08_integral,CH01_peak,CH02_peak,CH03_peak,CH04_peak,CH05_peak,CH06_peak,CH07_peak,CH08_peak,CH01_peak_integral,CH02_peak_integral,CH03_peak_integral,CH04_peak_integral,CH05_peak_integral,CH06_peak_integral,CH07_peak_integral,CH08_peak_integral,CH01_peak_time,CH02_peak_time,CH03_peak_time,CH04_peak_time,CH05_peak_time,CH06_peak_time,CH07_peak_time,CH08_peak_time,CH01_section_average,CH02_section_average,CH03_section_average,CH04_section_average,CH05_section_average,CH06_section_average,CH07_section_average,CH08_section_average,CH01_section_integral_1,CH02_section_integral_1,CH03_section_integral_1,CH04_section_integral_1,CH05_section_integral_1,CH06_section_integral_1,CH07_section_integral_1,CH08_section_integral_1,CH01_section_integral_2,CH02_section_integral_2,CH03_section_integral_2,CH04_section_integral_2,CH05_section_integral_2,CH06_section_integral_2,CH07_section_integral_2,CH08_section_integral_2,CH01_pointMonitor,CH02_pointMonitor,CH03_pointMonitor,CH04_pointMonitor,CH05_pointMonitor,CH06_pointMonitor,CH07_pointMonitor,CH08_pointMonitor,CH01_eject_Monitor,CH02_eject_Monitor,CH03_eject_Monitor,CH04_eject_Monitor,CH05_eject_Monitor,CH06_eject_Monitor,CH07_eject_Monitor,CH08_eject_Monitor,CH01_RisingTime,CH02_RisingTime,CH03_RisingTime,CH04_RisingTime,CH05_RisingTime,CH06_RisingTime,CH07_RisingTime,CH08_RisingTime,CH01_FallingTime,CH02_FallingTime,CH03_FallingTime,CH04_FallingTime,CH05_FallingTime,CH06_FallingTime,CH07_FallingTime,CH08_FallingTime,"


def test_fallback_colmap_matches_real_header():
    """ヘッダ無しフォールバックの列位置が、実機のヘッダから引いた位置と一致する。

    フォールバックは列位置の決め打ちなので、並びが違ってもエラーにならず
    それらしい間違った値を返す。実機ヘッダ（conftest とは別の写し）と突き合わせる。
    """
    from shottrend.core.csvsource import _FALLBACK_COLMAP, _build_colmap

    fields = REAL_HEADER_1_3_0_5.split(",")
    assert len(fields) == 104
    cm = _build_colmap(fields)
    assert cm is not None
    assert cm.base == _FALLBACK_COLMAP.base
    assert cm.metrics == _FALLBACK_COLMAP.metrics
    assert set(cm.metrics) == {
        "peak",
        "integral",
        "peak_integral",
        "peak_time",
        "section_average",
        "section_integral_1",
        "section_integral_2",
        "pointMonitor",
        "eject_Monitor",
        "RisingTime",
        "FallingTime",
    }
