"""tk.Canvas で自前描画するウィジェット群。

ttk の既定ウィジェットは見た目の制御が効かないので、状態が一目で分かる
必要のあるパーツ（トグル、状態帯、カード）は Canvas に直接描く。
依存を増やさずに見た目を詰められるのが利点。
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from . import theme


def round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kw):
    """角丸矩形。smooth=True のポリゴンで近似する。"""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [
        x1 + r,
        y1,
        x2 - r,
        y1,
        x2,
        y1,
        x2,
        y1 + r,
        x2,
        y2 - r,
        x2,
        y2,
        x2 - r,
        y2,
        x1 + r,
        y2,
        x1,
        y2,
        x1,
        y2 - r,
        x1,
        y1 + r,
        x1,
        y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


class SegmentedControl(tk.Canvas):
    """1 つだけ選べる横並びのボタン列。

    選択中がはっきり分かることを最優先にしている。表示件数やグラフ形式の
    切替は「今どれが効いているか」が読めないと意味がない。
    """

    def __init__(
        self,
        parent: tk.Misc,
        options: list[tuple[object, str]],
        initial: object,
        on_change: Callable[[object], None],
        *,
        seg_width: int = 54,
        height: int = 28,
        bg: str = theme.BG,
    ) -> None:
        # 属性の代入は必ず super().__init__() の後に行う。
        # tkinter.Misc は内部で self._options(cnf) を呼ぶため、その名前を
        # 先に潰すと 'list' object is not callable で初期化が死ぬ。
        # 同じ理由で名前も _segments にしてある。
        width = seg_width * len(options) + 2
        super().__init__(
            parent, width=width, height=height, background=bg, highlightthickness=0, bd=0
        )
        self._segments = options
        self._value = initial
        self._on_change = on_change
        self._seg_w = seg_width
        self._hover = -1
        self.bind("<Button-1>", self._on_click)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self._redraw()

    @property
    def value(self) -> object:
        return self._value

    def set_value(self, value: object) -> None:
        if value == self._value:
            return
        self._value = value
        self._redraw()

    # ----------------------------------------------------------------- events

    def _index_at(self, x: int) -> int:
        i = int((x - 1) // self._seg_w)
        return i if 0 <= i < len(self._segments) else -1

    def _on_click(self, event) -> None:
        i = self._index_at(event.x)
        if i < 0:
            return
        value = self._segments[i][0]
        if value == self._value:
            return
        self._value = value
        self._redraw()
        self._on_change(value)

    def _on_motion(self, event) -> None:
        i = self._index_at(event.x)
        if i != self._hover:
            self._hover = i
            self.configure(cursor="hand2" if i >= 0 else "")
            self._redraw()

    def _on_leave(self, _event) -> None:
        if self._hover != -1:
            self._hover = -1
            self.configure(cursor="")
            self._redraw()

    # ---------------------------------------------------------------- drawing

    def _redraw(self) -> None:
        """背景 → 選択の塗り → 区切り線 → 外枠 → 文字 の順に重ねる。

        セグメントを 1 つずつ「枠付きで」描くと、端の角丸を四角く戻す塗りが
        隣との境界線を消してしまう。塗りを全部置いてから線を引くことで、
        どのセグメントが選ばれていても境界が必ず残る。
        """
        self.delete("all")
        h = int(self["height"])
        n = len(self._segments)
        left, right = 1, 1 + self._seg_w * n

        # 1. 背景（全体で 1 つの角丸）
        round_rect(self, left, 1, right, h - 1, 6, fill=theme.PANEL, outline="")

        # 2. 選択・ホバーの塗り
        for i, (value, _label) in enumerate(self._segments):
            if value == self._value:
                fill = theme.ACCENT
            elif i == self._hover:
                fill = theme.ACCENT_SOFT
            else:
                continue
            x0 = 1 + i * self._seg_w
            x1 = x0 + self._seg_w
            first, last = i == 0, i == n - 1
            if first or last:
                # 端は外側だけ丸め、内側の角は塗り足して四角く戻す
                round_rect(self, x0, 1, x1, h - 1, 6, fill=fill, outline=fill)
                if not first:
                    self.create_rectangle(x0, 1, x0 + 7, h - 1, fill=fill, outline=fill)
                if not last:
                    self.create_rectangle(x1 - 7, 1, x1, h - 1, fill=fill, outline=fill)
            else:
                self.create_rectangle(x0, 1, x1, h - 1, fill=fill, outline=fill)

        # 3. 区切り線（塗りの上に引くので必ず見える）
        for i in range(1, n):
            x = 1 + i * self._seg_w
            self.create_line(x, 2, x, h - 2, fill=theme.BORDER)

        # 4. 外枠
        round_rect(self, left, 1, right, h - 1, 6, fill="", outline=theme.BORDER)

        # 5. 文字
        for i, (value, label) in enumerate(self._segments):
            x0 = 1 + i * self._seg_w
            if value == self._value:
                fg = "#FFFFFF"
            elif i == self._hover:
                fg = theme.FG
            else:
                fg = theme.MUTED
            self.create_text(x0 + self._seg_w / 2, h / 2, text=label, fill=fg, font=theme.F_LABEL)


class StatusStrip(tk.Canvas):
    """画面上部の状態帯。本体アプリの「モニタモード」帯に相当する。

    今どういう状態なのかが、離れた位置からでも色で分かることを狙う。
    """

    HEIGHT = 24

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent, height=self.HEIGHT, background=theme.BG, highlightthickness=0, bd=0
        )
        self._text = ""
        self._sub = ""
        self._color = theme.ACCENT_BAR
        self._fg = "#00323C"
        self.bind("<Configure>", lambda _e: self._redraw())

    def set_state(self, text: str, sub: str, color: str, fg: str = "#00323C") -> None:
        if (text, sub, color) == (self._text, self._sub, self._color):
            return
        self._text, self._sub, self._color, self._fg = text, sub, color, fg
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self.HEIGHT
        self.create_rectangle(0, 0, w, h, fill=self._color, outline=self._color)
        self.create_text(12, h / 2, text=self._text, anchor="w", fill=self._fg, font=theme.F_TITLE)
        if self._sub:
            self.create_text(
                w - 12, h / 2, text=self._sub, anchor="e", fill=self._fg, font=theme.F_SMALL
            )


class ChannelCard(tk.Canvas):
    """1 系列分の最新値・前ショットとの差・統計を 1 枚に収める。

    ch ごとのカードにも、合成値のカードにも使う。カード全体を Canvas に描く
    ことで、角丸や色チップ、数値の位置を自由に決められる。

    推移の小グラフ（スパークライン）は置かない。すぐ下に同じデータの本物の
    グラフがあり、二重に出しても読む場所が増えるだけだった。

    幅は親のグリッドに追従する（WIDTH は最小幅）。
    """

    WIDTH = 240
    HEIGHT = 150

    def __init__(self, parent: tk.Misc, name: str, color: str, text_color: str) -> None:
        super().__init__(
            parent,
            width=self.WIDTH,
            height=self.HEIGHT,
            background=theme.BG,
            highlightthickness=0,
            bd=0,
        )
        self._name = name
        self._color = color
        self._text_color = text_color
        self._value: float | None = None
        self._delta: float | None = None
        self._stats = None
        self.bind("<Configure>", lambda _e: self._redraw())
        self._redraw()

    def _width(self) -> int:
        # 配置前は winfo_width() が 1 を返す
        w = self.winfo_width()
        return w if w > 1 else self.WIDTH

    def set_data(self, value, delta, stats) -> None:
        self._value = value
        self._delta = delta
        self._stats = stats
        self._redraw()

    # ---------------------------------------------------------------- drawing

    def _redraw(self) -> None:
        self.delete("all")
        w, h = self._width(), self.HEIGHT
        round_rect(self, 1, 1, w - 1, h - 1, 8, fill=theme.PANEL, outline=theme.PANEL_EDGE)

        # 左端の色帯。どのチャンネルのカードか離れていても分かる
        self.create_rectangle(1, 12, 5, h - 12, fill=self._color, outline="")

        # --- 見出し ---
        self.create_rectangle(16, 15, 26, 25, fill=self._color, outline=theme.CHIP_EDGE)
        self.create_text(32, 20, text=self._name, anchor="w", fill=theme.FG, font=theme.F_TITLE)
        self._draw_delta(w - 16, 20)

        # --- 最新値 ---
        if self._value is None:
            self.create_text(20, 62, text="--.--", anchor="w", fill=theme.DIM, font=theme.F_HUGE)
            return
        num = self.create_text(
            20,
            62,
            text=f"{self._value:.2f}",
            anchor="w",
            fill=self._text_color,
            font=theme.F_HUGE,
        )
        # 単位は数値の実寸に合わせて添える。見出しに置くと数字と離れて読みにくい
        x_end = self.bbox(num)[2]
        self.create_text(x_end + 6, 74, text="MPa", anchor="w", fill=theme.DIM, font=theme.F_SMALL)
        self._draw_stats(20, 100, w - 20)

    def _draw_delta(self, x: float, y: float) -> None:
        if self._delta is None:
            return
        d = self._delta
        if abs(d) < 0.005:
            mark, color = "→", theme.FLAT
        elif d > 0:
            mark, color = "▲", theme.UP
        else:
            mark, color = "▼", theme.DOWN
        self.create_text(
            x,
            y,
            text=f"{mark} {abs(d):.2f}",
            anchor="e",
            fill=color,
            font=theme.F_STAT,
        )

    def _draw_stats(self, x: float, y: float, right: float) -> None:
        st = self._stats
        if st is None or st.empty:
            return
        self.create_line(x, y - 8, right, y - 8, fill=theme.PANEL_ALT)
        pairs = (
            ("max", f"{st.max:.2f}"),
            ("min", f"{st.min:.2f}"),
            ("avg", f"{st.avg:.2f}"),
            ("σ", f"{st.sd:.2f}"),
        )
        col_w = (right - x) / 4
        for i, (label, value) in enumerate(pairs):
            cx = x + col_w * i
            self.create_text(cx, y + 2, text=label, anchor="w", fill=theme.DIM, font=theme.F_TINY)
            self.create_text(
                cx, y + 18, text=value, anchor="w", fill=theme.MUTED, font=theme.F_STAT
            )


class CompactChannelCard(tk.Canvas):
    """ch が多いときに使う小型カード。

    4ch 以上になると大きいカードは横に並ばない。数値と前ショットとの差だけに
    絞り、スパークラインと統計は落とす（それらはグラフとテーブルで見る）。
    """

    WIDTH = 182
    HEIGHT = 72

    def __init__(self, parent: tk.Misc, name: str, color: str, text_color: str) -> None:
        super().__init__(
            parent,
            width=self.WIDTH,
            height=self.HEIGHT,
            background=theme.BG,
            highlightthickness=0,
            bd=0,
        )
        self._name = name
        self._color = color
        self._text_color = text_color
        self._value: float | None = None
        self._delta: float | None = None
        self._redraw()

    def set_data(self, value, delta, stats) -> None:  # noqa: ARG002 - 大型版と同じ呼び口にする
        self._value = value
        self._delta = delta
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        w, h = self.WIDTH, self.HEIGHT
        round_rect(self, 1, 1, w - 1, h - 1, 7, fill=theme.PANEL, outline=theme.PANEL_EDGE)
        self.create_rectangle(1, 9, 4, h - 9, fill=self._color, outline="")

        self.create_rectangle(13, 12, 21, 20, fill=self._color, outline=theme.CHIP_EDGE)
        self.create_text(27, 16, text=self._name, anchor="w", fill=theme.MUTED, font=theme.F_SMALL)

        if self._value is None:
            self.create_text(14, 46, text="--.--", anchor="w", fill=theme.DIM, font=theme.F_LARGE)
            return
        num = self.create_text(
            14,
            46,
            text=f"{self._value:.2f}",
            anchor="w",
            fill=self._text_color,
            font=theme.F_LARGE,
        )
        self.create_text(
            self.bbox(num)[2] + 4, 51, text="MPa", anchor="w", fill=theme.DIM, font=theme.F_TINY
        )
        if self._delta is not None:
            d = self._delta
            if abs(d) < 0.005:
                mark, color = "→", theme.FLAT
            elif d > 0:
                mark, color = "▲", theme.UP
            else:
                mark, color = "▼", theme.DOWN
            self.create_text(
                w - 12,
                16,
                text=f"{mark}{abs(d):.2f}",
                anchor="e",
                fill=color,
                font=theme.F_STAT_S,
            )
