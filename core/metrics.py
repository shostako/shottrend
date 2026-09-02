"""サマリ CSV に入っている ch ごとの演算値の一覧。

MPS08B は 1 ショットにつき ch ごとに 12 個の演算値を書く（`CHnn_<key>` 列）。
そのうち `error` を除く 11 個を表示項目として選べるようにする。

表示名は本体アプリ（PPSB v1.3.0.5）の演算値プルダウンに合わせた。本体の
隣に並べたときに同じ言葉で読めることを優先する。立上り／立下り時間は
本体のプルダウンには無いが CSV には入っているので、こちらで名前を付けた。

単位はヘッダに書かれていないため、量の意味から付けている（圧力 MPa、
時間 s、圧力の時間積分 MPa·s）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Metric:
    key: str
    """CSV の列名 `CHnn_<key>` の <key> 部分。"""
    label: str
    """画面に出す名前。本体アプリの表記に合わせる。"""
    unit: str
    digits: int
    """小数点以下の桁数。CSV に書かれている精度をそのまま出す。"""

    def fmt(self, value: float) -> str:
        return f"{value:.{self.digits}f}"


METRICS: tuple[Metric, ...] = (
    Metric("peak", "ピーク", "MPa", 2),
    Metric("integral", "積分値", "MPa·s", 2),
    Metric("peak_time", "ピーク到達", "s", 3),
    Metric("peak_integral", "ピーク積分", "MPa·s", 2),
    Metric("pointMonitor", "t秒後値", "MPa", 2),
    Metric("section_average", "区間平均値", "MPa", 2),
    Metric("section_integral_1", "区間積分1", "MPa·s", 2),
    Metric("section_integral_2", "区間積分2", "MPa·s", 2),
    Metric("eject_Monitor", "突出ピーク", "MPa", 2),
    Metric("RisingTime", "立上り時間", "s", 3),
    Metric("FallingTime", "立下り時間", "s", 3),
)

#: センサが繋がっているかの判定にも使う基準の項目。必ず存在する
DEFAULT_METRIC = "peak"

METRIC_KEYS: tuple[str, ...] = tuple(m.key for m in METRICS)
_BY_KEY = {m.key: m for m in METRICS}


def metric(key: str) -> Metric:
    """キーから項目を引く。知らないキーはピークに倒す（設定ファイルの手編集対策）。"""
    return _BY_KEY.get(key, _BY_KEY[DEFAULT_METRIC])


def column_name(key: str, ch_index: int) -> str:
    """0 始まりのチャンネル番号と項目キーから CSV の列名を作る。"""
    return f"CH{ch_index + 1:02d}_{key}"
