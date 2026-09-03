"""MPS08B 本体アプリから 5 言語の対訳を抜き出す。

    python tools/extract_official_terms.py <MPS08B_Application_*.exe> -o docs/official_terms.csv

ShotTrend の訳語は本体アプリ（PPSB）の表記に合わせてある。同じ値を違う言葉で
呼ぶと現場で混乱するため。その根拠を残し、本体が更新されたときに差分を見られる
ようにするのがこのスクリプトの目的で、カタログ（`shottrend/i18n/*.py`）は手で
書く。公式訳をそのまま使う箇所と、誤訳なので直す箇所の判断が要るから。

**既定では ShotTrend が実際に根拠にしているキーだけを書き出す**（`CITED_KEYS`）。
本体アプリの文字列は双葉電子工業の著作物なので、公開リポジトリに全 352 件を
そのまま置かない。全部見たいときは `--all` を付ける（手元で見るだけにすること）。

パスは引数で受ける。本体アプリの置き場は環境ごとに違う。

--------------------------------------------------------------------- 中の話

本体は WPF アプリで、5 言語分の文字列を `ResourceDictionary` の XAML として
持ち、コンパイル済みの BAML が exe の `.g.resources` に埋まっている:

    stringresources/stringresource.baml          英語（ニュートラル）
    stringresources/stringresource.ja-jp.baml    日本語
    stringresources/stringresource.ko-kr.baml    韓国語
    stringresources/stringresource.zh-cn.baml    簡体中文
    stringresources/stringresource.zh-hant.baml  繁體中文

外部ツールは使わない（標準ライブラリだけで読める程度の形式で、読めることは
実データで確認済み）。2 段構えで読む:

1. `.NET` の `.resources`（magic `0xBEEFCACE`）を辿って BAML の位置と長さを得る
2. BAML のレコード列から `x:Key` と値の文字列を拾う

BAML はレコード列で、可変長のレコードは種別バイトの直後に 7bit エンコードの
サイズを持つ。**このサイズは種別バイトを含まず、サイズ自身は含む**（実データで
確認: `AssemblyInfo` の総長 80 バイトに対しサイズ欄は 79）。ここを間違えると
何も拾えないので、レコードを 1 件ずつ「サイズと実際の長さが一致するか」で
検証しながら走査する。総当たりで走査して検証に通ったものだけ採るので、途中に
未知のレコードがあっても止まらない。
"""

from __future__ import annotations

import argparse
import csv
import struct
import sys
from pathlib import Path

#: .NET の `.resources` の先頭 4 バイト。
RESOURCE_MAGIC = struct.pack("<I", 0xBEEFCACE)

#: `ResourceTypeCode.Stream`。BAML はこれで入っている。
TYPE_CODE_STREAM = 33

#: BAML のレコード種別。使うのはこの 3 つだけ。
REC_TEXT_WITH_CONVERTER = 0x11  # 値の文字列（末尾に int16 のコンバータ ID）
REC_TEXT = 0x10  # 値の文字列（コンバータ無し）
REC_STRING_INFO = 0x20  # 文字列表（x:Key の名前がここに入る）
REC_DEF_KEY_STRING = 0x26  # x:Key -> 値の位置

#: リソース名の末尾 -> 言語コード。ニュートラルは英語。
LANG_BY_SUFFIX = {
    "stringresource.baml": "en",
    "stringresource.ja-jp.baml": "ja",
    "stringresource.ko-kr.baml": "ko",
    "stringresource.zh-cn.baml": "zh-Hans",
    "stringresource.zh-hant.baml": "zh-Hant",
}

COLUMNS = ("key", "en", "ja", "zh-Hant", "zh-Hans", "ko")

#: ShotTrend が訳語の根拠にしているリソースキー。`VL_N00`〜`VL_N08` が表示項目
#: 9 つに、`SW_*Time` が残る 2 つに対応する。あとは、公式訳が壊れていて直した
#: 語（`docs/official_terms.csv` を見れば「何を直したか」が分かるように残す）。
CITED_KEYS = (
    "VL_N00_Peak",
    "VL_N01_Integral",
    "VL_N02_PeakTime",
    "VL_N03_PeakIntegral",
    "VL_N04_tPoint",
    "VL_N05_SectionAverage",
    "VL_N06_SectionIntegral1",
    "VL_N07_SectionIntegral2",
    "VL_N08_EjectPeak",
    "SW_RisingTime",
    "SW_FallingTime",
    "MW_Menu_File",
    "MW_About",
    "MT_Item",
    "Max",
    "Integral",
    "times",
)


