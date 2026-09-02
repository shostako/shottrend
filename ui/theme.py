"""配色とフォント。

MPS08B 本体アプリ (Mold Marshalling System) の画面から実測した色をベースに
している。本体の隣に並べたときに同じ製品群に見えることを狙う。

本体から採った色:
    ウィンドウ地  #F2F5FF   わずかに青みがかった白
    モード帯      #00FFFF   画面上部の「モニタモード」帯
    強調帯        #FF1493   画面下部の帯
    ボタン地      #E2F5FA   淡いシアン寄りの白
    グラフ地      #000000   波形エリアだけが黒
    テーブル      #FFFFFF   交互行でグループを示す
    CH01 / CH02   #FF0000 / #FFA500  (init.xml の waveColor 先頭 2 色)

本体は明るい地に黒いグラフを置く構成で、全面ダークではない。
"""

from __future__ import annotations

# --- 面 ---
BG = "#F2F5FF"  # ウィンドウ地（本体実測値）
PANEL = "#FFFFFF"  # カード・テーブルの地
PANEL_ALT = "#E9EEF8"  # 交互行・沈めたい面
PANEL_EDGE = "#C9D4E6"  # カードの縁
BORDER = "#B8C4D8"
PLOT_BG = "#000000"  # グラフ地（本体と同じ）

# --- 文字 ---
FG = "#16202E"  # 本文
MUTED = "#5B6779"  # ラベル・補助
DIM = "#8B96A8"  # さらに弱い
ON_PLOT = "#E6E6E6"  # 黒地の上の文字
ON_PLOT_DIM = "#9E9E9E"

# --- アクセント（本体の色彩言語に合わせる） ---
ACCENT = "#00B8D4"  # シアン系。本体の #00FFFF は明るすぎるので少し沈める
ACCENT_BAR = "#00E5FF"  # 状態帯（本体のモード帯に相当）
ACCENT_SOFT = "#E2F5FA"  # ボタン地（本体実測値）
ACCENT_EDGE = "#7FD4E8"

OK = "#00A63C"
WARN = "#E09000"
ERR = "#D32F2F"
ALERT_BAR = "#FF1493"  # 本体下部の帯と同じ

SEL_BG = "#D6ECF7"  # 選択行
SEL_EDGE = "#6FC4DF"
CHIP_EDGE = "#9AA6B8"  # 明るい地で黄やシアンのチップが消えないように縁を付ける

# --- グラフ内（黒地の上） ---
GRID = "#2A2A2A"
GRID_STRONG = "#3C3C3C"
AXIS = "#5A5A5A"
GAP_LINE = "#5A5A5A"

# --- チャンネル ---
#: MPS08B 本体の init.xml にある waveColor と同じ 8 色。
#: 本体はアンプ 1 台 8ch ごとにこの並びを繰り返す（32ch まで）。
WAVE_COLORS = (
    "#FF0000",  # 赤
    "#FFA500",  # 橙
    "#FFFF00",  # 黄
    "#00FF00",  # 緑
    "#32CD32",  # LimeGreen
    "#008000",  # 濃緑
    "#00FFFF",  # シアン
    "#0000FF",  # 青
)
#: 明るい地の上で読める沈めた版。黄・シアン・緑は白地だとほぼ見えない
WAVE_TEXT_COLORS = (
    "#D40000",
    "#C97800",
    "#9A8500",
    "#149014",
    "#2A9E2A",
    "#006800",
    "#0091A6",
    "#1240C8",
)

CH01 = WAVE_COLORS[0]
CH02 = WAVE_COLORS[1]


def ch_name(index: int) -> str:
    """0 始まりのチャンネル番号を CH01 形式にする。"""
    return f"CH{index + 1:02d}"


def ch_color(index: int) -> str:
    """グラフ（黒地）で使う色。8ch ごとに巡回する。"""
    return WAVE_COLORS[index % len(WAVE_COLORS)]


def ch_text_color(index: int) -> str:
    """明るい地の上で使う色。"""
    return WAVE_TEXT_COLORS[index % len(WAVE_TEXT_COLORS)]


UP = "#D32F2F"  # 前ショットより上がった
DOWN = "#1565C0"  # 下がった
FLAT = "#8B96A8"

# --- フォント ---
MONO = "Consolas"
UI = "Yu Gothic UI"

F_HUGE = (MONO, 38, "bold")  # 最新ショットのピーク値
F_LARGE = (MONO, 20, "bold")
F_BIG = (MONO, 15, "bold")
F_TITLE = (UI, 12, "bold")
F_LABEL = (UI, 10)
F_SMALL = (UI, 9)
F_TINY = (UI, 8)
F_STAT = (MONO, 10)
F_STAT_S = (MONO, 9)
F_TABLE = (MONO, 10)


def apply_ttk_theme(style) -> None:
    """ttk を本体アプリ寄りの明るい配色に合わせる。

    clam 以外のテーマは background を素直に受け付けないので必ず clam にする。
    Treeview は background / fieldbackground / foreground の 3 つを揃えないと
    地の色が残る。
    """
    style.theme_use("clam")

    style.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, borderwidth=0)
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("Card.TFrame", background=PANEL, relief="flat")

    style.configure("TLabel", background=BG, foreground=FG, font=F_LABEL)
    style.configure("Panel.TLabel", background=PANEL, foreground=FG, font=F_LABEL)
    style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=F_SMALL)
    style.configure("MutedBg.TLabel", background=BG, foreground=MUTED, font=F_SMALL)
    style.configure("Stat.TLabel", background=PANEL, foreground=MUTED, font=F_STAT_S)

    style.configure(
        "TCheckbutton",
        background=BG,
        foreground=MUTED,
        font=F_SMALL,
        indicatorcolor=PANEL,
        indicatorbackground=PANEL,
        indicatormargin=(0, 0, 6, 0),
        padding=(0, 2),
    )
    style.map(
        "TCheckbutton",
        background=[("active", BG)],
        foreground=[("active", FG)],
        indicatorcolor=[("selected", ACCENT), ("pressed", ACCENT_SOFT)],
    )

    style.configure(
        "TCombobox",
        fieldbackground=PANEL,
        background=ACCENT_SOFT,
        foreground=FG,
        arrowcolor=MUTED,
        selectbackground=SEL_BG,
        selectforeground=FG,
        bordercolor=BORDER,
        lightcolor=PANEL,
        darkcolor=PANEL,
    )
    style.map("TCombobox", fieldbackground=[("readonly", PANEL)])

    style.configure(
        "Treeview",
        background=PANEL,
        fieldbackground=PANEL,
        foreground=FG,
        font=F_TABLE,
        rowheight=21,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=PANEL_ALT,
        foreground=MUTED,
        font=F_SMALL,
        relief="flat",
        borderwidth=0,
        padding=(2, 3),
    )
    style.map(
        "Treeview",
        background=[("selected", SEL_BG)],
        foreground=[("selected", FG)],
    )
    style.map("Treeview.Heading", background=[("active", ACCENT_SOFT)])

    style.configure(
        "Vertical.TScrollbar",
        background=PANEL_ALT,
        troughcolor=BG,
        bordercolor=BG,
        arrowcolor=MUTED,
    )
