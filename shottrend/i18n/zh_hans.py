"""简体中文の文言。

測定に関わる用語は MPS08B 本体アプリ（PPSB v1.3.0.5）の表記に合わせてある。
対応するリソースキーは `docs/official_terms.csv` を参照。

公式訳から変えた箇所はその行にコメントを残す。

訳さないものは `ja.py` を参照。
"""

from __future__ import annotations

TEXTS: dict[str, str] = {
    # ------------------------------------------------------------------ 全体
    "app.title": "ShotTrend — MPS08B 计算值趋势",
    # ---------------------------------------------------------------- 菜单
    "menu.file": "文件",
    "menu.choose_dir": "选择 MMS_DATA 文件夹",
    "menu.language": "语言 / Language",
    "menu.about": "关于",
    "menu.quit": "退出",
    # -------------------------------------------------------------- 版本信息
    "about.subtitle": "MPS08B (Mold Marshalling System) 计算值趋势监视器",
    "about.config": "设定：{path}",
    "about.data": "数据：{path}",
    "about.unset": "（未设定）",
    # ---------------------------------------------------------------- 对话框
    "dialog.choose_dir_title": "请选择 MPS08B 的 MMS_DATA 文件夹",
    # ---------------------------------------------------------------- 状态
    "status.running": "监视中",
    "status.idle": "停止中",
    "status.nodata": "无数据",
    "status.noroot": "未设定数据文件夹",
    "status.error": "读取异常",
    # ---------------------------------------------------------------- 消息
    "msg.no_root": "找不到数据文件夹",
    "msg.read_retry": "重试读取中（{count}回）",
    "msg.no_data": "无数据",
    "msg.skipped": "跳过 {rows} 行",
    "msg.hint_choose_dir": "{menu} > {item}",
    # ---------------------------------------------------------------- 控制栏
    # 公式の `MT_Item` は「物品」（商品の意）で計測項目にならない
    "control.metric": "项目",
    "control.window": "显示数",
    "control.kind": "形式",
    "control.composite": "合成值",
    "control.delta": "差分列",
    # ---------------------------------------------------------------- 图表
    "chart_kind.line": "折线",
    "chart_kind.bar": "柱状",
    # ---------------------------------------------------------------- 合成
    # 公式の `Max` は「最高」。誤りではないが、最小・平均と並ぶ選択肢なので
    # 系統を揃えた（繁体は公式も「最大」）
    "composite.max": "最大",
    "composite.min": "最小",
    "composite.avg": "平均",
    "composite.diff": "差",
    # ---------------------------------------------------------------- 项目
    "metric.peak": "高峰",
    "metric.integral": "积分值",
    "metric.peak_time": "高峰到达",
    "metric.peak_integral": "高峰积分",
    "metric.pointMonitor": "t秒后值",
    "metric.section_average": "区间平均值",
    "metric.section_integral_1": "区间积分1",
    "metric.section_integral_2": "区间积分2",
    "metric.eject_Monitor": "顶出高峰",
    "metric.RisingTime": "上升时间",
    # 公式の `SW_FallingTime` は「上升时间」＝上昇時間。逆の意味になっている
    "metric.FallingTime": "下降时间",
    # -------------------------------------------------------------- ヘッダ
    "header.session": "显示中的数据",
    "header.cycle": "周期 {value} s",
    "header.showing": "显示 {shown} / {total} 条",
    # ---------------------------------------------------------------- 表
    "table.spread": "偏差",
    # -------------------------------------------------------------- グラフ
    "chart.no_data": "无数据",
    "chart.missing": "缺{count}",
}
