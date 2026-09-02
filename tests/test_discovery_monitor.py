from __future__ import annotations

import os
from datetime import datetime, timedelta

from shottrend.core.discovery import DataRootScanner
from shottrend.core.history import ShotHistory
from shottrend.core.monitor import STATUS_IDLE, STATUS_NOROOT, STATUS_RUNNING, MonitorService

from .conftest import HEADER_LINE, data_line


def make_session_dir(root, name: str, lines: list[str], mtime: float | None = None):
    d = root / name
    d.mkdir()
    csv = d / f"{name}.csv"
    csv.write_bytes(("\r\n".join(lines) + "\r\n").encode("cp932"))
    # 生波形ファイルも置いて、これを掴まないことを確かめる
    (d / f"ALL_{name}_120000_000001.csv").write_bytes(b"Time:2026/09/01 12:00:00\r\n")
    if mtime is not None:
        os.utime(csv, (mtime, mtime))
    return csv


def test_latest_is_chosen_by_mtime_not_by_name(tmp_path):
    """罠3: 名前ソートは必ず誤答する。実在する紛らわしい名前で確かめる。"""
    base = 1_700_000_000.0
    make_session_dir(tmp_path, "separate_20260219", [HEADER_LINE], mtime=base + 100)
    make_session_dir(tmp_path, "_20260828", [HEADER_LINE], mtime=base + 200)
    make_session_dir(tmp_path, "DefaultFile001_20260216", [HEADER_LINE], mtime=base + 300)
    # 名前順では最後に来るが mtime は最も古い
    make_session_dir(tmp_path, "zz_newest_by_name_20260101", [HEADER_LINE], mtime=base)
    # 実際に今書かれているのはこれ
    newest = make_session_dir(
        tmp_path, "20260821_setting001_20260902", [HEADER_LINE], mtime=base + 999
    )

    scanner = DataRootScanner(tmp_path)
    assert scanner.latest().csv == newest
    assert len(scanner.list_sessions()) == 5


def test_same_day_two_folders(tmp_path):
    """同じ日に 2 フォルダ併存する実データのケース。"""
    base = 1_700_000_000.0
    make_session_dir(tmp_path, "20260821_setting001_20260902", [HEADER_LINE], mtime=base)
    live = make_session_dir(
        tmp_path, "20260902_setting001_20260902", [HEADER_LINE], mtime=base + 50
    )
    assert DataRootScanner(tmp_path).latest().csv == live


def test_waveform_files_are_never_picked(tmp_path):
    d = tmp_path / "odd_name"
    d.mkdir()
    (d / "ALL_odd_name_120000_000001.csv").write_bytes(b"Time:x\r\n")
    assert DataRootScanner(tmp_path).list_sessions() == []


def test_missing_root_returns_empty(tmp_path):
    assert DataRootScanner(tmp_path / "nope").list_sessions() == []


def test_monitor_reads_and_follows(tmp_path):
    base = 1_700_000_000.0
    make_session_dir(
        tmp_path,
        "20260901_setting_20260901",
        [HEADER_LINE, data_line(1, "2026/09/01 10:00:00", 50.0, 51.0)],
        mtime=base,
    )
    svc = MonitorService(DataRootScanner(tmp_path), ShotHistory())
    now = datetime(2026, 9, 1, 10, 0, 10)

    r = svc.poll(now=now, rescan=True)
    assert r.session_changed
    assert [s.shot_no for s in r.new_shots] == [1]
    assert r.status == STATUS_RUNNING

    # 新しいフォルダが現れたら追従する
    make_session_dir(
        tmp_path,
        "20260902_setting_20260902",
        [HEADER_LINE, data_line(9, "2026/09/02 08:00:00", 60.0, 61.0)],
        mtime=base + 500,
    )
    r = svc.poll(now=datetime(2026, 9, 2, 8, 0, 5), rescan=True)
    assert r.session_changed
    assert [s.shot_no for s in r.new_shots] == [9]
    assert len(svc.history) == 1  # 切替で履歴は捨てられる


def test_monitor_does_not_follow_when_pinned(tmp_path):
    """過去日を選んでいる間は自動切替しない。"""
    base = 1_700_000_000.0
    old = make_session_dir(
        tmp_path,
        "old_20260901",
        [HEADER_LINE, data_line(1, "2026/09/01 10:00:00", 1.0, 2.0)],
        mtime=base,
    )
    make_session_dir(
        tmp_path,
        "new_20260902",
        [HEADER_LINE, data_line(9, "2026/09/02 10:00:00", 3.0, 4.0)],
        mtime=base + 500,
    )
    scanner = DataRootScanner(tmp_path)
    svc = MonitorService(scanner, ShotHistory())
    pinned = next(s for s in scanner.list_sessions() if s.csv == old)
    svc.select_session(pinned, follow=False)

    r = svc.poll(now=datetime(2026, 9, 2, 10, 0, 30), rescan=True)
    assert not r.session_changed
    assert svc.session.csv == old
    assert [s.shot_no for s in r.new_shots] == [1]


def test_no_data_root(tmp_path):
    svc = MonitorService(DataRootScanner(tmp_path / "missing"), ShotHistory())
    r = svc.poll(now=datetime(2026, 9, 1, 10, 0, 0), rescan=True)
    assert r.status == STATUS_NOROOT


def test_idle_threshold_uses_median_interval(tmp_path):
    """罠4: interval は 0〜1,288,852 秒とばらつく。固定閾値は使えない。"""
    make_session_dir(
        tmp_path,
        "s_20260901",
        [HEADER_LINE]
        + [
            data_line(i, f"2026/09/01 10:{i:02d}:00", 50.0, 51.0, interval=30.0)
            for i in range(1, 6)
        ],
        mtime=1_700_000_000.0,
    )
    svc = MonitorService(DataRootScanner(tmp_path), ShotHistory())
    last = datetime(2026, 9, 1, 10, 5, 0)
    svc.poll(now=last, rescan=True)

    # 中央値 30 × 3 = 90 だが下限 90 でクランプされる
    assert svc.idle_threshold_sec() == 90.0
    assert svc.poll(now=last + timedelta(seconds=60), rescan=False).status == STATUS_RUNNING
    assert svc.poll(now=last + timedelta(seconds=200), rescan=False).status == STATUS_IDLE


def test_idle_threshold_scales_with_long_cycles(tmp_path):
    make_session_dir(
        tmp_path,
        "s_20260901",
        [HEADER_LINE]
        + [
            data_line(i, f"2026/09/01 10:{i:02d}:00", 50.0, 51.0, interval=120.0)
            for i in range(1, 6)
        ],
        mtime=1_700_000_000.0,
    )
    svc = MonitorService(DataRootScanner(tmp_path), ShotHistory())
    svc.poll(now=datetime(2026, 9, 1, 10, 5, 0), rescan=True)
    assert svc.idle_threshold_sec() == 360.0  # 120 × 3
