# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller の定義。`tools/build.py` から呼ぶ（直接 `pyinstaller shottrend.spec` でも可）。

1 ファイルの exe にする。現場 PC に置くのは exe 1 本で、config.json と logs/ は
exe の隣に作られる（shottrend/core/config.py の app_dir() の frozen 判定）。

console=False: pythonw 相当。stderr はどこにも出ないので、起動しないときは
logs/app.log を見る（app.pyw が例外を捕まえてログに残す）。
"""

from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "app.pyw")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    # 除外は「絶対に使わない」と言い切れるものだけ。標準ライブラリを推測で切ると
    # 別の標準モジュールが巻き添えで死ぬ（pathlib → urllib.parse を切って起動不能に
    # なった）。数 MB の節約に見合わない
    excludes=[
        "pytest",
        "ruff",
        "unittest",
        "doctest",
        "pydoc",
        "lib2to3",
        "curses",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="shottrend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    # exe のアイコン。tools/make_icon.py が assets/ に生成する
    icon=str(ROOT / "assets" / "shottrend.ico"),
    disable_windowed_traceback=False,
    target_arch=None,
)
