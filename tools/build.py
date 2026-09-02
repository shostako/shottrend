"""配布物を作る。Windows 上で実行する（PyInstaller はクロスビルドできない）。

    py -3.12 -m pip install -e ".[dev,build]"
    py -3.12 tools/build.py

できるもの:
    dist/shottrend.exe
    dist/shottrend-<version>-win64.zip   ← exe + README + CHANGELOG + config.example.json

GitHub Actions の release.yml も同じスクリプトを呼ぶ。手元と CI で手順を分けない。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shottrend.core.version import __version__  # noqa: E402

DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "shottrend.spec"
EXE = DIST / "shottrend.exe"
BUNDLE = [ROOT / "README.md", ROOT / "CHANGELOG.md", ROOT / "LICENSE", ROOT / "config.example.json"]


def run_pyinstaller() -> None:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD),
        str(SPEC),
    ]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def make_zip() -> Path:
    out = DIST / f"shottrend-{__version__}-win64.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(EXE, EXE.name)
        for f in BUNDLE:
            zf.write(f, f.name)
    return out


def main() -> int:
    if sys.platform != "win32":
        print("Windows 上で実行すること（PyInstaller はクロスビルドできない）", file=sys.stderr)
        return 2
    if DIST.exists():
        shutil.rmtree(DIST)
    run_pyinstaller()
    if not EXE.is_file():
        print(f"exe ができていない: {EXE}", file=sys.stderr)
        return 1
    out = make_zip()
    print(f"\nversion : {__version__}")
    print(f"exe     : {EXE}  ({EXE.stat().st_size / 1_000_000:.1f} MB)")
    print(f"zip     : {out}  ({out.stat().st_size / 1_000_000:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
