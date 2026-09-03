"""CHANGELOG の体裁の検証。

版を切るたびに手で足す部分があり、抜けても誰も気づかない（GitHub 上で
`[0.4.0]` が素の文字列として出るだけ）。機械で見張る。
"""

from __future__ import annotations

import re
from pathlib import Path

from shottrend.core.version import __version__

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

#: `## [0.4.0] — 2026-09-04` の版の部分。
_HEADINGS = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)
#: 末尾の `[0.4.0]: https://...` の定義。
_LINK_DEFS = re.compile(r"^\[(\d+\.\d+\.\d+)\]: \S+$", re.MULTILINE)


def test_every_version_heading_has_a_link_definition():
    headings = set(_HEADINGS.findall(CHANGELOG))
    defined = set(_LINK_DEFS.findall(CHANGELOG))
    assert headings, "版の見出しが 1 つも見つからない"
    assert not headings - defined, f"リンク定義が無い版: {sorted(headings - defined)}"
    assert not defined - headings, f"見出しの無いリンク定義: {sorted(defined - headings)}"


def test_the_current_version_has_a_section():
    """`version.py` の版に対応する節がある。

    `release.yml` はタグと `version.py` の一致を見た上で、CHANGELOG から
    その版の節を抜いて Release 本文にする。節が無いと本文が空になる。
    """
    assert __version__ in _HEADINGS.findall(CHANGELOG), f"CHANGELOG に [{__version__}] の節が無い"
