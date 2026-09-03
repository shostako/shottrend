"""`tools/extract_official_terms.py` のバイナリ読みの検証。

本体アプリの exe はリポジトリに入れられない（他社の製品）ので、形式だけを
最小限に組み立てて確かめる。ここが静かに壊れると `find_streams()` が例外を
飲んで「言語が見つからない」としか言わなくなり、原因が見えない。
"""

from __future__ import annotations

import importlib.util
import struct
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parent.parent / "tools" / "extract_official_terms.py"
_spec = importlib.util.spec_from_file_location("extract_official_terms", _TOOL)
assert _spec and _spec.loader
extract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(extract)


def write_7bit(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def write_string(text: str) -> bytes:
    raw = text.encode("utf-8")
    return write_7bit(len(raw)) + raw


def build_resources(entries: dict[str, bytes]) -> bytes:
    """`.resources`（`RuntimeResourceSet`）を最小限で組む。

    ストリーム単体を返す。呼び出し側が任意の位置に埋めて使う。
    """
    names = list(entries)

    data_section = bytearray()
    data_offsets = []
    for name in names:
        data_offsets.append(len(data_section))
        payload = entries[name]
        data_section += write_7bit(extract.TYPE_CODE_STREAM)
        data_section += struct.pack("<i", len(payload)) + payload

    name_section = bytearray()
    name_positions = []
    for name, offset in zip(names, data_offsets, strict=True):
        name_positions.append(len(name_section))
        raw = name.encode("utf-16-le")
        name_section += write_7bit(len(raw)) + raw + struct.pack("<i", offset)

    head = bytearray()
    head += extract.RESOURCE_MAGIC
    head += struct.pack("<ii", 1, 0)  # ヘッダ版と読み飛ばすバイト数
    head += struct.pack("<iii", 2, len(names), 0)  # セット版・件数・型の数
    head += b"\x00" * (-len(head) % 8)  # ← ストリーム先頭からの 8 バイト境界
    head += struct.pack(f"<{len(names)}i", *([0] * len(names)))  # 名前のハッシュ
    head += struct.pack(f"<{len(names)}i", *name_positions)

    data_start = len(head) + 4 + len(name_section)
    head += struct.pack("<i", data_start)
    return bytes(head) + bytes(name_section) + bytes(data_section)


@pytest.mark.parametrize("pad", range(8))
def test_streams_are_found_at_any_file_offset(pad):
    """リソースセットがファイル上のどの位置から始まっても読める。

    8 バイト境界はストリームの先頭から数える。ファイル上の絶対位置で丸めると、
    先頭が 8 の倍数でないリソースセットだけ静かに読めなくなる（実際の exe には
    そういうセットが 19 個あった）。
    """
    blob = build_resources({"stringresources/stringresource.baml": b"BAML-PAYLOAD"})
    data = b"\xaa" * pad + blob

    found = extract.find_streams(data)
    assert "stringresources/stringresource.baml" in found
    offset, size = found["stringresources/stringresource.baml"]
    assert data[offset : offset + size] == b"BAML-PAYLOAD"


def build_baml(pairs: dict[str, str], decoy: bytes = b"", extra_keys: bytes = b"") -> bytes:
    """`x:Key` と値だけを持つ最小の BAML を組む。

    可変長レコードのサイズ欄は「種別バイトを含まず、サイズ欄自身は含む」。
    """

    def record(kind: int, body: bytes) -> bytes:
        size = write_7bit(len(body) + 1)
        # サイズ欄が 1 バイトに収まる前提で組む（テストの文字列は十分短い）
        assert len(size) == 1
        return bytes([kind]) + size + body

    out = bytearray()
    for i, name in enumerate(pairs):
        out += record(extract.REC_STRING_INFO, struct.pack("<h", i) + write_string(name))

    # 値の位置は「最初の値レコード」からの相対。先にレコードを組んで位置を測る
    values = [record(extract.REC_TEXT, write_string(v)) for v in pairs.values()]
    offsets = []
    cursor = 0
    for v in values:
        offsets.append(cursor)
        cursor += len(v)

    for i, offset in enumerate(offsets):
        out += record(
            extract.REC_DEF_KEY_STRING,
            struct.pack("<hi", i, offset) + b"\x01\x01",
        )
    out += extra_keys  # 本物のキーに紛れ込む偽の DefAttributeKeyString
    out += decoy  # 値の並びの手前に置く（種別を知らないレコードの中身のつもり）
    for v in values:
        out += v
    return bytes(out)


def test_baml_keys_and_values_are_paired():
    pairs = {"VL_N00_Peak": "ピーク", "SW_RisingTime": "上昇時間"}
    assert extract.parse_baml(build_baml(pairs)) == pairs


def test_baml_with_no_values_yields_nothing():
    """値レコードが 1 つも無ければ空。基準位置が決まらないため。"""
    assert extract.parse_baml(b"") == {}


def test_bytes_that_merely_look_like_a_record_do_not_shift_the_values():
    """値の並びの手前に偽のレコードがあってもキーと値がずれない。

    種別を知らないレコードの中身も 1 バイトずつ検証にかけるので、`10 02 00`
    （空の Text に読める）のようなバイト列を拾ってしまう。先頭を「最初に
    見つかった値レコード」で決めていると、これだけで全キーが一斉にずれる。
    しかも壊れ方が「空欄の CSV」なので、出力を見ても異常に見えない。
    """
    pairs = {"VL_N00_Peak": "ピーク", "SW_RisingTime": "上昇時間"}
    blob = build_baml(pairs, decoy=b"\x10\x02\x00")
    assert extract.parse_baml(blob) == pairs


def _fake_key_record(offset: int) -> bytes:
    """`REC_DEF_KEY_STRING` として検証を通ってしまうバイト列。"""
    body = struct.pack("<hi", 999, offset) + b"\x01\x01"
    return bytes([extract.REC_DEF_KEY_STRING]) + write_7bit(len(body) + 1) + body


def test_a_spurious_key_does_not_take_down_the_whole_language():
    """偽のキーが混ざっても本物のキーは読める。

    「全部のキーが解決できる候補」を先頭に要求すると、偽キーの出鱈目な相対
    位置が 1 つ混ざるだけでどの候補も条件を満たさなくなり、その言語がまるごと
    落ちる。多数決なら偽キーは 1 票にしかならない。
    """
    pairs = {f"K{i:03d}": f"訳{i}" for i in range(40)}
    blob = build_baml(pairs, extra_keys=_fake_key_record(0x7FFFFF))
    assert extract.parse_baml(blob) == pairs


def test_spurious_text_and_key_together():
    """偽の Text と偽の Key が両方あっても本物が読める。"""
    pairs = {f"K{i:03d}": f"訳{i}" for i in range(40)}
    blob = build_baml(pairs, decoy=b"\x10\x02\x00", extra_keys=_fake_key_record(0x123456))
    assert extract.parse_baml(blob) == pairs


def test_garbage_yields_nothing_rather_than_a_wrong_answer():
    """本物のキーが 1 つも解決できないなら空を返す（誤った対応表を作らない）。"""
    blob = _fake_key_record(0x7FFFFF) * 3 + b"\x10\x02\x00"
    assert extract.parse_baml(blob) == {}


def test_a_language_missing_a_cited_key_is_an_error(monkeypatch, tmp_path):
    """1 言語でも引用キーが欠けたら CSV を書かずに止まる。

    和集合で見ていると、その言語だけ抽出が壊れていても「空欄の並んだ CSV」が
    成功として出てしまう。訳語の根拠として使えないものを黙って残さない。
    """
    full = {key: "x" for key in extract.CITED_KEYS}
    tables = {code: dict(full) for code in extract.COLUMNS[1:]}
    del tables["ko"][extract.CITED_KEYS[0]]
    monkeypatch.setattr(extract, "extract", lambda _path: tables)

    out = tmp_path / "terms.csv"
    assert extract.main(["dummy.exe", "-o", str(out)]) == 1
    assert not out.exists()


def test_complete_tables_are_written(monkeypatch, tmp_path):
    full = {key: "x" for key in extract.CITED_KEYS}
    tables = {code: dict(full) for code in extract.COLUMNS[1:]}
    monkeypatch.setattr(extract, "extract", lambda _path: tables)

    out = tmp_path / "terms.csv"
    assert extract.main(["dummy.exe", "-o", str(out)]) == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == ",".join(extract.COLUMNS)
    assert len(lines) == 1 + len(extract.CITED_KEYS)
