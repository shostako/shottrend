"""設定の正規化。手で編集された config.json でも落ちないこと。"""

from __future__ import annotations

import json

from core.config import AppConfig, load_config, save_config


def test_unknown_metric_falls_back_to_peak(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"metric": "no_such_metric"}), encoding="utf-8")
    assert load_config(p).metric == "peak"


def test_metric_round_trips(tmp_path):
    p = tmp_path / "config.json"
    cfg = AppConfig(metric="peak_time")
    save_config(cfg, p)
    assert load_config(p).metric == "peak_time"


def test_unknown_keys_are_ignored(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"metric": "integral", "bogus": 1}), encoding="utf-8")
    assert load_config(p).metric == "integral"
