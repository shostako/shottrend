"""翻訳表とコードの整合を見張る。

ここが守っているのは「訳を足し忘れた」「片方の言語だけプレースホルダを
落とした」を**マージ前に**捕まえること。GUI を起動しないと分からない類の
不具合を、できる限りテストの側に引き寄せている。
"""

from __future__ import annotations

import ast
import string
from pathlib import Path

import pytest

from shottrend import i18n
from shottrend.core import monitor
from shottrend.core.config import CHART_KINDS, LANGUAGES
from shottrend.core.metrics import METRIC_KEYS
from shottrend.core.stats import COMPOSITE_MODES

CODES = sorted(i18n.CATALOGS)


def placeholders(text: str) -> set[str]:
    """`str.format` のフィールド名の集合。"""
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


# ---------------------------------------------------------------- カタログ整合


@pytest.mark.parametrize("code", CODES)
def test_catalog_has_same_keys_as_japanese(code):
    """全言語が同じキー集合を持つ。差があればキー名を出して落ちる。"""
    diff = set(i18n.CATALOGS[code]) ^ set(i18n.ja.TEXTS)
    assert not diff, f"{code}: キーが日本語版とずれている: {sorted(diff)}"


@pytest.mark.parametrize("code", CODES)
def test_catalog_has_no_empty_value(code):
    empty = [k for k, v in i18n.CATALOGS[code].items() if not v.strip()]
    assert not empty, f"{code}: 空の訳文: {empty}"


@pytest.mark.parametrize("code", CODES)
def test_placeholders_match_japanese(code):
    """プレースホルダの集合が全言語で一致する。

    これを見張らないと、`{count}` を落とした訳文がそのまま出荷され、本番の
    その言語でだけ数字の入らない文字列が出る（t() は例外を投げないので
    気づけない）。
    """
    for key, ja_text in i18n.ja.TEXTS.items():
        text = i18n.CATALOGS[code].get(key)
        if text is None:
            continue  # キー欠落は別のテストが報告する
        assert placeholders(text) == placeholders(ja_text), f"{code}: {key}"


def test_registry_matches_supported_languages():
    """翻訳表のコードが `LANGUAGES` の部分集合になっている。"""
    assert set(i18n.CATALOGS) <= set(LANGUAGES)
    assert set(i18n.ENDONYMS) == set(LANGUAGES)
    assert i18n.available() == tuple(c for c in LANGUAGES if c in i18n.CATALOGS)


# ------------------------------------------------------- コードとの drift 検出


@pytest.mark.parametrize(
    ("prefix", "values"),
    [
        ("metric", METRIC_KEYS),
        ("composite", COMPOSITE_MODES),
        ("chart_kind", CHART_KINDS),
        (
            "status",
            (
                monitor.STATUS_RUNNING,
                monitor.STATUS_IDLE,
                monitor.STATUS_NODATA,
                monitor.STATUS_NOROOT,
                monitor.STATUS_ERROR,
            ),
        ),
    ],
)
def test_enumerated_values_have_translations(prefix, values):
    """コード側の選択肢が増えたら、訳の無いキーとして即座に落ちる。"""
    missing = [f"{prefix}.{v}" for v in values if f"{prefix}.{v}" not in i18n.ja.TEXTS]
    assert not missing, f"訳が無い: {missing}"


def test_monitor_messages_have_translations():
    """core が返しうるメッセージには必ず訳がある。"""
    keys = [v for n, v in vars(monitor).items() if n.startswith("MSG_")]
    assert keys, "MSG_* が 1 つも無い。定数の命名が変わった？"
    assert [k for k in keys if k not in i18n.ja.TEXTS] == []


def test_core_does_not_import_i18n():
    """`core` は言語を知らないまま保つ。

    core が翻訳関数を呼び始めると、`MonitorService` のテストが「その時点の
    表示言語」に依存し、テストの順序で結果が変わりうる。
    """
    core_dir = Path(monitor.__file__).parent
    offenders = []
    for path in sorted(core_dir.glob("*.py")):
        # docstring で i18n に言及するのは構わない。import だけを見る
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any("i18n" in n.split(".") for n in names):
                offenders.append(path.name)
                break
    assert offenders == [], f"core が i18n を import している: {offenders}"


# ------------------------------------------------------------------ t() の契約


def test_unknown_key_returns_the_key_itself():
    assert i18n.t("no.such.key") == "no.such.key"


def test_empty_key_returns_empty():
    assert i18n.t("") == ""


def test_missing_parameter_does_not_raise():
    """訳文が要求するパラメータが来なくても描画を止めない。"""
    assert i18n.t("msg.read_retry") == i18n.ja.TEXTS["msg.read_retry"]


def test_unused_parameter_is_ignored():
    assert i18n.t("status.running", count=3) == i18n.ja.TEXTS["status.running"]


def test_parameters_are_formatted():
    assert i18n.t("msg.skipped", rows=7) == "7行スキップ"


