"""画面に出す文言の多言語化。

tkinter を import しない。`core` と同じく GUI 無しでテストできる。

依存の向きは `ui -> i18n -> core.config` の一方向だけ。**`core` はこの
パッケージを import しない**（`core` は言語を知らないまま保つ）。core が
返すメッセージは `core.monitor.MSG_*` のような不透明なキーで、文言に
変えるのは UI 層の仕事。

翻訳表は言語ごとの Python モジュール（`ja.py` など）に dict で持つ。JSON に
すると PyInstaller の `datas` と `sys._MEIPASS` の分岐が要るし、gettext は
`.mo` のビルド工程が要って「`py app.pyw` で動く」が壊れる。dict モジュール
なら `shottrend.spec` を一切触らずに済む。

**この下の import を動的にしてはいけない。** `importlib.import_module()` は
PyInstaller の静的解析から見えないので、ソースでは動くのに exe だけ
`ModuleNotFoundError` で落ちる。windowed の exe は理由を出さない。
"""

from __future__ import annotations

import ctypes
import locale
import logging
import os

from shottrend.core.config import LANGUAGES

from . import ja

log = logging.getLogger(__name__)

#: 判別できないときに倒す先。
DEFAULT_LANG = "ja"

#: 言語コード -> 翻訳表。`core.config.LANGUAGES` と同じ顔ぶれになる
#: （ずれていないことは tests/test_i18n.py が見張る）。
CATALOGS: dict[str, dict[str, str]] = {
    "ja": ja.TEXTS,
}

#: メニューに出す言語名。自称名（endonym）を固定で出す。全言語 × 全言語の
#: 25 通りを訳しても意味が無いし、「今の UI が読めないから変えたい」人には
#: 自称名が一番親切。
ENDONYMS = {
    "ja": "日本語",
    "en": "English",
    "zh-Hant": "繁體中文",
    "zh-Hans": "简体中文",
    "ko": "한국어",
}

_current = DEFAULT_LANG


def available() -> tuple[str, ...]:
    """翻訳表が実在する言語コード。`LANGUAGES` の並び順を保つ。"""
    return tuple(code for code in LANGUAGES if code in CATALOGS)


def current() -> str:
    return _current


def set_language(code: str) -> None:
    """表示言語を切り替える。知らないコードは既定に倒す。"""
    global _current
    _current = code if code in CATALOGS else DEFAULT_LANG


def endonym(code: str) -> str:
    return ENDONYMS.get(code, code)


def t(key: str, /, **params: object) -> str:
    """文言を引く。

    描画のたびに呼ばれるので、**何があっても例外を投げない**。1 つの訳漏れで
    常駐アプリのループが止まるほうが、変な文字列が出るよりずっと悪い。

    現在の言語に無ければ日本語、日本語にも無ければキーをそのまま返す。
    キー文字列が画面に出れば、どこが抜けているかは一目で分かる。
    """
    if not key:
        return ""
    text = CATALOGS.get(_current, {}).get(key)
    if text is None:
        text = ja.TEXTS.get(key, key)
    if not params:
        return text
    try:
        return text.format(**params)
    except (KeyError, IndexError, ValueError):
        # 訳文のプレースホルダが崩れている。整形前を返して描画は続ける
        log.warning("format failed: key=%s lang=%s", key, _current)
        return text


def metric_label(key: str) -> str:
    """項目キー（`core.metrics` の `Metric.key`）の表示名。"""
    return t(f"metric.{key}")


def composite_label(mode: str) -> str:
    """合成値モードの表示名。知らないモードは最大に倒す。

    倒し方を 1 箇所に閉じ込める（`core.metrics.metric()` が「知らないキーは
    ピークに倒す」を 1 箇所でやっているのと同じ形）。呼び出し側が
    `.get(mode, "最大")` のような既定値を持たなくて済む。
    """
    from shottrend.core.stats import COMPOSITE_MODES

    if mode not in COMPOSITE_MODES:
        mode = COMPOSITE_MODES[0]
    return t(f"composite.{mode}")


# --------------------------------------------------------------- ロケール検出

#: Windows の LANGID（下位 10 bit が主言語、上位がサブ言語）から言語コードへ。
#: 中国語だけは繁体／簡体の判別に地域まで要るので、完全な LANGID で引く。
_LANGID_FULL = {
    0x0404: "zh-Hant",  # 台湾
    0x0C04: "zh-Hant",  # 香港
    0x1404: "zh-Hant",  # マカオ
    0x0804: "zh-Hans",  # 中国
    0x1004: "zh-Hans",  # シンガポール
}
_LANGID_PRIMARY = {0x11: "ja", 0x12: "ko", 0x09: "en"}

#: ロケール文字列から言語コードへ。区切りを `_` に均してから前方一致で見る
#: ので、並び順に意味がある（繁体を簡体より先に置く）。
#:
#: Windows の Python は `"ja_JP"` ではなく `"Japanese_Japan"` を返す（実測
#: 済み）ため、英語の言語名も受ける。
_LOCALE_PREFIXES = (
    ("chinese (traditional", "zh-Hant"),
    ("chinese_taiwan", "zh-Hant"),
    ("chinese_hong", "zh-Hant"),
    ("chinese_macau", "zh-Hant"),
    ("zh_hant", "zh-Hant"),
    ("zh_tw", "zh-Hant"),
    ("zh_hk", "zh-Hant"),
    ("zh_mo", "zh-Hant"),
    ("chinese", "zh-Hans"),
    ("zh", "zh-Hans"),
    ("japanese", "ja"),
    ("ja", "ja"),
    ("korean", "ko"),
    ("ko", "ko"),
    ("english", "en"),
    ("en", "en"),
)


def _from_langid(langid: int) -> str | None:
    if langid in _LANGID_FULL:
        return _LANGID_FULL[langid]
    return _LANGID_PRIMARY.get(langid & 0x3FF)


def parse_locale(raw: str | None) -> str | None:
    """ロケール文字列を言語コードにする。読めなければ None。"""
    if not raw:
        return None
    s = raw.strip().lower().replace("-", "_")
    for prefix, code in _LOCALE_PREFIXES:
        if s.startswith(prefix):
            return code
    return None


def detect_language(raw: str | None = None) -> str:
    """OS の表示言語から言語コードを推測する。判別できなければ既定。

    `raw` を渡したときは OS を見ない（テストのため）。

    Windows では `GetUserDefaultUILanguage()` を最優先する。これは**表示
    言語**を直接返すので最も正確。`locale.getdefaultlocale()` は Python 3.15
    で削除されるので使わない。
    """
    if raw is not None:
        return parse_locale(raw) or DEFAULT_LANG

    try:
        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
        code = _from_langid(langid)
        if code:
            return code
    except Exception:
        # Windows 以外、または API が無い。次の手段へ
        pass

    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        code = parse_locale(os.environ.get(name))
        if code:
            return code

    try:
        code = parse_locale(locale.getlocale()[0])
        if code:
            return code
    except Exception:
        pass

    return DEFAULT_LANG
