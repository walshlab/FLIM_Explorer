# flimexplorer/callbacks/register.py
from __future__ import annotations

from dash import Dash

from flimexplorer.callbacks import data, plot, overlays, stats, outliers, exports, ui


def register_callbacks(app: Dash) -> None:
    data.register(app)
    plot.register(app)
    overlays.register(app)
    stats.register(app)
    outliers.register(app)
    exports.register(app)
    ui.register(app)