def read_7bit(buf: bytes, pos: int) -> tuple[int, int]:
    """`BinaryWriter.Write7BitEncodedInt` の逆。(値, 次の位置) を返す。"""
    value = 0
    shift = 0
    while True:
        byte = buf[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7


def read_string(buf: bytes, pos: int) -> tuple[str, int]:
    """`BinaryWriter.Write(string)` の逆。長さ前置きの UTF-8。"""
    length, pos = read_7bit(buf, pos)
    return buf[pos : pos + length].decode("utf-8"), pos + length


# ------------------------------------------------------------ .NET .resources


def find_streams(data: bytes) -> dict[str, tuple[int, int]]:
    """`.resources` を全部辿って、名前 -> (位置, 長さ) を返す。"""
    out: dict[str, tuple[int, int]] = {}
    start = 0
    while True:
        base = data.find(RESOURCE_MAGIC, start)
        if base < 0:
            return out
        start = base + 1
        try:
            out.update(_parse_resource_set(data, base))
        except Exception:
            # 画像やアイコンだけのリソースセットもある。読めないものは飛ばす
            continue


def _parse_resource_set(data: bytes, base: int) -> dict[str, tuple[int, int]]:
    pos = base + 4
    _version, skip = struct.unpack_from("<ii", data, pos)
    pos += 8 + skip  # リーダの型名など。中身は使わない

    _set_version, count, type_count = struct.unpack_from("<iii", data, pos)
    pos += 12
    for _ in range(type_count):
        length, pos = read_7bit(data, pos)
        pos += length
    pos = (pos + 7) & ~7  # 名前ハッシュの手前で 8 バイト境界に揃う

    pos += 4 * count  # 名前のハッシュ。引くのに使うだけなので読み飛ばす
    positions = struct.unpack_from(f"<{count}i", data, pos)
    pos += 4 * count
    (data_section,) = struct.unpack_from("<i", data, pos)
    name_section = pos + 4

    out: dict[str, tuple[int, int]] = {}
    for offset in positions:
        p = name_section + offset
        length, p = read_7bit(data, p)
        name = data[p : p + length].decode("utf-16-le")
        p += length
        (value_offset,) = struct.unpack_from("<i", data, p)

        q = base + data_section + value_offset
        type_code, q = read_7bit(data, q)
        if type_code != TYPE_CODE_STREAM:
            continue
        (size,) = struct.unpack_from("<i", data, q)
        out[name] = (q + 4, size)
    return out


# --------------------------------------------------------------------- BAML


def parse_baml(blob: bytes) -> dict[str, str]:
    """1 言語分の `ResourceDictionary` を キー -> 訳文 にする。"""
    names: dict[int, str] = {}  # StringInfo の ID -> 文字列
    keys: list[tuple[int, int]] = []  # (名前の ID, 値の位置)
    texts: dict[int, str] = {}  # レコードの位置 -> 訳文

    pos = 0
    end = len(blob)
    while pos < end:
        record = _read_record(blob, pos)
        if record is None:
            pos += 1
            continue
        kind, payload, pos = record
        if kind == REC_STRING_INFO:
            names[payload[0]] = payload[1]
        elif kind == REC_DEF_KEY_STRING:
            keys.append(payload)
        else:
            texts[payload[0]] = payload[1]

    if not texts:
        return {}
    # 値の位置は「最初の値レコード」からの相対。実データで一致を確認済み
    origin = min(texts)
    out: dict[str, str] = {}
    for name_id, offset in keys:
        name = names.get(name_id)
        text = texts.get(origin + offset)
        if name is not None and text is not None:
            out[name] = text
    return out


def _read_record(blob: bytes, pos: int):
    """`pos` から 1 レコード読む。サイズが合わなければ None（＝ここではない）。"""
    kind = blob[pos]
    if kind not in (REC_TEXT, REC_TEXT_WITH_CONVERTER, REC_STRING_INFO, REC_DEF_KEY_STRING):
        return None
    try:
        size, p = read_7bit(blob, pos + 1)
        if kind == REC_STRING_INFO:
            (string_id,) = struct.unpack_from("<h", blob, p)
            value, p = read_string(blob, p + 2)
            payload = (string_id, value)
        elif kind == REC_DEF_KEY_STRING:
            string_id, offset = struct.unpack_from("<hi", blob, p)
            p += 6 + 2  # Shared / SharedSet の bool 2 つ
            payload = (string_id, offset)
        else:
            value, p = read_string(blob, p)
            if kind == REC_TEXT_WITH_CONVERTER:
                p += 2  # コンバータの型 ID
            payload = (pos, value)
    except (IndexError, struct.error, UnicodeDecodeError):
        return None
    # サイズ欄は種別バイトを含まず、サイズ欄自身は含む
    if p - pos != size + 1:
        return None
    return kind, payload, p


# --------------------------------------------------------------------- main


def extract(exe: Path) -> dict[str, dict[str, str]]:
    data = exe.read_bytes()
    streams = find_streams(data)
    tables: dict[str, dict[str, str]] = {}
    for name, (offset, size) in streams.items():
        lang = LANG_BY_SUFFIX.get(name.rsplit("/", 1)[-1].lower())
        if lang is None:
            continue
        tables[lang] = parse_baml(data[offset : offset + size])
    return tables


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("exe", type=Path, help="MPS08B_Application_*.exe")
    ap.add_argument("-o", "--out", type=Path, default=Path("docs/official_terms.csv"))
    ap.add_argument(
        "--all",
        action="store_true",
        help="CITED_KEYS に絞らず全キーを出す（手元で調べるとき用。公開リポには置かない）",
    )
    args = ap.parse_args(argv)

    tables = extract(args.exe)
    missing = [code for code in COLUMNS[1:] if code not in tables]
    if missing:
        print(f"言語が見つからない: {missing}", file=sys.stderr)
        return 1

    if args.all:
        all_keys = sorted(set().union(*(t.keys() for t in tables.values())))
    else:
        found = set().union(*(t.keys() for t in tables.values()))
        unknown = [k for k in CITED_KEYS if k not in found]
        if unknown:
            print(f"本体に無いキー: {unknown}", file=sys.stderr)
            return 1
        all_keys = list(CITED_KEYS)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        # 既定の CRLF ではなく LF。リポジトリの他のファイルと揃え、再実行
        # したときに改行だけの差分が出ないようにする
        w = csv.writer(f, lineterminator="\n")
        w.writerow(COLUMNS)
        for key in all_keys:
            w.writerow([key] + [tables[c].get(key, "") for c in COLUMNS[1:]])

    print(f"{args.out}: {len(all_keys)} keys / 本体には {len(tables['ja'])} キーある")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