@pytest.mark.parametrize(
    "template",
    [
        "{x.y} 個",  # 属性アクセス -> AttributeError
        "{x[0]} 個",  # 添字アクセス -> TypeError
        "{x:>{width}} 個",  # 入れ子の書式指定 -> KeyError
        "{ 個",  # 閉じていない -> ValueError
    ],
)
def test_broken_placeholder_does_not_raise(monkeypatch, template):
    """訳文の書き方が壊れていても常駐ループを止めない。

    訳文は外から流し込むデータで、書き方を完全には統制できない。
    str.format が投げる例外の種類も書き方次第で変わる。
    """
    monkeypatch.setitem(i18n.CATALOGS, "xx", {"broken": template})
    i18n.set_language("xx")
    assert i18n.t("broken", x=1) == template


def test_falls_back_to_japanese(monkeypatch):
    """訳が抜けている言語では日本語が出る（キー文字列を見せるより親切）。"""
    monkeypatch.setitem(i18n.CATALOGS, "xx", {"app.title": "X"})
    i18n.set_language("xx")
    assert i18n.t("app.title") == "X"
    assert i18n.t("status.running") == i18n.ja.TEXTS["status.running"]


def test_unknown_language_falls_back_to_default():
    i18n.set_language("fr")
    assert i18n.current() == i18n.DEFAULT_LANG


def test_composite_label_falls_back_to_first_mode():
    """不正なモードの倒し先を 1 箇所に閉じ込めてある。"""
    assert i18n.composite_label("nope") == i18n.composite_label(COMPOSITE_MODES[0])


def test_metric_label_covers_every_metric():
    for key in METRIC_KEYS:
        assert i18n.metric_label(key) != f"metric.{key}"


def test_hint_is_assembled_from_menu_labels():
    """案内文がメニューの訳語から組み上がる（固定文にしていない）。

    ここが崩れると「メニューだけ訳を直して案内文が古いまま」になる。
    """
    hint = i18n.t(
        "msg.hint_choose_dir",
        menu=i18n.t("menu.file"),
        item=i18n.t("menu.choose_dir"),
    )
    assert hint == "ファイル > MMS_DATA フォルダを選ぶ"


def test_about_lines_keep_their_values():
    assert i18n.t("about.config", path="C:/x/config.json") == "設定: C:/x/config.json"
    assert i18n.t("about.data", path=i18n.t("about.unset")) == "データ: (未設定)"


# ------------------------------------------------------------------ フォント


@pytest.mark.parametrize(
    ("lang", "families", "expected"),
    [
        ("ko", {"Malgun Gothic", "Segoe UI"}, "Malgun Gothic"),
        ("ko", {"Gulim"}, "Gulim"),  # 第 1 候補が無ければ次へ
        ("zh-Hant", {"PMingLiU", "Yu Gothic UI"}, "PMingLiU"),
        ("zh-Hans", {"Microsoft YaHei UI"}, "Microsoft YaHei UI"),
        ("en", {"Segoe UI"}, "Segoe UI"),
        # その言語の候補が全滅したら日本語用へ。豆腐を並べるよりまし
        ("ko", {"Yu Gothic UI"}, "Yu Gothic UI"),
    ],
)
def test_resolve_ui_font(lang, families, expected):
    from shottrend.ui import theme

    assert theme.resolve_ui_font(lang, families) == expected


def test_resolve_ui_font_never_raises_on_empty_family_list():
    """フォントが 1 つも見つからなくても名前を返す（Tk が既定に倒す）。"""
    from shottrend.ui import theme

    assert theme.resolve_ui_font("ko", set())
    assert theme.resolve_ui_font("xx", set())


def test_set_language_font_leaves_monospace_alone():
    """数値用の等幅は言語で変えない。桁が揃うことだけが要件。"""
    from shottrend.ui import theme

    before = (theme.F_HUGE, theme.F_STAT, theme.F_TABLE)
    try:
        theme.set_language_font("ko", {"Malgun Gothic"})
        assert theme.F_LABEL[0] == "Malgun Gothic"
        assert (theme.F_HUGE, theme.F_STAT, theme.F_TABLE) == before
    finally:
        theme.set_language_font("ja", {"Yu Gothic UI"})


def test_every_language_has_font_candidates():
    """言語を足したらフォント候補も足す。片方だけ増えると豆腐になる。"""
    from shottrend.ui import theme

    assert set(theme.UI_FONT_CANDIDATES) == set(LANGUAGES)


# ------------------------------------------------------------- ロケール検出


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Windows の Python が返す形（実測: locale.getlocale() -> Japanese_Japan）
        ("Japanese_Japan", "ja"),
        ("Korean_Korea", "ko"),
        ("Chinese (Traditional)_Taiwan", "zh-Hant"),
        ("Chinese_China", "zh-Hans"),
        ("English_United States", "en"),
        # POSIX 形式
        ("ja_JP", "ja"),
        ("ko_KR.UTF-8", "ko"),
        ("zh_TW", "zh-Hant"),
        ("zh_HK", "zh-Hant"),
        ("zh_CN.UTF-8", "zh-Hans"),
        ("en_GB", "en"),
        # BCP-47 形式
        ("zh-Hant", "zh-Hant"),
        ("zh-Hans", "zh-Hans"),
    ],
)
def test_parse_locale(raw, expected):
    assert i18n.parse_locale(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "fr_FR", "xx"])
def test_parse_locale_gives_up_quietly(raw):
    assert i18n.parse_locale(raw) is None


def test_detect_language_falls_back_when_unreadable():
    assert i18n.detect_language("fr_FR") == i18n.DEFAULT_LANG
