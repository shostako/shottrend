"""テスト用の合成 CSV を組み立てるヘルパー。

実データ (MPS08B PPSB v1.3.0.5) の癖を再現する:
  - 104 列、末尾にもカンマ（最終列は常に空）
  - 改行は CRLF
  - ヘッダがファイル途中に何度も現れる
"""

from __future__ import annotations

import pytest

# 実データのヘッダを再現する。CH01_peak が 23、CH02_peak が 24 列目に来る。
_GROUPS = (
    "error",
    "integral",
    "peak",
    "peak_integral",
    "peak_time",
    "section_average",
    "section_integral_1",
    "section_integral_2",
    "pointMonitor",
    "eject_Monitor",
    "RisingTime",
    "FallingTime",
)

HEADER_FIELDS = ["DateTime", "interval", "Shot", "Result", "Error", "MT_State", "MD"]
for _g in _GROUPS:
    HEADER_FIELDS += [f"CH{i:02d}_{_g}" for i in range(1, 9)]

#: 末尾のカンマにより最終列は常に空になる
HEADER_LINE = ",".join(HEADER_FIELDS) + ","

assert HEADER_FIELDS.index("CH01_peak") == 23
assert HEADER_FIELDS.index("CH02_peak") == 24
assert len(HEADER_FIELDS) == 103  # 末尾カンマを足して 104 列


def data_line(
    shot_no: int,
    dt: str,
    ch01: float = 0.0,
    ch02: float = 0.0,
    interval: float = 21.9,
    peaks: tuple[float, ...] | None = None,
    extra: dict[str, tuple[float, ...]] | None = None,
) -> str:
    """1 データ行。peaks を渡すと CH01 から順にその値を入れる。

    extra は項目キー → CH01 から順の値。ピーク以外の列を埋めたいときに使う。
    """
    fields = [""] * len(HEADER_FIELDS)
    fields[0] = dt
    fields[1] = f"{interval:.2f}"
    fields[2] = str(shot_no)
    fields[3] = "-"
    for i in range(7, len(fields)):
        fields[i] = "0.00"
    values = peaks if peaks is not None else (ch01, ch02)
    base = HEADER_FIELDS.index("CH01_peak")
    for i, v in enumerate(values):
        fields[base + i] = f"{v:.2f}"
    for key, seq in (extra or {}).items():
        start = HEADER_FIELDS.index(f"CH01_{key}")
        for i, v in enumerate(seq):
            fields[start + i] = (
                f"{v:.3f}" if key.endswith("time") or key.endswith("Time") else f"{v:.2f}"
            )
    return ",".join(fields) + ","


def build_csv(lines: list[str]) -> bytes:
    """CRLF で連結する。lines には HEADER_LINE と data_line を混ぜてよい。"""
    return ("\r\n".join(lines) + "\r\n").encode("cp932")


@pytest.fixture
def summary_csv(tmp_path):
    """サマリ CSV を書くファクトリ。"""

    def _write(lines: list[str], name: str = "sample.csv", terminated: bool = True) -> object:
        path = tmp_path / name
        body = "\r\n".join(lines)
        if terminated:
            body += "\r\n"
        path.write_bytes(body.encode("cp932"))
        return path

    return _write
