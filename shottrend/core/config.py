"""設定の読み書き。

罠3 への対処: MMS_DATA のパスは絶対に埋め込まない。ここで保持して GUI から
変更できるようにする（調査中に実際にユーザーがアプリ一式を Desktop から
Documents へ移動した）。

書き込みは一時ファイル → os.replace で原子的に行う。途中で落ちても設定が
半端な状態で残らない。
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .metrics import DEFAULT_METRIC, METRIC_KEYS

log = logging.getLogger(__name__)

CONFIG_FILENAME = "config.json"

WINDOW_SIZES = (10, 50, 100)
CHART_KINDS = ("line", "bar")


def app_dir() -> Path:
    """アプリ本体のあるディレクトリ。

    PyInstaller で固めると __file__ は展開先の一時ディレクトリを指すため、
    frozen 判定を最初から入れておく（後付けすると必ず忘れる）。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return app_dir() / CONFIG_FILENAME


@dataclass
class AppConfig:
    mms_data_dir: str = ""
    poll_interval_ms: int = 2000
    session_rescan_ticks: int = 10
    window_size: int = 50
    chart_kind: str = "line"
    metric: str = DEFAULT_METRIC
    composite_mode: str = "max"
    show_delta_columns: bool = False
    geometry: str = "1280x880+30+16"

    def normalized(self) -> AppConfig:
        """不正な値を既定値に丸める。手で編集された config でも落ちないように。"""
        if self.window_size not in WINDOW_SIZES:
            self.window_size = 50
        if self.chart_kind not in CHART_KINDS:
            self.chart_kind = "line"
        if self.metric not in METRIC_KEYS:
            self.metric = DEFAULT_METRIC
        if self.composite_mode not in ("max", "min", "avg", "diff"):
            self.composite_mode = "max"
        self.poll_interval_ms = max(250, min(int(self.poll_interval_ms), 60_000))
        self.session_rescan_ticks = max(1, min(int(self.session_rescan_ticks), 600))
        self.show_delta_columns = bool(self.show_delta_columns)
        return self


def load_config(path: Path | None = None) -> AppConfig:
    p = path or config_path()
    if not p.is_file():
        return AppConfig()
    try:
        # utf-8-sig: メモ帳や PowerShell 5.1 の Set-Content が付ける BOM を許容する。
        # 素の utf-8 だと「Unexpected UTF-8 BOM」で丸ごと既定値に落ちる
        raw = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("config unreadable (%s), using defaults: %s", p, exc)
        return AppConfig()
    known = {f.name for f in fields(AppConfig)}
    return AppConfig(**{k: v for k, v in raw.items() if k in known}).normalized()


def save_config(cfg: AppConfig, path: Path | None = None) -> None:
    p = path or config_path()
    tmp = p.with_suffix(p.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, p)
    except OSError as exc:
        log.warning("failed to save config %s: %s", p, exc)
        tmp.unlink(missing_ok=True)
