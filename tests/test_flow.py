from shottrend.ui.flow import pack_rows, single_row_width


def test_fits_in_one_row():
    assert pack_rows([100, 100, 100], gap=10, avail=320) == [[0, 1, 2]]


def test_wraps_when_gap_pushes_over():
    # 100+10+100 = 210 は入るが、+10+100 = 320 で avail=319 を超える
    assert pack_rows([100, 100, 100], gap=10, avail=319) == [[0, 1], [2]]


def test_oversized_item_takes_its_own_row():
    assert pack_rows([500, 50, 50], gap=10, avail=200) == [[0], [1, 2]]
    assert pack_rows([50, 500, 50], gap=10, avail=200) == [[0], [1], [2]]


def test_every_item_placed_exactly_once():
    widths = [174, 200, 180, 277, 63]
    for avail in range(1, 1200, 7):
        rows = pack_rows(widths, gap=22, avail=avail)
        flat = [i for row in rows for i in row]
        assert flat == list(range(len(widths))), avail
        # どの行も、複数要素なら avail に収まっている
        for row in rows:
            if len(row) > 1:
                assert single_row_width([widths[i] for i in row], 22) <= avail


def test_single_row_width():
    assert single_row_width([], 22) == 0
    assert single_row_width([100], 22) == 100
    assert single_row_width([100, 50], 22) == 172


def test_wide_enough_never_wraps():
    widths = [174, 200, 180, 277, 63]
    assert pack_rows(widths, 22, single_row_width(widths, 22)) == [[0, 1, 2, 3, 4]]
