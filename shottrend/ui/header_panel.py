"""最新ショットの値と統計を出すヘッダ。

このアプリの存在理由がここに集約されている。純正トレンドビューアは値を
クリックしないと読めないので、常時大きく出す。加えて「前ショットからどう
動いたか」を ▲▼ で見せる（純正にはこれが無い）。

並ぶのは ch ごとのカードと、合成値（最大／最小／平均／差）のカードが 1 枚。
どのカードも、コントロールバーで選んだ項目（ピーク／積分値／…）の値を出す。
合成値の種類もコントロールバーの選択に追従し、テーブルの合成値列と常に同じ
ものを指す。サイクル・表示件数・使用 ch 数はカードにせず、ショット番号の
行に添える。カードにするほどの情報量が無い。

使用中の ch 数でカードの形を変える。MPS08B は 32ch まで計測できるので、
大きいカードを固定で並べる作りにすると破綻する。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from shottrend.core.metrics import metric as metric_of
from shottrend.core.models import Session, Shot
from shottrend.core.stats import ChannelStats, composite, window_stats
from shottrend.i18n import composite_label, t

from . import theme
from .flow import pack_rows
from .widgets import ChannelCard, CompactChannelCard

#: これを超える ch 数になったら小型カードに切り替える
LARGE_CARD_LIMIT = 3
#: 小型カード同士の間隔
COMPACT_GAP = 8


class HeaderPanel(ttk.Frame):
    def __init__(self, parent: tk.Misc, on_session_change) -> None:
        super().__init__(parent, style="TFrame", padding=(14, 10, 14, 4))
        self._on_session_change = on_session_change
        self._sessions: list[Session] = []
        self._suppress = False
        self._channels: list[int] = []
        self._compact = False
        self._cards: list[tk.Canvas] = []
        self._composite_card: tk.Canvas | None = None
        self._composite_mode = ""
        self._metric = ""
        self._grid_columns = 0

        top = ttk.Frame(self, style="TFrame")
        top.pack(fill="x", pady=(0, 8))
        self._top = top
        # セッション選択が上段に入りきらないときの 2 段目。必要なときだけ pack する
        self._top2 = ttk.Frame(self, style="TFrame")
        self._session_on_second_row = False

        self.shot_label = ttk.Label(top, text="Shot ----", font=theme.F_BIG)
        self.shot_label.pack(side="left")

        self.time_label = ttk.Label(top, text="", style="MutedBg.TLabel")
        self.time_label.pack(side="left", padx=(12, 0))

        # サイクル・表示件数・使用 ch 数。値そのものより「今どの窓を見ているか」の
        # 文脈なので、目立たせずショット番号の隣に置く
        self.meta_label = ttk.Label(top, text="", style="MutedBg.TLabel")
        self.meta_label.pack(side="left", padx=(24, 0))

        # セッション選択は「ラベル＋ドロップダウン」で 1 単位。親を self にして
        # おくと `pack(in_=...)` で上段と 2 段目のどちらにも置ける（tk はウィジェット
        # の親を変えられないので、置き場所だけを変える）。ウィンドウを半分に
        # すると上段に収まらず、左のメタ情報とぶつかっていた
        self._session_unit = ttk.Frame(self, style="TFrame")
        self.session_box = ttk.Combobox(
            self._session_unit, state="readonly", width=28, font=theme.F_SMALL
        )
        self.session_box.pack(side="right")
        self.session_box.bind("<<ComboboxSelected>>", self._session_selected)
        ttk.Label(self._session_unit, text=t("header.session"), style="MutedBg.TLabel").pack(
            side="right", padx=(0, 8)
        )
        self._session_unit.pack(in_=top, side="right")
        top.bind("<Configure>", self._on_top_configure)

        self._card_area = ttk.Frame(self, style="TFrame")
        self._card_area.pack(fill="x")
        self._compact_rows: list[list[int]] = []
        self._card_area.bind("<Configure>", self._on_cards_configure)

    # ------------------------------------------------------------- top row

    #: 上段の左側（ショット番号〜メタ情報）とセッション選択の間に最低限残す間隔
    _TOP_GAP = 24

    def _on_top_configure(self, event: tk.Event) -> None:
        if event.widget is self._top and event.width > 1:
            self._reflow_top(event.width)

    def _reflow_top(self, width: int | None = None) -> None:
        """セッション選択を上段に置くか 2 段目に落とすかを、実際の幅で決める。"""
        if width is None:
            width = self._top.winfo_width()
            if width <= 1:
                return
        self.update_idletasks()
        left = (
            self.shot_label.winfo_reqwidth()
            + 12
            + self.time_label.winfo_reqwidth()
            + 24
            + self.meta_label.winfo_reqwidth()
        )
        need = left + self._TOP_GAP + self._session_unit.winfo_reqwidth()
        second = need > width
        if second == self._session_on_second_row:
            return
        self._session_on_second_row = second
        self._session_unit.pack_forget()
        if second:
            self._top2.pack(fill="x", pady=(0, 8), after=self._top)
            self._session_unit.pack(in_=self._top2, side="right")
        else:
            self._top2.pack_forget()
            self._session_unit.pack(in_=self._top, side="right")

    # ---------------------------------------------------------------- channels

    def _rebuild_cards(self, channels: list[int], composite_mode: str, metric_key: str) -> None:
        """ch の顔ぶれ・合成値の種類・項目のどれかが変わったときだけカードを作り直す。"""
        for card in self._cards:
            card.destroy()
        if self._composite_card is not None:
            self._composite_card.destroy()
        self._cards = []
        self._composite_card = None
        self._channels = list(channels)
        self._composite_mode = composite_mode
        self._metric = metric_key
        m = metric_of(metric_key)

        # 前回の列の重みを消す。残すと ch が減ったときに空の列が幅を取り続ける
        for col in range(self._grid_columns):
            self._card_area.columnconfigure(col, weight=0, uniform="")

        self._compact = len(channels) > LARGE_CARD_LIMIT
        specs = [
            (theme.ch_name(ch), theme.ch_color(ch), theme.ch_text_color(ch)) for ch in channels
        ]
        # 合成値のカード。ch の色と混ざらないよう本体のアクセント色を使う。
        # 見出しは種類だけ（「最大」等）。何の値かはコントロールバーの「合成値」
        # グループが示しているので、カード側で繰り返すと幅を食うだけになる
        specs.append((composite_label(composite_mode), theme.ACCENT, theme.FG))

        self._compact_rows = []
        for pos, (name, color, text_color) in enumerate(specs):
            if self._compact:
                # 配置は _place_compact() が幅から決める。固定の 5 列だと 4ch＋合成値
                # で 978px を要求し、ハーフスナップの 960px で右端が切れる
                card = CompactChannelCard(
                    self._card_area, name, color, text_color, unit=m.unit, digits=m.digits
                )
            else:
                # 大型カードは幅を均等に分け合う。固定幅だと最小ウィンドウ幅で
                # 入りきらず、ウィンドウを広げても右に空きができる。
                # padx は全カード同じにする。末尾だけ変えると uniform でも実幅が
                # ずれて、隣同士で見た目が食い違う
                card = ChannelCard(
                    self._card_area, name, color, text_color, unit=m.unit, digits=m.digits
                )
                card.grid(row=0, column=pos, sticky="ew", padx=(0, 10))
                self._card_area.columnconfigure(pos, weight=1, uniform="card")
            if pos < len(channels):
                self._cards.append(card)
            else:
                self._composite_card = card
        self._grid_columns = max(self._grid_columns, len(specs))
        if self._compact:
            self._place_compact()

    def _all_cards(self) -> list[tk.Canvas]:
        cards = list(self._cards)
        if self._composite_card is not None:
            cards.append(self._composite_card)
        return cards

    def _on_cards_configure(self, event: tk.Event) -> None:
        if event.widget is self._card_area and event.width > 1 and self._compact:
            self._place_compact(event.width)

    def _place_compact(self, width: int | None = None) -> None:
        """小型カードを、幅に収まる枚数ずつ段に分けて並べる。"""
        if width is None:
            width = self._card_area.winfo_width()
        cards = self._all_cards()
        # 配置前（幅 1）は 1 段に置いておき、実際の幅が分かった <Configure> で組み直す
        avail = width if width > 1 else 10**9
        rows = pack_rows([c.winfo_reqwidth() for c in cards], COMPACT_GAP, avail)
        if rows == self._compact_rows:
            return
        self._compact_rows = rows
        for c in cards:
            c.grid_forget()
        for r, row in enumerate(rows):
            for col, i in enumerate(row):
                cards[i].grid(row=r, column=col, padx=(0, COMPACT_GAP), pady=(0, 6))
        self._grid_columns = max(self._grid_columns, max(len(row) for row in rows))

    # ------------------------------------------------------------------ update

    def set_data(
        self,
        shots: list[Shot],
        channels: list[int],
        stats: list[ChannelStats],
        composite_mode: str,
        metric_key: str,
        total: int,
    ) -> None:
        """表示中のショット列から、ヘッダの全要素を作り直す。

        stats は channels と同じ並びで、metric_key の値に対する統計。
        """
        if (
            channels != self._channels
            or composite_mode != self._composite_mode
            or metric_key != self._metric
        ):
            self._rebuild_cards(channels, composite_mode, metric_key)

        latest = shots[-1] if shots else None
        prev = shots[-2] if len(shots) >= 2 else None

        if latest is None:
            self.shot_label.config(text="Shot ----")
            self.time_label.config(text="")
            self.meta_label.config(text="")
            for card in self._cards:
                card.set_data(None, None, None)
            if self._composite_card is not None:
                self._composite_card.set_data(None, None, None)
            return

        self.shot_label.config(text=f"Shot {latest.shot_no}")
        self.time_label.config(text=latest.dt.strftime("%Y/%m/%d  %H:%M:%S"))
        self.meta_label.config(
            text=(
                t("header.cycle", value=f"{latest.interval:.2f}")
                + "    "
                + t("header.showing", shown=len(shots), total=total)
                + f"    {len(channels)} ch"
            )
        )
        # メタ情報の長さが変わると上段の収まりも変わる
        self._reflow_top()

        for pos, ch in enumerate(channels):
            value = latest.value(metric_key, ch)
            delta = None if prev is None else value - prev.value(metric_key, ch)
            self._cards[pos].set_data(value, delta, stats[pos])

        if self._composite_card is not None:
            series = [composite(s, composite_mode, channels, metric_key) for s in shots]
            value = series[-1]
            delta = None if prev is None else value - series[-2]
            self._composite_card.set_data(value, delta, window_stats(series))

    # ---------------------------------------------------------------- sessions

    def set_sessions(self, sessions: list[Session], current: Session | None) -> None:
        self._sessions = sessions
        labels = [s.label for s in sessions]
        self._suppress = True
        self.session_box.config(values=labels)
        if current is not None:
            for i, s in enumerate(sessions):
                if s.csv == current.csv:
                    self.session_box.current(i)
                    break
        self._suppress = False

    def _session_selected(self, _event) -> None:
        if self._suppress:
            return
        i = self.session_box.current()
        if 0 <= i < len(self._sessions):
            # 先頭 (= 最新) を選び直したら自動追従に戻す
            self._on_session_change(self._sessions[i], i == 0)
