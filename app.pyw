"""ShotTrend エントリポイント。

pythonw.exe (窓なし) で起動されると sys.stdout が None になるため、
その場合はログをファイルへ回す。py.exe で手動起動したときは画面に出す。

PyInstaller で固めた exe でも同じファイル。frozen のとき __file__ は展開先の
一時ディレクトリを指すので、ログと設定の置き場は exe の隣に固定する。
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import tkinter as tk
from pathlib import Path

if not getattr(sys, "frozen", False):
    # ソース実行: パッケージを見つけられるように、このファイルの隣を先頭に足す
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from shottrend.core.config import app_dir  # noqa: E402

# ログと設定の置き場。判定は core.config.app_dir() の 1 箇所に寄せる。
# frozen なら exe の隣（onefile は起動ごとに一時ディレクトリへ展開されるので
# __file__ 基準だと終了時に消える）、ソース実行なら app.pyw の隣
APP_DIR = app_dir()

LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    handlers: list[logging.Handler] = [
        logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    ]
    # pythonw 起動では stdout が無い。ある時だけコンソールにも出す。
    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def enable_dpi_awareness() -> None:
    """DPI 125% の環境で文字と線がぼやけるのを防ぐ。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001 - DPI 設定の失敗で起動を止める理由がない
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass


def main() -> int:
    setup_logging()
    enable_dpi_awareness()
    logging.info("===== ShotTrend start =====")

    try:
        from shottrend.ui.app import MonitorApp

        root = tk.Tk()
        MonitorApp(root)
        root.mainloop()
    except Exception:
        # pythonw 起動では stderr がどこにも出ないため、必ずログに残す。
        # ここを握らないと「起動しない」としか分からなくなる。
        logging.exception("fatal: application terminated")
        return 1
    logging.info("===== ShotTrend stop =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
