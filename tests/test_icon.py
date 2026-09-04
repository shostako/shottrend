"""アイコンの生成物の整合。tools/make_icon.py の出力を手で触ると崩れる箇所を見張る。"""

from __future__ import annotations

import base64
import struct
from pathlib import Path

from shottrend.ui import icon_data

ROOT = Path(__file__).resolve().parent.parent


def _png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "PNG のシグネチャがない"
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def test_window_icons_are_square_pngs_of_the_declared_size():
    for name in ("PNG_32", "PNG_256"):
        raw = base64.b64decode(getattr(icon_data, name))
        w, h = _png_size(raw)
        assert (w, h) == (int(name.split("_")[1]),) * 2, name
    assert len(icon_data.SIZES) == 2


def test_ico_has_the_sizes_windows_uses():
    ico = (ROOT / "assets" / "shottrend.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", ico[:6])
    assert (reserved, kind) == (0, 1), "ICO のヘッダではない"
    sizes = set()
    for i in range(count):
        w, h = ico[6 + i * 16], ico[7 + i * 16]
        sizes.add(256 if w == 0 else w)
        assert (256 if h == 0 else h) == (256 if w == 0 else w)
    assert {16, 32, 48, 256} <= sizes


def test_spec_embeds_the_ico():
    spec = (ROOT / "shottrend.spec").read_text(encoding="utf-8")
    assert 'icon=str(ROOT / "assets" / "shottrend.ico")' in spec
