"""横一列に並べたものを、幅が足りなければ次の行へ送る（折り返し）計算。

tkinter を import しない純粋な計算にしてあるのは、テストが GUI 環境を要求
しないようにするため。ウィジェット側は測った幅を渡して、返ってきた行割りで
`grid()` し直すだけ。
"""

from __future__ import annotations


def pack_rows(widths: list[int], gap: int, avail: int) -> list[list[int]]:
    """幅 `widths` の要素を左から詰め、`avail` に収まらなくなったら改行する。

    戻り値は行ごとの要素インデックスの並び。1 つでも `avail` より広い要素は
    それだけで 1 行を占める（どこかには置かないといけない）。要素が無ければ
    空のリスト。
    """
    rows: list[list[int]] = []
    row: list[int] = []
    used = 0
    for i, w in enumerate(widths):
        need = w if not row else used + gap + w
        if row and need > avail:
            rows.append(row)
            row, used = [i], w
        else:
            row.append(i)
            used = need
    if row:
        rows.append(row)
    return rows


def single_row_width(widths: list[int], gap: int) -> int:
    """全部を 1 行に並べたときの幅。"""
    if not widths:
        return 0
    return sum(widths) + gap * (len(widths) - 1)
