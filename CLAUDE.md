# shot-monitor プロジェクト設定

MPS08B（Futaba 金型内圧計測システム）のサマリ CSV を追従して、ショットごとの演算値（ピーク圧力など）を数値で見せる常駐 Tkinter アプリ。背景と全体像は `README.md` を読むこと。

## 開発と実行

- **依存は標準ライブラリのみ**。この方針を崩さない。現場PCに置いて `py app.pyw` で動くことが最大の価値
- 開発は WSL、実行は **Windows 側の Python 3.12**（`C:/Users/<user>/AppData/Local/Programs/Python/Python312/python.exe`）
  - PATH 先頭の `python` は Hermes の venv なので使わない。scoop に python は入っていない
  - WSL 上のコードを Windows から動かすなら `\\wsl.localhost\<WSL_DISTRO_NAME>\home\<user>\ClaudeCode\shot-monitor\app.pyw`。ディストロ名はハードコードせず `$WSL_DISTRO_NAME` を使う
- テストと lint は WSL 側の `.venv` で回す

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check . && .venv/bin/ruff format .
```

## 設計上の約束

**`core/` に tkinter を import しない。** これが崩れるとテストが GUI 環境を要求するようになる。UI 層は `MonitorService.poll()` を呼んで結果を描くだけで、判断ロジックを持たない。

**絶対パスを埋め込まない。** MMS_DATA の場所は `config.json` にあり GUI から変更できる。開発中に実際にユーザーがアプリ一式を Desktop から Documents へ移動した。

**フォルダ名で並べ替えない。** 最新セッションの判定は CSV の mtime のみ。`separate_20260219` / `_20260828` / `DefaultFile001_20260216` が実在し、同日 2 フォルダ併存もある。

**チャンネル数を決め打ちにしない。** MPS08B はアンプ 4 台で 32ch まで計測できる。
CSV はヘッダにある `CHnn_<項目>` を項目ごとに全部読み、`Shot.values` に
項目キー → 可変長の並びで持つ。画面に出すのは `ShotHistory.used_channels()` が
返す「一度でもピークが非ゼロだった ch」だけ。未接続の ch も本体は 0.00 で
書き続けるので、列の有無では判別できない。ch が 4 本以上になったらカードは
自動で小型版に切り替わる。

**表示項目は全 ch 共通で 1 つ。** 項目の一覧と表示名・単位・桁数は `core/metrics.py`
が単一ソース。ch ごとに項目を変えられる作りにしない（縦軸が 1 本のグラフに載らず、
合成値も意味を失う）。センサ接続の判定は表示項目に関係なくピークで行う。

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
from core.csvsource import SummaryCsvReader
f = Path('/mnt/c/Users/<user>/Documents/MPS08B_Application_1_3_0_5/MMS_DATA/20260821_setting001_20260831/20260821_setting001_20260831.csv')
r = SummaryCsvReader(f).read_new()
print(len(r.shots), r.skipped)  # 241 0 になるはず
"
```

GUI の見た目は必ずスクリーンショットで確認する。レイアウトの崩れはテストで検出できない。
