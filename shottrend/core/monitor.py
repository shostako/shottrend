"""ポーリング 1 回分の判断ロジック。

Tk を一切知らないので、UI なしで pytest から丸ごと検証できる。
UI 層は poll() を呼んで結果を描くだけ。
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime

from .csvsource import SummaryCsvReader
from .discovery import DataRootScanner
from .history import ShotHistory
from .models import Session, Shot

log = logging.getLogger(__name__)

# 監視状態
STATUS_RUNNING = "running"
STATUS_IDLE = "idle"
STATUS_NODATA = "nodata"
STATUS_ERROR = "error"
STATUS_NOROOT = "noroot"

#: UI に返すメッセージ。**表示文字列ではなく翻訳キー**で、STATUS_* と同じく
#: 不透明な識別子。文言に変えるのは UI 層の仕事（core は言語を知らない）。
MSG_NO_ROOT = "msg.no_root"
MSG_READ_RETRY = "msg.read_retry"  # params: count
MSG_NO_DATA = "msg.no_data"
MSG_SKIPPED = "msg.skipped"  # params: rows

#: 無通信を「止まっている」と判断するまでの許容秒数の下限・上限。
#: 罠4: interval は実測で 0.0〜1,288,852 秒とばらつくため固定値は使えない。
#: 直近の interval の中央値 × 3 を採り、この範囲にクランプする。
IDLE_MIN_SEC = 90.0
IDLE_MAX_SEC = 600.0
IDLE_SAMPLE = 10

#: 現 CSV がこの秒数以上更新されていなければ、次ティックでフォルダを再走査する。
FORCE_RESCAN_AFTER_SEC = 60.0


@dataclass
class PollResult:
    new_shots: list[Shot] = field(default_factory=list)
    session_changed: bool = False
    session: Session | None = None
    reloaded: bool = False
    status: str = STATUS_NODATA
    message_key: str = ""
    """翻訳キー（`MSG_*`）。空なら表示するメッセージ無し。"""
    message_params: dict[str, object] = field(default_factory=dict)


class MonitorService:
    def __init__(self, scanner: DataRootScanner, history: ShotHistory) -> None:
        self.scanner = scanner
        self.history = history
        self.session: Session | None = None
        self.follow = True
        self._reader: SummaryCsvReader | None = None
        self._last_change: datetime | None = None

    # ------------------------------------------------------------------ session

    def select_session(self, session: Session, *, follow: bool) -> None:
        """対象セッションを切り替える。履歴は捨てて全部読み直す。"""
        self.session = session
        self.follow = follow
        self._reader = SummaryCsvReader(session.csv)
        self._last_change = None
        self.history.clear()

    def _needs_rescan(self, now: datetime, rescan: bool) -> bool:
        if not self.follow:
            return False
        if self.session is None or self._reader is None:
            return True
        if rescan:
            return True
        # 更新が途絶えているなら、保存先が別フォルダに移った可能性がある。
        if self._last_change is not None:
            if (now - self._last_change).total_seconds() >= FORCE_RESCAN_AFTER_SEC:
                return True
        return False

    # --------------------------------------------------------------------- poll

    def poll(self, *, now: datetime, rescan: bool = False) -> PollResult:
        session_changed = False

        if self._needs_rescan(now, rescan):
            latest = self.scanner.latest()
            if latest is None:
                if self.session is None:
                    return PollResult(status=STATUS_NOROOT, message_key=MSG_NO_ROOT)
            elif self.session is None or latest.csv != self.session.csv:
                log.info("switching session: %s", latest.csv)
                self.select_session(latest, follow=True)
                session_changed = True

        if self._reader is None or self.session is None:
            return PollResult(status=STATUS_NOROOT, message_key=MSG_NO_ROOT)

        result = self._reader.read_new()
        if not result.ok:
            return PollResult(
                session=self.session,
                session_changed=session_changed,
                status=STATUS_ERROR,
                message_key=MSG_READ_RETRY,
                message_params={"count": self._reader.fail_count},
            )

        if result.reloaded:
            # ファイルが差し替わった。履歴を捨てて読み直した内容で作り直す。
            self.history.clear()

        added = self.history.add_many(result.shots)
        if added:
            self._last_change = now

        message_key, message_params = self._message(result.skipped)
        return PollResult(
            new_shots=added,
            session_changed=session_changed,
            session=self.session,
            reloaded=result.reloaded,
            status=self._status(now),
            message_key=message_key,
            message_params=message_params,
        )

    # ------------------------------------------------------------------- status

    def idle_threshold_sec(self) -> float:
        """無通信の許容秒数。直近の interval の中央値から決める。"""
        shots = self.history.tail(IDLE_SAMPLE)
        intervals = [s.interval for s in shots if s.interval > 0]
        if not intervals:
            return IDLE_MIN_SEC
        median = statistics.median(intervals)
        return max(IDLE_MIN_SEC, min(median * 3.0, IDLE_MAX_SEC))

    def _status(self, now: datetime) -> str:
        latest = self.history.latest()
        if latest is None:
            return STATUS_NODATA
        elapsed = (now - latest.dt).total_seconds()
        return STATUS_RUNNING if elapsed <= self.idle_threshold_sec() else STATUS_IDLE

    def _message(self, skipped: int) -> tuple[str, dict[str, object]]:
        """状態帯に添えるメッセージの翻訳キーとパラメータ。"""
        if self.history.latest() is None:
            return MSG_NO_DATA, {}
        if skipped:
            return MSG_SKIPPED, {"rows": skipped}
        return "", {}
