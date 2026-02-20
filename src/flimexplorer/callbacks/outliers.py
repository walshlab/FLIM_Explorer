# flimexplorer/callbacks/outliers.py
from __future__ import annotations

import pandas as pd
from dash import Dash, Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate

from flimexplorer.core.io_table import ensure_outlier_col
from flimexplorer.app_utils import df_to_store, store_to_df


def register(app: Dash) -> None:

    @app.callback(
        Output("store-df", "data", allow_duplicate=True),
        Output("outlier-msg", "children"),
        Input("btn-flag", "n_clicks"),
        Input("btn-unflag", "n_clicks"),
        State("store-df", "data"),
        State("store-selected", "data"),
        prevent_initial_call=True,
    )
    def flag_unflag(btn_flag, btn_unflag, store, selected):
        if not store:
            return no_update, "Load data first."
        selected = selected or []
        if not selected:
            return no_update, "Select points in the plot first."

        df = store_to_df(store)
        df = ensure_outlier_col(df)

        trigger = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
        which = "flag" if trigger == "btn-flag" else "unflag"
        df.loc[selected, "outliers"] = (which == "flag")
        return df_to_store(df), f"Updated {len(selected)} row(s): {which}."



    @app.callback(
        Output("outlier-table", "data"),
        Output("outlier-table", "columns"),
        Output("outlier-list-msg", "children"),
        Input("store-df", "data"),
        State("dd-group", "value"),
        State("dd-hue", "value"),
        State("dd-metric", "value"),
    )
    def update_outlier_table(store, group_col, hue_col, metric_col):
        if not store:
            return [], [], ""
        df = store_to_df(store)
        df = ensure_outlier_col(df)

        flagged = df[df["outliers"] == True].copy()
        if flagged.empty:
            return [], [], "No flagged outliers."

        cols = ["outliers"]
        for c in [group_col, hue_col, metric_col, "Common Name", "mask_id"]:
            if c and c in flagged.columns and c not in cols:
                cols.append(c)

        flagged = flagged.reset_index().rename(columns={"_rowid": "__rowid__"})
        show_cols = ["__rowid__"] + [c for c in cols if c in flagged.columns and c != "outliers"]

        data = flagged[show_cols].to_dict("records")
        columns = [{"name": c, "id": c} for c in show_cols]
        return data, columns, f"Flagged outliers: {len(flagged)}"


    @app.callback(
        Output("store-df", "data", allow_duplicate=True),
        Output("outlier-msg", "children", allow_duplicate=True),
        Output("outlier-table", "selected_rows"),
        Input("btn-unflag-checked", "n_clicks"),
        State("store-df", "data"),
        State("outlier-table", "derived_virtual_data"),
        State("outlier-table", "derived_virtual_selected_rows"),
        prevent_initial_call=True,
    )
    def unflag_checked_outliers(_n, store, virtual_data, selected_rows):
        if not store:
            raise PreventUpdate

        if not virtual_data or not selected_rows:
            return no_update, "Select rows in the flagged outliers table first.", no_update

        chosen = []
        for i in selected_rows:
            if 0 <= i < len(virtual_data):
                r = virtual_data[i]
                if "__rowid__" in r:
                    try:
                        chosen.append(int(r["__rowid__"]))
                    except Exception:
                        pass

        if not chosen:
            return no_update, "No valid 'row' IDs found in selected items.", no_update

        df = store_to_df(store)
        df = ensure_outlier_col(df)

        chosen = [rid for rid in chosen if rid in df.index]
        if not chosen:
            return no_update, "Selected rows not found in current dataframe index.", []

        df.loc[chosen, "outliers"] = False
        return df_to_store(df), f"Unmarked {len(chosen)} flagged outlier(s).", []
