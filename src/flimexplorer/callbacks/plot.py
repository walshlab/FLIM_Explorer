# flimexplorer/callbacks/plot.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dash import Dash, Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate

from flimexplorer.core.plotting import make_violin_figure
from flimexplorer.core.stats_annotate import annotate_significance

from flimexplorer.app_utils import store_to_df


def register(app: Dash) -> None:

    @app.callback(
        Output("graph", "figure"),
        Output("store-fig", "data"),
        Input("store-df", "data"),
        Input("dd-metric", "value"),
        Input("dd-group", "value"),
        Input("dd-hue", "value"),
        Input("dd-palette", "value"),
        Input("sw-showpoints", "value"),
        Input("sw-hide-outliers", "value"),
        Input("plot-font-family", "value"),
        Input("plot-font-size", "value"),
        Input("axis-y-label", "value"),
        Input("axis-x-label", "value"),
        Input("store-stats", "data"),
        Input("stats-enable-annot", "value"),
        Input("stats-draw-bars", "value"),
        Input("stats-annot-only-sig", "value"),
        Input("stats-alpha", "value"),
        Input("stats-annot-spacing", "value"),
    )
    def update_plot(
        store, metric, group, hue, palette,
        showpoints, hide_outliers,
        font_family, font_size,
        y_label, x_label,
        stats_store, enable_annot, draw_bars, annot_only_sig, alpha,
        annot_spacing,   
    ):
        if not store or not metric or not group:
            return go.Figure(), None

        df = store_to_df(store)

        fig = make_violin_figure(
            df=df,
            metric_col=metric,
            group_col=group,
            hue_col=(None if hue in (None, "— none —") else hue),
            show_points=bool(showpoints),
            hide_outliers=bool(hide_outliers),
            palette=palette,
        )

        font_family = font_family or "system-ui"
        font_size = int(font_size or 12)

        fig.update_layout(
            font=dict(family=font_family, size=font_size),
            legend=dict(font=dict(family=font_family, size=font_size)),
            margin=dict(l=40, r=20, t=40, b=40),
        )

        y_title = (y_label or "").strip() or metric
        x_title = (x_label or "").strip() or group
        fig.update_yaxes(title_text=y_title)
        fig.update_xaxes(title_text=x_title)

        # -------------------------
        # Auto-annotate from stats
        # -------------------------
        want_annot = ("annot" in (enable_annot or [])) if enable_annot is not None else False

        if want_annot and stats_store and isinstance(stats_store, dict):
            sdf = pd.DataFrame.from_records(stats_store.get("stats_all", stats_store.get("stats", [])))


            hue_col = (None if hue in (None, "— none —") else hue)
            if (
                stats_store.get("metric") == metric
                and stats_store.get("group") == group
                and stats_store.get("hue") == hue_col
                and not sdf.empty
            ):
                pos_map = {}
                try:
                    if isinstance(fig.layout.meta, dict):
                        pos_map = fig.layout.meta.get("pos_map", {}) or {}
                except Exception:
                    pos_map = {}

                y_data = pd.to_numeric(df[metric], errors="coerce").to_numpy() if metric in df.columns else np.array([])

                if pos_map:
                    fig = annotate_significance(
                        fig=fig,
                        stats_df=sdf,
                        pos_map=pos_map,
                        y_data=y_data,
                        draw_bars=("bars" in (draw_bars or [])),
                        annotate_only_sig=("sig" in (annot_only_sig or [])),
                        alpha=float(alpha or 0.05),
                        spacing=float(annot_spacing or 1.0),  
                    )

        return fig, fig.to_dict()


    @app.callback(
        Output("store-selected", "data"),
        Input("graph", "selectedData"),
        Input("graph", "clickData"),
        State("store-selected", "data"),
    )
    def update_selected(selectedData, clickData, current):
        '''
        Update the list of selected row IDs based on plot interactions.
        - If the user selects points (e.g., box/lasso select), update to those points.
        - If the user clicks a single point, update to that point.
        - If the selection is cleared (e.g., clicking on empty space), keep the current selection unchanged.
        '''
        current = current or []

        def _get_rowid(point):
           
            pid = point.get("id", None)
            if pid is not None:
                try:
                    return int(pid)
                except Exception:
                    pass

            # Fallback: your customdata[0] = _rowid
            cd = point.get("customdata", None)
            if cd is None:
                return None
            if isinstance(cd, (int, np.integer)):
                return int(cd)
            if isinstance(cd, (list, tuple)) and len(cd) > 0:
                try:
                    return int(cd[0])
                except Exception:
                    try:
                        return int(float(cd[0]))
                    except Exception:
                        return None
            return None

        # Only handle the input that actually triggered this callback
        trig = (callback_context.triggered[0]["prop_id"] if callback_context.triggered else "")
        # trig looks like "graph.selectedData" or "graph.clickData"

        if trig.endswith("selectedData"):
            if selectedData and selectedData.get("points"):
                ids = []
                for p in selectedData["points"]:
                    rid = _get_rowid(p)
                    if rid is not None:
                        ids.append(rid)
                ids = sorted(set(ids))
                return ids if ids else current
            return current

        if trig.endswith("clickData"):
            if clickData and clickData.get("points"):
                rid = _get_rowid(clickData["points"][0])
                return [rid] if rid is not None else current
            return current

        return current


    @app.callback(
        Output("table", "data"),
        Output("table", "columns"),
        Input("store-df", "data"),
        Input("store-selected", "data"),
    )
    def update_table(store, selected):
    # This callback updates the data table to show only the selected rows, and limits the number of columns for readability.

        if not store:
            return [], []
        df = store_to_df(store)
        selected = selected or []
        if not selected:
            return [], []

        shown = df.loc[selected].copy()
        cols = list(shown.columns)
        cols = cols[:35] if len(cols) > 35 else cols

        shown = shown.reset_index().rename(columns={"_rowid": "__rowid__"})
        data = shown[["__rowid__"] + cols].to_dict("records")
        columns = [{"name": c, "id": c} for c in (["__rowid__"] + cols)]
        return data, columns


    # axis default / autofill / insertion helpers
    @app.callback(Output("axis-y-label", "value"), Input("dd-metric", "value"), prevent_initial_call=True)
    def set_default_y_label(metric):
        return metric or ""

    @app.callback(Output("axis-x-label", "value"), Input("dd-group", "value"), prevent_initial_call=True)
    def set_default_x_label(group):
        return group or ""

    @app.callback(
        Output("axis-y-label", "value", allow_duplicate=True),
        Input("dd-metric", "value"),
        State("axis-y-label", "value"),
        prevent_initial_call=True,
    )
    def autofill_y_label(metric, current):
        current = (current or "").strip()
        if current:            # user already typed something
            return no_update
        return metric or ""    # fill default if user hasn't typed anything

    @app.callback(
        Output("axis-x-label", "value", allow_duplicate=True),
        Input("dd-group", "value"),
        State("axis-x-label", "value"),
        prevent_initial_call=True,
    )
    def autofill_x_label(group, current):
        current = (current or "").strip()
        if current:
            return no_update
        return group or ""

    @app.callback(
        Output("axis-active", "data"),
        Input("axis-x-label", "value"),
        Input("axis-y-label", "value"),
        prevent_initial_call=True,
    )
    def set_active_axis(_x, _y):
        tid = callback_context.triggered_id
        if tid == "axis-x-label":
            return "x"
        if tid == "axis-y-label":
            return "y"
        raise PreventUpdate

    @app.callback(
        Output("axis-y-label", "value", allow_duplicate=True),
        Output("axis-x-label", "value", allow_duplicate=True),
        Output("axis-insert", "value"),
        Input("axis-insert", "value"),
        State("axis-insert-target", "value"),
        State("axis-active", "data"),
        State("axis-y-label", "value"),
        State("axis-x-label", "value"),
        prevent_initial_call=True,
    )
    def insert_axis_token(token, target_choice, active_axis, y_val, x_val):
        if not token:
            raise PreventUpdate

        y_val = y_val or ""
        x_val = x_val or ""

        # Prefer explicit dropdown choice; fall back to last clicked field
        target = target_choice or active_axis or "y"

        if target == "x":
            x_val = x_val + token
        else:
            y_val = y_val + token

        # Clear selection after insert
        return y_val, x_val, None

    @app.callback(
        Output("store-stats", "data", allow_duplicate=True),
        Input("dd-metric", "value"),
        Input("dd-group", "value"),
        Input("dd-hue", "value"),
        Input("sw-hide-outliers", "value"),
        prevent_initial_call=True,
    )
    def clear_stats_on_plot_change(_metric, _group, _hue, _hide_outliers):
        return None
