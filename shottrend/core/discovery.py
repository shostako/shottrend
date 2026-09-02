"""MMS_DATA 配下からデータフォルダ (Session) を見つける。

罠3: フォルダ名で並べ替えてはいけない。実在する名前:
       separate_20260219 / _20260828 / DefaultFile001_20260216
     さらに同じ日に 2 フォルダ併存する:
       20260821_setting001_20260902 と 20260902_setting001_20260902
     どちらが「今書かれている方」かは名前からは決して分からない。
     → CSV の mtime で判定する。
"""

from __future__ import annotations

import logging
from pathlib import Path

from .models import Session

log = logging.getLogger(__name__)

#: 生波形ファイルの接頭辞。サマリ CSV と取り違えないよう除外する。
WAVEFORM_PREFIX = "ALL_"


def _summary_csv_in(d: Path) -> Path | None:
    """フォルダ内のサマリ CSV を特定する。

    MPS08B は <dir>/<dir>.csv という規則で作る（実測: 全 36 フォルダで一致）。
    規則から外れた場合の保険として、ALL_ で始まらない CSV が 1 本だけなら
    それを採用する。
    """
    primary = d / f"{d.name}.csv"
    if primary.is_file():
        return primary
    candidates = [p for p in d.glob("*.csv") if not p.name.startswith(WAVEFORM_PREFIX)]
    if len(candidates) == 1:
        return candidates[0]
    return None


class DataRootScanner:
    """MMS_DATA ルートを走査する。"""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def list_sessions(self) -> list[Session]:
        """CSV の mtime 降順で Session を返す。"""
        sessions: list[Session] = []
        try:
            entries = list(self.root.iterdir())
        except OSError as exc:
            log.warning("cannot list data root %s: %s", self.root, exc)
            return []

        for d in entries:
            if not d.is_dir():
                continue
            csv_path = _summary_csv_in(d)
            if csv_path is None:
                continue
            try:
                mtime = csv_path.stat().st_mtime
            except OSError:
                continue
            sessions.append(Session(dir=d, csv=csv_path, mtime=mtime))

        sessions.sort(key=lambda s: s.mtime, reverse=True)
        return sessions

    def latest(self) -> Session | None:
        sessions = self.list_sessions()
        return sessions[0] if sessions else None
