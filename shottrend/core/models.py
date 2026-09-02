"""ドメインモデル。Tk に依存しない。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .metrics import DEFAULT_METRIC

# MPS08B のサマリ CSV が吐く DateTime 列の形式: 2026/09/01 13:55:46
DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"

# フォルダ名末尾の _YYYYMMDD。表示ラベルを整えるためだけに使う。
# フォルダの選別には一切使わない（罠3: 名前ソートは必ず誤答する）。
_DIR_DATE_SUFFIX = re.compile(r"_(\d{8})$")


#: MPS08B はアンプ 4 台まで連結でき、8ch x 4 = 32ch まで計測できる。
MAX_CHANNELS = 32


@dataclass(frozen=True, slots=True)
class Shot:
    """1 ショット分の計測結果。shot_no が一意キー。

    values は項目キー（`core.metrics`）→ CH01 から順に並んだ値の列。実際に
    何 ch 取れるかは CSV のヘッダ次第で、センサが 2 本しか繋がっていなくても
    本体は 8ch 分の列を書く（未接続は 0.0）。ピーク（"peak"）は必ず入る。
    他の項目は CSV に列が無ければ空のまま。
    """

    shot_no: int
    dt: datetime
    interval: float
    values: dict[str, tuple[float, ...]] = field(default_factory=dict)

    @property
    def time_text(self) -> str:
        return self.dt.strftime("%H:%M:%S")

    @property
    def peaks(self) -> tuple[float, ...]:
        """ピーク値の列。センサ接続の判定にも使う基準の項目。"""
        return self.values.get(DEFAULT_METRIC, ())

    def value(self, key: str, index: int) -> float:
        """項目キーと 0 始まりのチャンネル番号で値を引く。無ければ 0.0。"""
        seq = self.values.get(key, ())
        return seq[index] if 0 <= index < len(seq) else 0.0

    def peak(self, index: int) -> float:
        """0 始まりのチャンネル番号でピーク値を引く。範囲外は 0.0。"""
        return self.value(DEFAULT_METRIC, index)


@dataclass(frozen=True, slots=True)
class Session:
    """1 つのデータフォルダ（= MPS08B が 1 日 / 1 設定ごとに作る保存先）。"""

    dir: Path
    csv: Path
    mtime: float

    @property
    def label(self) -> str:
        """ドロップダウンに出す表示名。

        末尾の _YYYYMMDD を解釈できれば "09/02  setting001" のように整形し、
        できなければフォルダ名をそのまま返す。整形は飾りなので失敗しても構わない。
        """
        name = self.dir.name
        m = _DIR_DATE_SUFFIX.search(name)
        if not m:
            return name
        stamp = m.group(1)
        head = name[: m.start()]
        try:
            d = datetime.strptime(stamp, "%Y%m%d")
        except ValueError:
            return name
        return f"{d.strftime('%m/%d')}  {head}" if head else d.strftime("%m/%d")
