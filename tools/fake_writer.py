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

CH01_INDEX = HEADER_FIELDS.index("CH01_peak")
CH02_INDEX = HEADER_FIELDS.index("CH02_peak")


def data_line(shot_no: int, when: datetime, ch01: float, ch02: float, interval: float) -> str:
    fields = ["0.00"] * len(HEADER_FIELDS)
    fields[0] = when.strftime("%Y/%m/%d %H:%M:%S")
    fields[1] = f"{interval:.2f}"
    fields[2] = str(shot_no)
    fields[3] = "-"
    fields[4] = ""
    fields[5] = ""
    fields[6] = ""
    fields[CH01_INDEX] = f"{ch01:.2f}"
    fields[CH02_INDEX] = f"{ch02:.2f}"
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
    base01, base02 = 52.0, 55.0
    print(f"writing to {csv_path} (Ctrl+C to stop)")
    try:
        while True:
            # たまに中断を挟む: ヘッダ再挿入 + ショット番号の飛び
            if rng.random() < 0.06:
                append(csv_path, HEADER_LINE)
                skipped = rng.randint(3, 25)
                shot += skipped
                print(f"  -- interruption: header re-inserted, skipped {skipped} shots")

            ch01 = base01 + rng.gauss(0, 1.2)
            ch02 = base02 + rng.gauss(0, 1.0)
            append(
                csv_path,
                data_line(
                    shot, datetime.now(), ch01, ch02, interval=args.interval + rng.gauss(0, 0.3)
                ),
            )
            print(f"  shot {shot}  CH01={ch01:.2f}  CH02={ch02:.2f}")
            shot += 1
            # ゆっくりドリフトさせて傾向が見えるようにする
            base01 += rng.gauss(0, 0.08)
            base02 += rng.gauss(0, 0.08)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
