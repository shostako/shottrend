"""配色とフォント。

CH01=赤 / CH02=オレンジ は MPS08B 本体の init.xml にある waveColor の先頭 2 色
(255,0,0) と (255,165,0) に合わせてある。本体の波形画面と並べたときに
同じセンサが同じ色で見えることを優先した。
"""

from __future__ import annotations

# --- 色 ---
BG = "#101010"  # ウィンドウ地
PANEL = "#181818"  # パネル地
PLOT_BG = "#000000"  # グラフ地（本体アプリの波形画面と同じ黒）
BORDER = "#2E2E2E"

FG = "#E6E6E6"  # 本文（純白は目が疲れる）
MUTED = "#9E9E9E"  # 補助テキスト・軸ラベル
DIM = "#6E6E6E"

GRID = "#2A2A2A"
AXIS = "#555555"
GAP_LINE = "#4A4A4A"  # 計測中断の区切り線

CH01 = "#FF0000"
CH02 = "#FFA500"
CH_COLORS = (CH01, CH02)
CH_NAMES = ("CH01", "CH02")

OK = "#4CAF50"
WARN = "#FFC107"
ERR = "#F44336"

SEL_BG = "#2A3A4A"

# --- フォント ---
# 数値は等幅にしないと桁が揺れて読みにくい
MONO = "Consolas"
UI = "Yu Gothic UI"

F_HUGE = (MONO, 40, "bold")  # 最新ショットのピーク値
F_BIG = (MONO, 15, "bold")
F_LABEL = (UI, 11)
F_SMALL = (UI, 9)
F_STAT = (MONO, 10)
F_TABLE = (MONO, 10)
F_TITLE = (UI, 12, "bold")


def apply_ttk_theme(style) -> None:
    """ttk を暗色に寄せる。

    clam 以外のテーマは background を素直に受け付けないので必ず clam にする。
    Treeview は background / fieldbackground / foreground の 3 つを揃えないと
    白地が残る。
    """
    style.theme_use("clam")

    style.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, borderwidth=0)
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("TLabel", background=BG, foreground=FG, font=F_LABEL)
    style.configure("Panel.TLabel", background=PANEL, foreground=FG, font=F_LABEL)
    style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=F_SMALL)
    style.configure("Stat.TLabel", background=PANEL, foreground=MUTED, font=F_STAT)

    style.configure(
        "TButton", background=PANEL, foreground=FG, font=F_LABEL, padding=(10, 4), borderwidth=1
    )
    style.map(
        "TButton",
        background=[("active", "#2A2A2A"), ("pressed", "#333333")],
        foreground=[("disabled", DIM)],
    )
    style.configure("Toggle.TButton", background=PANEL, foreground=MUTED)
    style.configure("ToggleOn.TButton", background=SEL_BG, foreground=FG)

    style.configure(
        "TCombobox",
        fieldbackground=PANEL,
        background=PANEL,
        foreground=FG,
        arrowcolor=MUTED,
        selectbackground=SEL_BG,
        selectforeground=FG,
    )
    style.map("TCombobox", fieldbackground=[("readonly", PANEL)])

    style.configure(
        "Treeview",
        background=PLOT_BG,
        fieldbackground=PLOT_BG,
        foreground=FG,
        font=F_TABLE,
        rowheight=20,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=PANEL,
        foreground=MUTED,
        font=F_SMALL,
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "Treeview",
        background=[("selected", SEL_BG)],
        foreground=[("selected", FG)],
    )
    style.map("Treeview.Heading", background=[("active", "#242424")])
