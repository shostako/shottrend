"""日本語の文言。

キーは「どのウィジェットにあるか」ではなく「何の言葉か」でまとめてある。
文字列がウィジェット間を引っ越してもキー名が変わらないようにするため。

**訳さないと決めたもの**（この表に入れない）: 単位（MPa, MPa·s, s）、`CH01`
などの ch 名、テーブル列見出しの `Shot` / `Time` / `interval`（MPS08B の CSV の
列名そのもの＝データ源の識別子）、グラフ x 軸の `shot`、カード内の
`max/min/avg/σ`、`▲▼`、`--.--`、`{n} ch`、製品名、ログメッセージ。

プレースホルダは必ず名前付きにすること。位置指定（`{}` や `{0}`）だと、訳文で
語順を変えられない言語が出る。
"""

from __future__ import annotations

TEXTS: dict[str, str] = {
    # ------------------------------------------------------------ アプリ全体
    "app.title": "ShotTrend — MPS08B 演算値トレンド",
    # -------------------------------------------------------------- メニュー
    "menu.file": "ファイル",
    "menu.choose_dir": "MMS_DATA フォルダを選ぶ",
    # 自称名の一覧を出すカスケード。今の UI が読めない人にも当たりが付くよう
    # 英語を併記する
    "menu.language": "言語 / Language",
    "menu.about": "バージョン情報",
    "menu.quit": "終了",
    # ------------------------------------------------------ バージョン情報
    "about.subtitle": "MPS08B (Mold Marshalling System) 演算値トレンドモニタ",
    "about.config": "設定: {path}",
    "about.data": "データ: {path}",
    "about.unset": "(未設定)",
    # ---------------------------------------------------------- ダイアログ
    "dialog.choose_dir_title": "MPS08B の MMS_DATA フォルダを選んでください",
    # ------------------------------------------ 状態帯（core.monitor.STATUS_*）
    "status.running": "監視中",
    "status.idle": "停止中",
    "status.nodata": "データなし",
    "status.noroot": "データフォルダ未設定",
    "status.error": "読み取り異常",
    # ------------------------------------ core が返すメッセージ（MSG_* と 1:1）
    "msg.no_root": "データフォルダが見つからない",
    "msg.read_retry": "読み取り再試行中 ({count}回)",
    "msg.no_data": "データなし",
    "msg.skipped": "{rows}行スキップ",
    # メニューの訳語から組み立てる。ここを固定文にすると、メニューだけ訳を
    # 直したときに案内文が古いまま取り残される
    "msg.hint_choose_dir": "{menu} > {item}",
    # ------------------------------------------------------ コントロールバー
    "control.metric": "項目",
    "control.window": "表示数",
    "control.kind": "形式",
    "control.composite": "合成値",
    "control.delta": "差分列",
    # ------------------------------------- グラフ形式（core.config.CHART_KINDS）
    "chart_kind.line": "折れ線",
    "chart_kind.bar": "棒",
    # ------------------------------- 合成値（core.stats.COMPOSITE_MODES と 1:1）
    "composite.max": "最大",
    "composite.min": "最小",
    "composite.avg": "平均",
    "composite.diff": "差",
    # ------------------------------------------------------------------ 項目
    # 末尾は CSV 列名 `CHnn_<key>` の <key> そのもの。camelCase も原文どおりに
    # 保つ（snake_case へ正規化すると変換表が生まれ、必ず drift する）。
    #
    # 表示名は MPS08B 本体アプリ（PPSB v1.3.0.5）のリソースの表記に合わせて
    # ある。用語が本体と食い違うと現場で混乱するため。対応するリソースキーは
    # `docs/official_terms.csv` にある（`VL_N00`〜`VL_N08` と
    # `SW_RisingTime` / `SW_FallingTime`）。
    "metric.peak": "ピーク",
    "metric.integral": "積分値",
    "metric.peak_time": "ピーク到達",
    "metric.peak_integral": "ピーク積分",
    "metric.pointMonitor": "t秒後値",
    "metric.section_average": "区間平均値",
    "metric.section_integral_1": "区間積分1",
    "metric.section_integral_2": "区間積分2",
    "metric.eject_Monitor": "突出ピーク",
    "metric.RisingTime": "上昇時間",
    "metric.FallingTime": "下降時間",
    # ------------------------------------------------------------ ヘッダパネル
    "header.session": "表示中のデータ",
    "header.cycle": "サイクル {value} s",
    "header.showing": "表示 {shown} / {total} 件",
    # ------------------------------------------------------------ テーブル
    "table.spread": "ばらつき",
    # -------------------------------------------------------------- グラフ
    "chart.no_data": "データなし",
    # 欠番マーカー。グラフ上の狭い場所に 13px 間隔で段組みされるので、
    # 訳文は 5 文字程度までに収めること
    "chart.missing": "{count}欠",
}
