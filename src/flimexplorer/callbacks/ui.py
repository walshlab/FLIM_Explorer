# flimexplorer/callbacks/ui.py
from __future__ import annotations

from urllib.parse import parse_qs

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc

from flimexplorer.layouts.components import (
    overlay_section_layout,
    outliers_section_layout,
    stats_section_layout,
    export_section_layout,
)


def register(app: Dash) -> None:

    @app.callback(
        Output("col-plot", "style"),
        Output("col-details", "md"),
        Output("btn-toggle-plot", "children"),
        Output("btn-toggle-plot", "color"),
        Input("ui-hide-plot", "data"),
    )
    def apply_plot_visibility(hidden):
        if hidden:
            return {"display": "none"}, 12, "Show plot", "success"  
        return {}, 6, "Hide plot", "warning" 

    @app.callback(
        Output("ui-hide-plot", "data"),
        Input("btn-toggle-plot", "n_clicks"),
        State("ui-hide-plot", "data"),
        prevent_initial_call=True,
    )
    def toggle_plot(_n, hidden):
        return not bool(hidden)

    @app.callback(
        Output("collapse-table-import", "is_open"),
        Input("btn-collapse-table-import", "n_clicks"),
        State("collapse-table-import", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_table_import(n, is_open):
        return (not is_open) if n else is_open

    @app.callback(
        Output("collapse-spc", "is_open"),
        Input("btn-collapse-spc", "n_clicks"),
        State("collapse-spc", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_spc(n, is_open):
        return (not is_open) if n else is_open

    @app.callback(
        Output("collapse-plot-controls", "is_open"),
        Input("btn-collapse-plot-controls", "n_clicks"),
        State("collapse-plot-controls", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_plot_controls(_n, is_open):
        return not bool(is_open)

    @app.callback(
        Output("modules-container", "children"),
        Input("store-paper-mode", "data"),
    )
    def render_modules(paper_mode):
        if paper_mode:
            return dbc.Container(
                fluid=True,
                children=[
                    dbc.Alert(
                        "Paper export mode: all modules shown together for screenshots / PDF export.",
                        color="info",
                        className="mb-3",
                    ),
                    overlay_section_layout(),
                    outliers_section_layout(),
                    stats_section_layout(),
                    export_section_layout(),
                ],
            )
        return dcc.Tabs(
            [
                dcc.Tab(label="Image Overlays", children=[overlay_section_layout()]),
                dcc.Tab(label="Outliers", children=[outliers_section_layout()]),
                dcc.Tab(label="Statistics", children=[stats_section_layout()]),
                dcc.Tab(label="Export", children=[export_section_layout()]),
            ]
        )

    @app.callback(
        Output("store-paper-mode", "data"),
        Input("url", "search"),
    )
    def sync_paper_mode(search):
        if not search:
            return False
        params = parse_qs(search.lstrip("?"))
        return params.get("paper", ["0"])[0] in ("1", "true", "yes")
