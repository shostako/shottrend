"""ドメインモデル。Tk に依存しない。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# MPS08B のサマリ CSV が吐く DateTime 列の形式: 2026/09/01 13:55:46
DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"

# フォルダ名末尾の _YYYYMMDD。表示ラベルを整えるためだけに使う。
# フォルダの選別には一切使わない（罠3: 名前ソートは必ず誤答する）。
_DIR_DATE_SUFFIX = re.compile(r"_(\d{8})$")


@dataclass(frozen=True, slots=True)
class Shot:
    """1 ショット分の計測結果。shot_no が一意キー。"""

    shot_no: int
    dt: datetime
    interval: float
    ch01: float
    ch02: float

    @property
    def time_text(self) -> str:
        return self.dt.strftime("%H:%M:%S")


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
