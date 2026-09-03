"""English text.

Terms that name a measured value come from the MPS08B application itself
(PPSB v1.3.0.5, resource keys `VL_N00`–`VL_N08` and `SW_RisingTime` /
`SW_FallingTime`). Using different words for the same number than the
machine's own screen would confuse the shop floor.

The one place the official wording is not copied verbatim is
`SW_RisingTime`, which reads `Risign Time` there — a typo, not a term.

See `ja.py` for what is deliberately left untranslated.
"""

from __future__ import annotations

TEXTS: dict[str, str] = {
    # ---------------------------------------------------------- application
    "app.title": "ShotTrend — MPS08B calculated value trend",
    # ----------------------------------------------------------------- menu
    "menu.file": "File",
    "menu.choose_dir": "Choose MMS_DATA folder",
    "menu.language": "Language",
    "menu.about": "About",
    "menu.quit": "Exit",
    # ---------------------------------------------------------------- about
    "about.subtitle": "MPS08B (Mold Marshalling System) calculated value trend monitor",
    "about.config": "Settings: {path}",
    "about.data": "Data: {path}",
    "about.unset": "(not set)",
    # --------------------------------------------------------------- dialog
    "dialog.choose_dir_title": "Choose the MMS_DATA folder of MPS08B",
    # --------------------------------------------------------------- status
    "status.running": "Monitoring",
    "status.idle": "Stopped",
    "status.nodata": "No data",
    "status.noroot": "Data folder not set",
    "status.error": "Read error",
    # ------------------------------------------------------------- messages
    "msg.no_root": "Data folder not found",
    "msg.read_retry": "Retrying read ({count})",
    "msg.no_data": "No data",
    "msg.skipped": "{rows} rows skipped",
    "msg.hint_choose_dir": "{menu} > {item}",
    # ---------------------------------------------------------- control bar
    "control.metric": "Item",
    "control.window": "Shots",
    "control.kind": "Chart",
    "control.composite": "Combined",
    "control.delta": "Delta",
    # ----------------------------------------------------------- chart kind
    "chart_kind.line": "Line",
    "chart_kind.bar": "Bar",
    # ------------------------------------------------------------ composite
    # `diff` is max − min across the channels of one shot, so `Range` says
    # what it is. `table.spread` is the same number in the table.
    "composite.max": "Max",
    "composite.min": "Min",
    "composite.avg": "Average",
    "composite.diff": "Range",
    # ----------------------------------------------------------- items
    "metric.peak": "Peak",
    "metric.integral": "Integral value",
    "metric.peak_time": "Time to Peak",
    "metric.peak_integral": "Integral to Peak",
    "metric.pointMonitor": "Point Monitor",
    "metric.section_average": "Section Average",
    "metric.section_integral_1": "Section Integral 1",
    "metric.section_integral_2": "Section Integral 2",
    "metric.eject_Monitor": "Eject Monitor",
    # Official spells this `Risign Time`. Kept as the intended word.
    "metric.RisingTime": "Rising Time",
    "metric.FallingTime": "Falling Time",
    # --------------------------------------------------------------- header
    "header.session": "Data shown",
    "header.cycle": "Cycle {value} s",
    "header.showing": "{shown} of {total}",
    # ---------------------------------------------------------------- table
    "table.spread": "Spread",
    # ---------------------------------------------------------------- chart
    "chart.no_data": "No data",
    # Stacked 13px apart in a narrow strip on the plot, and staggered only
    # when two of them come within 46px. Keep it short.
    "chart.missing": "gap {count}",
}
