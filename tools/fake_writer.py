"""MPS08B のサマリ CSV 追記を模して、実機なしで動作確認できるようにする。

成形機が止まっている時間帯でもリアルタイム更新の挙動を確認・デモできる。
本物と同じ癖を再現する:
  - CRLF、104 列、末尾カンマ
  - たまにヘッダ行を挟む（= 計測の中断→再開）
  - たまにショット番号を飛ばす（= 中断中のショット）

使い方:
    python tools/fake_writer.py --root /tmp/fake_mms --interval 2
    # 別の端末（または config.json）で mms_data_dir を /tmp/fake_mms に向ける
"""

from __future__ import annotations

import argparse
import random
import time
from datetime import datetime
from pathlib import Path

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
HEADER_LINE = ",".join(HEADER_FIELDS) + ","


def _col(group: str, ch: int) -> int:
    return HEADER_FIELDS.index(f"CH{ch + 1:02d}_{group}")


def data_line(shot_no: int, when: datetime, peaks: list[float], interval: float) -> str:
    """1 行分。ピーク以外の項目も、ピークから派生させたそれらしい値で埋める。

    項目切替の動作確認用なので物理的な正しさは狙っていない。
    """
    fields = ["0.00"] * len(HEADER_FIELDS)
    fields[0] = when.strftime("%Y/%m/%d %H:%M:%S")
    fields[1] = f"{interval:.2f}"
    fields[2] = str(shot_no)
    fields[3] = "-"
    fields[4] = ""
    fields[5] = ""
    fields[6] = ""
    for i, p in enumerate(peaks):
        fields[_col("error", i)] = "-"
        fields[_col("peak", i)] = f"{p:.2f}"
        fields[_col("integral", i)] = f"{p * 2.2:.2f}"
        fields[_col("peak_integral", i)] = f"{p * 0.13:.2f}"
        fields[_col("peak_time", i)] = f"{1.2 + p * 0.004:.3f}"
        fields[_col("section_average", i)] = f"{p * 0.62:.2f}"
        fields[_col("section_integral_1", i)] = f"{p * 0.63:.2f}"
        fields[_col("section_integral_2", i)] = f"{p * 0.63:.2f}"
        fields[_col("eject_Monitor", i)] = f"{p * 0.43:.2f}"
        fields[_col("RisingTime", i)] = f"{1.1 + p * 0.004:.3f}"
    return ",".join(fields) + ","


def append(path: Path, line: str) -> None:
    with open(path, "ab") as fh:
        fh.write((line + "\r\n").encode("cp932"))


def main() -> int:
    ap = argparse.ArgumentParser(description="MPS08B サマリ CSV の追記シミュレータ")
    ap.add_argument("--root", required=True, help="MMS_DATA に相当するディレクトリ")
    ap.add_argument("--interval", type=float, default=2.0, help="1 ショットの間隔[秒]")
    ap.add_argument("--start-shot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument(
        "--channels", type=int, default=2, help="値を入れる ch 数 (1-8)。多 ch の画面確認用"
    )
    args = ap.parse_args()

    rng = random.Random(args.seed)
    root = Path(args.root)
    stamp = datetime.now().strftime("%Y%m%d")
    session = root / f"fake_setting_{stamp}"
    session.mkdir(parents=True, exist_ok=True)
    csv_path = session / f"{session.name}.csv"

    if not csv_path.exists():
        append(csv_path, HEADER_LINE)

    shot = args.start_shot
    nch = max(1, min(args.channels, 8))
    bases = [50.0 + 3.0 * i for i in range(nch)]
    print(f"writing to {csv_path} (Ctrl+C to stop)")
    try:
        while True:
            # たまに中断を挟む: ヘッダ再挿入 + ショット番号の飛び
            if rng.random() < 0.06:
                append(csv_path, HEADER_LINE)
                skipped = rng.randint(3, 25)
                shot += skipped
                print(f"  -- interruption: header re-inserted, skipped {skipped} shots")

            peaks = [b + rng.gauss(0, 1.1) for b in bases]
            append(
                csv_path,
                data_line(shot, datetime.now(), peaks, interval=args.interval + rng.gauss(0, 0.3)),
            )
            print("  shot " + str(shot) + "  " + "  ".join(f"{v:.2f}" for v in peaks))
            shot += 1
            # ゆっくりドリフトさせて傾向が見えるようにする
            bases = [b + rng.gauss(0, 0.08) for b in bases]
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
