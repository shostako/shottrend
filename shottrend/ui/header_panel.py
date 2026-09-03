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
from shottrend.core.stats import COMPOSITE_LABELS, ChannelStats, composite, window_stats

from . import theme
from .widgets import ChannelCard, CompactChannelCard

#: これを超える ch 数になったら小型カードに切り替える
LARGE_CARD_LIMIT = 3
#: 小型カードを 1 段に並べる枚数
COMPACT_PER_ROW = 5


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

        self.shot_label = ttk.Label(top, text="Shot ----", font=theme.F_BIG)
        self.shot_label.pack(side="left")

        self.time_label = ttk.Label(top, text="", style="MutedBg.TLabel")
        self.time_label.pack(side="left", padx=(12, 0))

        # サイクル・表示件数・使用 ch 数。値そのものより「今どの窓を見ているか」の
        # 文脈なので、目立たせずショット番号の隣に置く
        self.meta_label = ttk.Label(top, text="", style="MutedBg.TLabel")
        self.meta_label.pack(side="left", padx=(24, 0))

        self.session_box = ttk.Combobox(top, state="readonly", width=28, font=theme.F_SMALL)
        self.session_box.pack(side="right")
        self.session_box.bind("<<ComboboxSelected>>", self._session_selected)
        ttk.Label(top, text="表示中のデータ", style="MutedBg.TLabel").pack(
            side="right", padx=(0, 8)
        )

        self._card_area = ttk.Frame(self, style="TFrame")
        self._card_area.pack(fill="x")

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
        specs.append((COMPOSITE_LABELS.get(composite_mode, ""), theme.ACCENT, theme.FG))

        for pos, (name, color, text_color) in enumerate(specs):
            if self._compact:
                card = CompactChannelCard(
                    self._card_area, name, color, text_color, unit=m.unit, digits=m.digits
                )
                card.grid(
                    row=pos // COMPACT_PER_ROW,
                    column=pos % COMPACT_PER_ROW,
                    padx=(0, 8),
                    pady=(0, 6),
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
                f"サイクル {latest.interval:.2f} s    "
                f"表示 {len(shots)} / {total} 件    "
                f"{len(channels)} ch"
            )
        )

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
