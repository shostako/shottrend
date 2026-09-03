"""繁體中文の文言。

測定に関わる用語は MPS08B 本体アプリ（PPSB v1.3.0.5）の表記に合わせてある。
対応するリソースキーは `docs/official_terms.csv` を参照（`tools/
extract_official_terms.py` で作り直せる）。

公式訳から変えた箇所はその行にコメントを残す。

訳さないものは `ja.py` を参照。
"""

from __future__ import annotations

TEXTS: dict[str, str] = {
    # ------------------------------------------------------------------ 全体
    "app.title": "ShotTrend — MPS08B 計算值趨勢",
    # ---------------------------------------------------------------- 選單
    "menu.file": "檔案",
    "menu.choose_dir": "選擇 MMS_DATA 文件夾",
    "menu.language": "語言 / Language",
    "menu.about": "版本資訊",
    "menu.quit": "退出",
    # ------------------------------------------------------------ 版本資訊
    "about.subtitle": "MPS08B (Mold Marshalling System) 計算值趨勢監視器",
    "about.config": "設定：{path}",
    "about.data": "數據：{path}",
    "about.unset": "（未設定）",
    # ------------------------------------------------------------ 對話方塊
    "dialog.choose_dir_title": "請選擇 MPS08B 的 MMS_DATA 文件夾",
    # ---------------------------------------------------------------- 狀態
    "status.running": "監視中",
    "status.idle": "停止中",
    "status.nodata": "無數據",
    "status.noroot": "未設定數據文件夾",
    "status.error": "讀取異常",
    # ---------------------------------------------------------------- 訊息
    "msg.no_root": "找不到數據文件夾",
    "msg.read_retry": "重試讀取中（{count}次）",
    "msg.no_data": "無數據",
    "msg.skipped": "跳過 {rows} 行",
    "msg.hint_choose_dir": "{menu} > {item}",
    # ---------------------------------------------------------- 控制列
    # 公式の `MT_Item` は「物品」（商品の意）で計測項目にならない
    "control.metric": "項目",
    "control.window": "顯示數",
    "control.kind": "形式",
    "control.composite": "合成值",
    "control.delta": "差分列",
    # ---------------------------------------------------------------- 圖表
    "chart_kind.line": "折線",
    "chart_kind.bar": "長條",
    # ---------------------------------------------------------------- 合成
    "composite.max": "最大",
    "composite.min": "最小",
    "composite.avg": "平均",
    "composite.diff": "差",
    # ---------------------------------------------------------------- 項目
    "metric.peak": "峰值",
    "metric.integral": "積分值",
    "metric.peak_time": "峰值到達",
    "metric.peak_integral": "峰值積分",
    "metric.pointMonitor": "t秒後值",
    "metric.section_average": "區段平均值",
    "metric.section_integral_1": "區段積分1",
    "metric.section_integral_2": "區段積分2",
    "metric.eject_Monitor": "頂出峰值",
    "metric.RisingTime": "上升時間",
    "metric.FallingTime": "下降時間",
    # -------------------------------------------------------------- ヘッダ
    "header.session": "顯示中的數據",
    "header.cycle": "週期 {value} s",
    "header.showing": "顯示 {shown} / {total} 筆",
    # ---------------------------------------------------------------- 表
    "table.spread": "偏差",
    # -------------------------------------------------------------- グラフ
    "chart.no_data": "無數據",
    "chart.missing": "缺{count}",
}
