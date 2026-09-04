"""アプリのアイコンを描いて書き出す。Pillow が要る（`pip install -e ".[icon]"`）。

    py -3.12 tools/make_icon.py

できるもの:
    assets/shottrend.ico           ← PyInstaller が exe に埋める（shottrend.spec の icon=）
    assets/shottrend_icon.png      ← 1024px の元絵。README やストア向け
    shottrend/ui/icon_data.py      ← ウィンドウ用。PNG を base64 で埋めた Python モジュール

ウィンドウのアイコンをファイルにしないのは、PyInstaller の datas と `sys._MEIPASS`
分岐を持ち込まないため（翻訳表を dict モジュールにしたのと同じ理由）。Tk の
`PhotoImage(data=...)` は base64 の PNG をそのまま受ける。

絵柄: 紺地に横罫線、オレンジとシアンの 2ch 折れ線（点を明示）、左上に ShotTrend。
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - 実行環境の話
    print('Pillow が要る: pip install -e ".[icon]"', file=sys.stderr)
    raise SystemExit(2) from None

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICO = ASSETS / "shottrend.ico"
PNG = ASSETS / "shottrend_icon.png"
MODULE = ROOT / "shottrend" / "ui" / "icon_data.py"

S = 1024
INK = (28, 30, 38)
GRID = (60, 66, 84)
ORANGE = (255, 138, 40)
CYAN = (80, 210, 230)
#: ico に入れるサイズ。Windows は 16/32/48 をよく使い、256 は大きい表示用
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
#: ウィンドウ用。タイトルバーは 16〜32、Alt+Tab やタスクバーは 32〜48 を使う
WINDOW_SIZES = (32, 256)


#: 文字のフォント。環境で変わると生成物の diff が出るので 1 つに決める。
#: WSL（Ubuntu の fonts-dejavu-core）で作るのが正。Windows で回すなら
#: 同じ ttf を置くか FONT を差し替えて、生成物の diff を見て判断する
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def _font(size: int) -> ImageFont.FreeTypeFont:
    if not FONT.is_file():
        # load_default() に落とすとビットマップの小さな字で静かに壊れた絵ができる
        raise RuntimeError(f"フォントが無い: {FONT}（WSL で apt install fonts-dejavu-core）")
    return ImageFont.truetype(str(FONT), size)


def draw() -> Image.Image:
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=S // 5, fill=255)
    im.paste(Image.new("RGBA", (S, S), INK + (255,)), (0, 0), mask)
    d = ImageDraw.Draw(im)

    for y in range(250, 960, 150):
        d.line((100, y, 924, y), fill=GRID, width=10)

    def polyline(points, color):
        d.line(points, fill=color, width=38, joint="curve")
        for x, y in points:
            d.ellipse((x - 60, y - 60, x + 60, y + 60), fill=color)
            d.ellipse((x - 40, y - 40, x + 40, y + 40), fill=INK)

    polyline([(170, 840), (330, 740), (490, 780), (650, 620), (820, 540)], CYAN)
    polyline([(170, 600), (330, 470), (490, 540), (650, 360), (820, 270)], ORANGE)

    f = _font(118)
    d.text((110, 120), "Shot", font=f, fill=ORANGE, anchor="la")
    d.text((110 + d.textlength("Shot", font=f), 120), "Trend", font=f, fill=CYAN, anchor="la")
    return im


def write_ico(im: Image.Image) -> None:
    frames = [im.resize((s, s), Image.LANCZOS) for s in ICO_SIZES]
    frames[-1].save(ICO, format="ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=frames[:-1])


def write_module(im: Image.Image) -> None:
    import io

    chunks = []
    for s in WINDOW_SIZES:
        buf = io.BytesIO()
        im.resize((s, s), Image.LANCZOS).save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        lines = "\n".join(f'    "{b64[i : i + 88]}"' for i in range(0, len(b64), 88))
        chunks.append(f"PNG_{s} = (\n{lines}\n)\n")
    body = (
        '"""ウィンドウのアイコン。tools/make_icon.py が生成する。手で編集しない。\n\n'
        "base64 の PNG。`tk.PhotoImage(data=...)` にそのまま渡せる。ファイルにしないのは\n"
        "PyInstaller の datas と `sys._MEIPASS` 分岐を持ち込まないため。\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        + "\n".join(chunks)
        + "\nSIZES = ("
        + ", ".join(f"PNG_{s}" for s in WINDOW_SIZES)
        + ")\n"
    )
    MODULE.write_text(body, encoding="utf-8")


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    im = draw()
    im.save(PNG)
    write_ico(im)
    write_module(im)
    print(f"ico    : {ICO}  ({ICO.stat().st_size:,} bytes)")
    print(f"png    : {PNG}")
    print(f"module : {MODULE}  ({MODULE.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
