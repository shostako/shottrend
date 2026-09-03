"""한국어の文言。

測定に関わる用語は MPS08B 本体アプリ（PPSB v1.3.0.5）の表記に合わせてある。
対応するリソースキーは `docs/official_terms.csv` を参照。

**公式の韓国語訳は機械翻訳の質が低く、意味が壊れているものがある。** 語感が
古い・不自然という程度なら公式のまま残し、意味が違うものだけ直す。変えた行には
公式の訳を添えておく（本体と食い違う理由が後から追えるように）。

訳さないものは `ja.py` を参照。
"""

from __future__ import annotations

TEXTS: dict[str, str] = {
    # ------------------------------------------------------------------ 全体
    "app.title": "ShotTrend — MPS08B 연산값 추이",
    # ---------------------------------------------------------------- メニュー
    "menu.file": "파일",
    "menu.choose_dir": "MMS_DATA 폴더 선택",
    "menu.language": "언어 / Language",
    # 公式の `MW_About` は「약」（＝約）。about の誤訳
    "menu.about": "버전 정보",
    "menu.quit": "종료",
    # ------------------------------------------------------------ バージョン
    "about.subtitle": "MPS08B (Mold Marshalling System) 연산값 추이 모니터",
    "about.config": "설정: {path}",
    "about.data": "데이터: {path}",
    "about.unset": "(설정 안 됨)",
    # ---------------------------------------------------------- ダイアログ
    "dialog.choose_dir_title": "MPS08B의 MMS_DATA 폴더를 선택하세요",
    # ---------------------------------------------------------------- 状態
    "status.running": "감시 중",
    "status.idle": "정지 중",
    "status.nodata": "데이터 없음",
    "status.noroot": "데이터 폴더 미설정",
    "status.error": "읽기 오류",
    # -------------------------------------------------------------- メッセージ
    "msg.no_root": "데이터 폴더를 찾을 수 없습니다",
    # 公式の `times` は「타임스」（times の音写）
    "msg.read_retry": "읽기 재시도 중 ({count}회)",
    "msg.no_data": "데이터 없음",
    "msg.skipped": "{rows}행 건너뜀",
    "msg.hint_choose_dir": "{menu} > {item}",
    # ------------------------------------------------------ コントロールバー
    # 公式の `MT_Item` は「안건」（＝議案）で計測項目にならない
    "control.metric": "항목",
    "control.window": "표시 수",
    "control.kind": "형식",
    "control.composite": "합성값",
    "control.delta": "차분 열",
    # ---------------------------------------------------------------- グラフ
    "chart_kind.line": "꺾은선",
    "chart_kind.bar": "막대",
    # ---------------------------------------------------------------- 合成
    "composite.max": "최대",
    "composite.min": "최소",
    "composite.avg": "평균",
    "composite.diff": "차",
    # ---------------------------------------------------------------- 項目
    "metric.peak": "피크",
    # 公式の `Integral` は「완전한」（＝完全な）。`VL_N01` 側の「적분값」を採る
    "metric.integral": "적분값",
    "metric.peak_time": "피크 도달",
    "metric.peak_integral": "피크 적분",
    "metric.pointMonitor": "t초값",
    "metric.section_average": "구간 평균 값",
    "metric.section_integral_1": "구간 적분 1",
    "metric.section_integral_2": "구간 적분 2",
    "metric.eject_Monitor": "돌출 피크",
    "metric.RisingTime": "상승 시간",
    # 公式は「떨어지는 시간」。「상승 시간」と対にならず座りが悪いが、意味は
    # 通るので本体の表記に合わせる
    "metric.FallingTime": "떨어지는 시간",
    # -------------------------------------------------------------- ヘッダ
    "header.session": "표시 중인 데이터",
    "header.cycle": "사이클 {value} s",
    "header.showing": "표시 {shown} / {total} 건",
    # ---------------------------------------------------------------- テーブル
    "table.spread": "편차",
    # -------------------------------------------------------------- グラフ
    "chart.no_data": "데이터 없음",
    "chart.missing": "누락 {count}",
}
