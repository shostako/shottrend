"""MPS08B のサマリ CSV を差分読みする。

このモジュールが本アプリで最も壊れやすい場所なので、実データで確認した癖を
すべてここに閉じ込めてある。

罠1: 計測を中断→再開するたびにヘッダ行がファイル途中へ再挿入される。
     実測で 247 行中 6 回。素朴に csv.DictReader へ渡すと落ちる。
罠2: ショット番号は飛ぶが巻き戻らない。重複もない。
罠5: 改行は CRLF。ヘッダ末尾にもカンマがあるので最終列は常に空。
罠6: 追記中に読むと最終行が途中で切れていることがある。

状態の持ち方:
  _offset  … ファイル上で読み込み終えた位置（次回の seek 位置）。
  _pending … 読んだが行として完結していない末尾の断片。次回の先頭に連結される。

  この 2 つで「読み込み位置」と「行の完結」を分離している。stat/read が例外を
  投げた場合は _offset を一切進めないので、次のティックで同じ位置から再試行できる。
  同じ行を二度読んでも ShotHistory が shot_no で弾くため結果は変わらない (冪等)。
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .models import DATETIME_FORMAT, Shot

log = logging.getLogger(__name__)

#: ヘッダ行の 1 列目。この文字列でヘッダ行を判別する。
HEADER_FIRST_FIELD = "DateTime"

#: 実際に使う列。位置ではなく名前で引く（列順が変わっても壊れないように）。
COL_DATETIME = "DateTime"
COL_INTERVAL = "interval"
COL_SHOT = "Shot"
COL_CH01 = "CH01_peak"
COL_CH02 = "CH02_peak"
REQUIRED_COLUMNS = (COL_DATETIME, COL_INTERVAL, COL_SHOT, COL_CH01, COL_CH02)

#: ヘッダに一度も遭遇しないままデータ行に当たった場合のフォールバック。
#: PPSB v1.3.0.5 の 104 列レイアウトにおける各列の位置。
_FALLBACK_COLMAP = {
    COL_DATETIME: 0,
    COL_INTERVAL: 1,
    COL_SHOT: 2,
    COL_CH01: 23,
    COL_CH02: 24,
}


@dataclass
class ReadResult:
    """1 回の read_new() の結果。"""

    shots: list[Shot] = field(default_factory=list)
    reloaded: bool = False
    """ファイルが縮んだ / 差し替わったため先頭から読み直したか。"""
    skipped: int = 0
    """壊れた行・途中で切れた行として捨てた行数。"""
    error: str | None = None
    """読み取り自体に失敗した場合の理由。次回ティックで再試行される。"""

    @property
    def ok(self) -> bool:
        return self.error is None


def _parse_row(fields: list[str], colmap: dict[str, int]) -> Shot | None:
    """1 データ行を Shot にする。壊れていれば None。"""
    try:
        dt = datetime.strptime(fields[colmap[COL_DATETIME]].strip(), DATETIME_FORMAT)
        shot_no = int(fields[colmap[COL_SHOT]])
        interval = float(fields[colmap[COL_INTERVAL]])
        ch01 = float(fields[colmap[COL_CH01]])
        ch02 = float(fields[colmap[COL_CH02]])
    except (KeyError, IndexError, ValueError):
        return None
    return Shot(shot_no=shot_no, dt=dt, interval=interval, ch01=ch01, ch02=ch02)


def _build_colmap(header_fields: list[str]) -> dict[str, int] | None:
    """ヘッダ行から必要列の位置を引く。1 つでも欠けたら None。"""
    index = {name.strip(): i for i, name in enumerate(header_fields)}
    try:
        return {name: index[name] for name in REQUIRED_COLUMNS}
    except KeyError:
        return None


class SummaryCsvReader:
    """1 本のサマリ CSV を追従する。

    read_new() を繰り返し呼ぶと、前回以降に追記された行だけが返る。
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._offset = 0
        self._colmap: dict[str, int] | None = None
        self._pending = b""
        self._fail_count = 0

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def fail_count(self) -> int:
        return self._fail_count

    def reset(self) -> None:
        """先頭から読み直す状態に戻す。"""
        self._offset = 0
        self._colmap = None
        self._pending = b""

    def read_new(self) -> ReadResult:
        """前回以降に追記された行を読む。例外は投げない。"""
        try:
            size = self.path.stat().st_size
        except OSError as exc:
            # ファイルが一時的に見えない（削除中・差し替え中・ネットワーク断）。
            # offset は据え置いて次回に賭ける。
            self._fail_count += 1
            return ReadResult(error=f"stat failed: {exc}")

        reloaded = False
        if size < self._offset:
            # 切り詰められた or 別のファイルに差し替わった。先頭から読み直す。
            log.info(
                "file shrank (%d < %d), reloading from start: %s", size, self._offset, self.path
            )
            self.reset()
            reloaded = True
        elif size == self._offset:
            # 何も増えていない。ここで抜けるのが最大の最適化（再描画も起きない）。
            self._fail_count = 0
            return ReadResult()

        try:
            with open(self.path, "rb") as fh:
                fh.seek(self._offset)
                chunk = fh.read()
        except OSError as exc:
            self._fail_count += 1
            return ReadResult(reloaded=reloaded, error=f"read failed: {exc}")

        self._fail_count = 0
        buf = self._pending + chunk

        # 罠6: 末尾が改行で終わっていない断片は「まだ書き込み中の行」とみなす。
        cut = buf.rfind(b"\n")
        if cut < 0:
            # 完全な行が 1 つもない。全部を保留にして offset は進めない。
            self._pending = buf
            self._offset += len(chunk)
            return ReadResult(reloaded=reloaded)

        complete, self._pending = buf[: cut + 1], buf[cut + 1 :]
        # _offset は読み込み位置なので読んだ分だけ進める。
        # 行として未完結な末尾は _pending が持っているので取りこぼさない。
        self._offset += len(chunk)

        shots: list[Shot] = []
        skipped = 0
        for raw in complete.split(b"\n"):
            line = raw.rstrip(b"\r")
            if not line.strip():
                continue
            text = line.decode("cp932", errors="replace")
            try:
                fields = next(csv.reader(io.StringIO(text)))
            except (csv.Error, StopIteration):
                skipped += 1
                continue
            if not fields:
                continue

            # 罠1: ヘッダ行はスキップするだけでなく、列マップを作り直す。
            if fields[0].strip() == HEADER_FIRST_FIELD:
                colmap = _build_colmap(fields)
                if colmap is None:
                    log.warning("header lacks required columns: %s", self.path)
                    skipped += 1
                else:
                    self._colmap = colmap
                continue

            colmap = self._colmap
            if colmap is None:
                # 途中から読み始めてヘッダを見ていない場合の保険。
                colmap = _FALLBACK_COLMAP
            shot = _parse_row(fields, colmap)
            if shot is None:
                skipped += 1
                continue
            shots.append(shot)

        return ReadResult(shots=shots, reloaded=reloaded, skipped=skipped)
