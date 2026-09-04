# ShotTrend プロジェクト設定

1 ショット 1 行の CSV を追従してショットごとの値の推移を数値で見せる常駐 Tkinter アプリ。現状の対応データ源は MPS08B（Futaba 金型内圧計測システム）のサマリ CSV。背景と全体像は `README.md` を読むこと。

## 名前

- 表示名は **ShotTrend**、機械が読む名前（リポ・パッケージ・exe・pyproject）は **`shottrend`** 小文字一語。`shot-trend` / `shot_trend` は使わない
- 旧名 `shot-monitor`（v0.2.0 まで）。GitHub の旧 URL はリダイレクトされる

## 開発と実行

- **依存は標準ライブラリのみ**。この方針を崩さない。現場PCに置いて `py app.pyw` で動くことが最大の価値
- 開発は WSL、実行は **Windows 側の Python 3.12**（`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`）
  - PATH 先頭の `python` は Hermes の venv なので使わない。scoop に python は入っていない
  - WSL 上のコードを Windows から動かすなら `\\wsl.localhost\<WSL_DISTRO_NAME>\home\<user>\ClaudeCode\shottrend\app.pyw`。ディストロ名はハードコードせず `$WSL_DISTRO_NAME` を使う
- テストと lint は WSL 側の `.venv` で回す。**`.venv` は Python 3.12**（`uv venv --python 3.12 .venv`）。Ubuntu 22.04 の `python3` は 3.10 で `requires-python >=3.12` に弾かれる

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check . && .venv/bin/ruff format .
```

## 配布物

- `tools/build.py` が PyInstaller で `dist/shottrend.exe`（onefile, windowed）と zip を作る。**Windows 上でしか動かない**
- 手元で組むときは WSL のツリーを Windows 側へコピーしてから（`robocopy` で `.git` `.venv` `logs` `build` `dist` `config.json` を除外）。UNC パス上で PyInstaller を回さない。ビルド用 venv は `%LOCALAPPDATA%\shottrend-build\venv`
- リリースは `v<version>` タグの push だけ。`release.yml` が Windows で lint・テスト・ビルドを通し、CHANGELOG の該当節を本文に Release を作る。タグと `shottrend/core/version.py` が食い違うと止まる
- バージョンは `shottrend/core/version.py` が単一ソース。上げるときは CHANGELOG に節を切る
- アイコンは `tools/make_icon.py` が描く（Pillow、`pip install -e ".[icon]"`）。出力は `assets/shottrend.ico`（spec の `icon=` で exe に埋める）と `shottrend/ui/icon_data.py`（ウィンドウ用、base64 PNG を `PhotoImage(data=)` に渡す）。**`icon_data.py` を手で編集しない**。ウィンドウ用をファイルにしないのは datas と `sys._MEIPASS` 分岐を持ち込まないため
- exe の動作確認は、**空のフォルダに exe と config.json だけ置いて起動**する（開発ツリーで起動すると隣の `config.json` や `logs/` を拾って frozen 判定の穴が見えない）。`logs/app.log` が exe の隣にできれば frozen 判定は効いている

### PyInstaller で踏んだ罠

- **`excludes` に標準ライブラリを推測で入れない。** `urllib` を除外したら `pathlib`（3.12 は `urllib.parse` を import する）が巻き添えで死に、起動時に `ModuleNotFoundError` で落ちた。windowed の exe は「Unhandled exception in script」としか出さないので原因が見えない。console=True の一時 spec を組んでトレースバックを取る
- PowerShell 5.1 の `Get-Content`/`Set-Content` は既定が cp932。spec や `.py` を通すと UTF-8 のコメントが壊れて `SyntaxError: (unicode error)` になる。必ず `-Encoding UTF8`
- 同じ理由で PowerShell 5.1 の `Set-Content -Encoding UTF8` は **BOM を付ける**。`config.json` は `utf-8-sig` で読む（メモ帳で編集しても同じ BOM が付く）

## 設計上の約束

**`shottrend/core/` に tkinter を import しない。** これが崩れるとテストが GUI 環境を要求するようになる。UI 層は `MonitorService.poll()` を呼んで結果を描くだけで、判断ロジックを持たない。

**`shottrend/core/` に `i18n` を import しない。** core は言語を知らないまま保つ。画面に出す言葉は `shottrend/i18n/` にあり、core が UI に渡すのは `MSG_NO_ROOT` のような**翻訳キー**（`STATUS_RUNNING` と同種の不透明な識別子）とパラメータだけ。core が翻訳関数を呼び始めると、`MonitorService` のテストが「その時点の表示言語」に依存して実行順序で壊れる。`tests/test_i18n.py` が import を走査して見張っている。

**画面に出す文字列をコードに直接書かない。** すべて `i18n.t()` 経由。翻訳表は言語ごとの Python モジュール（`i18n/ja.py` など）で、**`i18n/__init__.py` から静的に import する**。`importlib.import_module()` のような動的 import は PyInstaller の静的解析から見えず、ソースでは動くのに exe だけ `ModuleNotFoundError` で落ちる（windowed なので理由が出ない）。プレースホルダは必ず名前付き（`{count}`）にする。位置指定だと訳文で語順を変えられない。

**訳語は MPS08B 本体アプリの表記に合わせる。** 同じ値を本体と違う言葉で呼ぶと現場で混乱する。根拠にした対訳は `docs/official_terms.csv`（`tools/extract_official_terms.py` が本体の exe から抜く）。公式訳には機械翻訳由来の壊れたものが混じっているが、**直すのは意味が違うものだけ**。語感が古い・不自然という程度なら本体に合わせたままにし、直した行にはカタログへ「公式は○○だが誤訳なので変えた」とコメントを残す。本体アプリの文字列は他社の著作物なので、CSV には ShotTrend が実際に引いているキーだけを載せる（`CITED_KEYS`）。

**訳さないもの**: 単位（MPa, MPa·s, s）、`CH01` などの ch 名、テーブル列見出しの `Shot` / `Time` / `interval`（MPS08B の CSV の列名そのもの＝データ源の識別子）、カード内の `max/min/avg/σ`。

**言語の切替は画面を丸ごと組み直す**（`MonitorApp._rebuild_ui()`）。ウィジェットごとに `retranslate()` を配る方式は採らない。`control_bar._group()` や `header_panel` の見出しは参照を保持しない匿名ラベルで、その方式だと「ラベルを足したとき retranslate に足し忘れる」バグが構造的に残るため。**`root` の直下にウィジェットを足したら `_rebuild_ui()` の destroy 対象にも足すこと**（`tests/test_i18n.py` が対応を見張る）。`ttk.Style` はフォントのタプルを生成時に取り込むので、切替のたびに `apply_ttk_theme()` を通し直す。

**ウィンドウの最小幅は決め打ちにしない。** 英語のラベルは日本語より 1 割以上横に長い。コントロールバーは「ラベル＋操作部」の単位で折り返す（`ui/flow.py` の `pack_rows`、tkinter 非依存でテスト可）ので、`_apply_min_size()` は最も広い単位が収まる幅を下限にする。バーを 1 行に固定していた頃は最小幅が 1092px（英語 1233px）あり、Win+← のハーフスナップ（1920px 画面で 960px）がそこで止まった。ハーフスナップの幅より小さい最小幅を保つこと。

**絶対パスを埋め込まない。** MMS_DATA の場所は `config.json` にあり GUI から変更できる。開発中に実際にユーザーがアプリ一式を Desktop から Documents へ移動した。

**フォルダ名で並べ替えない。** 最新セッションの判定は CSV の mtime のみ。`separate_20260219` / `_20260828` / `DefaultFile001_20260216` が実在し、同日 2 フォルダ併存もある。

**チャンネル数を決め打ちにしない。** MPS08B はアンプ 4 台で 32ch まで計測できる。
CSV はヘッダにある `CHnn_<項目>` を項目ごとに全部読み、`Shot.values` に
項目キー → 可変長の並びで持つ。画面に出すのは `ShotHistory.used_channels()` が
返す「一度でもピークが非ゼロだった ch」だけ。未接続の ch も本体は 0.00 で
書き続けるので、列の有無では判別できない。ch が 4 本以上になったらカードは
自動で小型版に切り替わる。

**表示項目は全 ch 共通で 1 つ。** 項目の一覧と単位・桁数は `shottrend/core/metrics.py`
が単一ソース（表示名は言語で変わるので `i18n` が持つ）。ch ごとに項目を変えられる
作りにしない（縦軸が 1 本のグラフに載らず、合成値も意味を失う）。センサ接続の判定は
表示項目に関係なくピークで行う。

**`after()` の予約は必ず `after_cancel` してから入れ直す**（`_schedule()` / `_cancel_scheduled()`）。多重ループはこの手のアプリの定番事故。`_tick()` は `finally` で必ず再予約し、例外でループを止めない。

## tkinter で踏んだ罠

**`tk.Canvas` のサブクラスで `self._options` という属性名を使ってはいけない。**
`tkinter.Misc` が内部で `self._options(cnf)` を呼ぶため、`TypeError: 'list'
object is not callable` で初期化ごと死ぬ。属性の代入は必ず `super().__init__()`
より後に行うこと。

**`pythonw` 起動では stderr がどこにも出ない。** `app.pyw` の `main()` で例外を
捕まえてログに残しているので、起動しないときは `logs/app.log` を見る。この捕捉が
無いと「起動しない」以上の情報が得られない。

**`ttk.Frame` に `height=` を指定しても効かない。** 行数を決めたいときは
`ttk.Treeview` 側に `height=<行数>` を渡す。

**セグメント状のボタンを Canvas に描くときは、塗りを全部置いてから線を引く。**
1 つずつ「枠付きで」描くと、端の角丸を四角く戻す塗りが隣との境界線を消す。

## データ仕様で踏んだ罠

実データで確認済み。ここを忘れると必ず壊れる。

1. **ヘッダ行がファイル途中に何度も現れる**（計測の中断→再開ごと。実測 247 行中 6 回、全 36 ファイル中 17 ファイルで 2 回以上）。素朴に `csv.DictReader` へ渡すと `could not convert string to float: 'CH01_peak'` で落ちる
2. **ショット番号は飛ぶが巻き戻らず重複しない**。だから shot_no をキーにすれば冪等。だが実数軸にすると欠番で巨大な空白ができるので、グラフは等間隔カテゴリ軸
3. **`interval` は 0.0〜1,288,852 秒とばらつく**。「約22秒」を前提にした判定は破綻する
4. CRLF・末尾カンマ・0 行 CSV・書き込み途中の不完全行がすべて実在する

新しい挙動を見つけたらここに追記し、`tests/` に再現ケースを足すこと。

## テスト

`tests/conftest.py` が 104 列・CRLF・末尾カンマの合成 CSV を組み立てる。実データを test fixture に置かない（リポに成形条件の実データを入れない）。

実データでの検証は手元で行う:

```bash
.venv/bin/python -c "
from pathlib import Path
from shottrend.core.csvsource import SummaryCsvReader
f = Path('/mnt/c/Users/<user>/Documents/MPS08B_Application_1_3_0_5/MMS_DATA/<設定名>_<日付>/<設定名>_<日付>.csv')
r = SummaryCsvReader(f).read_new()
print(len(r.shots), r.skipped)  # skipped は 0 になるはず
"
```

GUI の見た目は必ずスクリーンショットで確認する。レイアウトの崩れはテストで検出できない。
