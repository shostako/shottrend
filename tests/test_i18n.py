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


def test_readme_metric_table_matches_the_japanese_catalog():
    """README の「表示できる項目」表が日本語カタログとずれない。

    項目名は本体アプリの表記に合わせて変わることがあり、実際に
    「立上り時間」→「上昇時間」で README だけ取り残された。表示名と CSV の
    列名が同じ行に並んでいることまで見る。
    """
    readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
    table = readme.split("### 表示できる項目", 1)[1].split("\n## ", 1)[0]
    missing = [
        key
        for key in METRIC_KEYS
        if f"| {i18n.ja.TEXTS[f'metric.{key}']} | `CHnn_{key}` |" not in table
    ]
    assert not missing, f"README の項目表に無い、または名前がずれている: {missing}"


def test_metric_label_covers_every_metric():
    for key in METRIC_KEYS:
        assert i18n.metric_label(key) != f"metric.{key}"


def test_hint_is_assembled_from_menu_labels():
    """案内文がメニューの訳語から組み上がる（固定文にしていない）。

    ここが崩れると「メニューだけ訳を直して案内文が古いまま」になる。
    """
    hint = i18n.t(
        "msg.hint_choose_dir",
        menu=i18n.Ref("menu.file"),
        item=i18n.Ref("menu.choose_dir"),
    )
    assert hint == "ファイル > MMS_DATA フォルダを選ぶ"


def test_reference_parameters_are_resolved_at_format_time():
    """`Ref` のパラメータは、渡した時点ではなく整形の時点の言語で引かれる。

    状態帯の案内文はパラメータごと `_last_msg_params` に残り、言語を
    切り替えたあとの描き直しでも同じものが使われる。訳文を先に焼き込むと
    英語の画面に日本語の案内が次のポーリング（最大 60 秒）まで居座る。
    """
    params = {"menu": i18n.Ref("menu.file"), "item": i18n.Ref("menu.choose_dir")}
    assert i18n.t("msg.hint_choose_dir", **params) == "ファイル > MMS_DATA フォルダを選ぶ"

    i18n.set_language("en")
    # 同じ params をそのまま使い回す（アプリと同じ持ち方）
    assert i18n.t("msg.hint_choose_dir", **params) == "File > Choose MMS_DATA folder"


def test_status_hint_parameters_are_not_translated_in_advance():
    """アプリ側が `Ref` を渡している（`t()` の戻り値を渡していない）。

    `_tick_once()` で訳してしまうと上のテストが守っている性質が意味を失う。
    ここは呼び出し側の書き方の問題なので、ソースで縛る。
    """
    from shottrend.ui import app as app_module

    tick = _function(app_module, "_tick_once")
    refs = {
        node.args[0].value
        for node in ast.walk(tick)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Ref"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert refs == {"menu.file", "menu.choose_dir"}


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


def test_app_resolves_the_font_before_styling():
    """起動経路が `set_language_font()` を呼ぶ。

    これを呼び忘れると `resolve_ui_font()` とフォールバック候補が丸ごと死に、
    `Yu Gothic UI` の無い環境で代替が選ばれない。しかもウィジェットの幅を
    「実際には使われないフォント」で測ることになる。テストは通るのに機能だけ
    死ぬので、呼び出しの実在をここで縛る。

    呼ぶ順序（スタイルを組む前）は目で見るしかないが、まず呼ばれていることを
    保証する。
    """
    from shottrend.ui import app as app_module

    tree = ast.parse(Path(app_module.__file__).read_text(encoding="utf-8"))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "set_language_font" in called
    assert "apply_ttk_theme" in called


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


# ------------------------------------------------------------ 言語切替の配線


def _function(module, name: str) -> ast.FunctionDef:
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{module.__name__} に {name}() が無い")


def _self_attr(node) -> str | None:
    """`self.X` なら X、そうでなければ None。"""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if node.value.id == "self":
            return node.attr
    return None


def test_root_level_widgets_are_all_destroyed_on_rebuild():
    """`root` に直接置いたウィジェットは、作り直しの前に全部捨てられる。

    言語切替は画面を丸ごと組み直す方式なので、捨て漏れがあると同じ場所に
    ウィジェットが二重に積まれる。`_build_layout()` にパネルを 1 枚足した
    ときの「destroy リストに足し忘れ」がこの手の事故の典型で、日本語のまま
    使っている限り誰も気づかない。
    """
    from shottrend.ui import app as app_module

    build = _function(app_module, "_build_layout")
    rebuild = _function(app_module, "_rebuild_ui")

    created = set()
    for node in ast.walk(build):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        name = _self_attr(node.targets[0])
        args = node.value.args
        # 第 1 引数が self.root のものだけ = root 直下に置かれるウィジェット
        if name and args and _self_attr(args[0]) == "root":
            created.add(name)
    assert created, "_build_layout() から root 直下のウィジェットが読み取れない"

    destroyed = set()
    for node in ast.walk(rebuild):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "destroy":
                name = _self_attr(node.func.value)
                if name:
                    destroyed.add(name)
        elif isinstance(node, ast.Tuple | ast.List):
            destroyed |= {n for n in (_self_attr(e) for e in node.elts) if n}

    missing = created - destroyed
    assert not missing, f"_rebuild_ui() が捨て損ねている: {sorted(missing)}"


def test_language_menu_is_wired_to_the_rebuild():
    """メニューから `_on_language` が呼べて、そこから画面が組み直される。"""
    from shottrend.ui import app as app_module

    build_menu = _function(app_module, "_build_menu")
    labels = {
        node.func.attr
        for node in ast.walk(build_menu)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "add_radiobutton" in labels

    on_language = _function(app_module, "_on_language")
    called = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(on_language)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute | ast.Name)
    }
    # 文言・フォント・ttk スタイル・画面、この 4 つが揃わないと切り替わらない
    assert {"set_language", "set_language_font", "apply_ttk_theme", "_rebuild_ui"} <= called


def test_language_variable_is_held_on_the_instance():
    """`tk.StringVar` を self に持つ。ローカルだと GC で選択マークが消える。"""
    from shottrend.ui import app as app_module

    build_menu = _function(app_module, "_build_menu")
    held = {
        _self_attr(node.targets[0])
        for node in ast.walk(build_menu)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "attr", "") == "StringVar"
    }
    assert held - {None}, "StringVar がインスタンスに保持されていない"


def test_chart_cancels_its_pending_redraw_when_destroyed():
    """`ShotChart.destroy()` が `after()` の予約を取り消す。

    画面を作り直す方式にしたので、リサイズ debounce の予約が生き残ると
    死んだウィジェットに `redraw()` が飛ぶ。
    """
    from shottrend.ui import chart as chart_module

    destroy = _function(chart_module, "destroy")
    called = {
        node.func.attr
        for node in ast.walk(destroy)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "after_cancel" in called
