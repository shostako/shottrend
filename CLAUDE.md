# shot-monitor プロジェクト設定

MPS08B（Futaba 金型内圧計測システム）のサマリ CSV を追従して、ショットごとのピーク圧力を数値で見せる常駐 Tkinter アプリ。背景と全体像は `README.md` を読むこと。

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

**`after()` の予約は必ず `after_cancel` してから入れ直す**（`_schedule()` / `_cancel_scheduled()`）。多重ループはこの手のアプリの定番事故。`_tick()` は `finally` で必ず再予約し、例外でループを止めない。

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
