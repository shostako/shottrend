"""サマリ CSV に入っている ch ごとの演算値の一覧。

MPS08B は 1 ショットにつき ch ごとに 12 個の演算値を書く（`CHnn_<key>` 列）。
そのうち `error` を除く 11 個を表示項目として選べるようにする。

表示名はここには無い。言語で変わるので `i18n` が持つ（core は言語を
知らない）。訳語の根拠も `i18n/ja.py` の該当行に書いてある。

単位はヘッダに書かれていないため、量の意味から付けている（圧力 MPa、
時間 s、圧力の時間積分 MPa·s）。単位は訳さないので core に残る。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Metric:
    key: str
    """CSV の列名 `CHnn_<key>` の <key> 部分。表示名は持たない。

    画面に出す名前は言語で変わるので `i18n.metric_label(key)` が持つ
    （core は言語を知らない）。
    """
    unit: str
    """訳さない。MPa などの単位記号は万国共通で、量の意味から決まる。"""
    digits: int
    """小数点以下の桁数。CSV に書かれている精度をそのまま出す。"""

    def fmt(self, value: float) -> str:
        return f"{value:.{self.digits}f}"


METRICS: tuple[Metric, ...] = (
    Metric("peak", "MPa", 2),
    Metric("integral", "MPa·s", 2),
    Metric("peak_time", "s", 3),
    Metric("peak_integral", "MPa·s", 2),
    Metric("pointMonitor", "MPa", 2),
    Metric("section_average", "MPa", 2),
    Metric("section_integral_1", "MPa·s", 2),
    Metric("section_integral_2", "MPa·s", 2),
    Metric("eject_Monitor", "MPa", 2),
    Metric("RisingTime", "s", 3),
    Metric("FallingTime", "s", 3),
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
