"""設定の正規化。手で編集された config.json でも落ちないこと。"""

from __future__ import annotations

import json

from shottrend.core.config import AppConfig, app_dir, load_config, save_config


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


def test_config_with_utf8_bom_is_read(tmp_path):
    """メモ帳や PowerShell 5.1 が付ける BOM 付きでも読める。"""
    p = tmp_path / "config.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"metric": "integral"}).encode("utf-8"))
    assert load_config(p).metric == "integral"


def test_app_dir_is_the_directory_holding_app_pyw():
    """ソース実行時の設定の置き場は app.pyw の隣。パッケージを動かすとここがずれる。"""
    d = app_dir()
    assert (d / "app.pyw").is_file(), d
    assert not (d / "core").is_dir()  # パッケージ内 (shottrend/) を指していない
