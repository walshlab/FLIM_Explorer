# flimexplorer/callbacks/data.py
from __future__ import annotations

from flask import app
import pandas as pd

from dash import Dash, Input, Output, State, no_update
import dash_bootstrap_components as dbc

from flimexplorer.core.io_table import read_df_from_dash_upload, infer_candidates, ensure_outlier_col
from flimexplorer.core.spc_import import AscSuffixConfig, extract_spc_from_excel

from flimexplorer.app_utils import df_to_store, store_to_df 


def register(app: Dash) -> None:

    @app.callback(
        Output("store-df", "data", allow_duplicate=True),
        Output("upload-msg", "children"),
        Input("upload", "contents"),
        State("upload", "filename"),
        prevent_initial_call=True,
    )
    def on_upload(contents, filename):
        try:
            df = read_df_from_dash_upload(contents, filename)
            df = ensure_outlier_col(df)
            return df_to_store(df), f"Loaded: {filename} ({len(df):,} rows × {df.shape[1]} cols)."
        except Exception as e:
            return no_update, f"Failed to load {filename}: {type(e).__name__}: {e}"


    @app.callback(
        Output("spc-upload-msg", "children"),
        Input("spc-upload", "contents"),
        State("spc-upload", "filename"),
        prevent_initial_call=True,
    )
    def spc_upload_feedback(contents, filename):
        if not contents:
            return "No SPC file uploaded."

        if isinstance(contents, list):
            contents = contents[0]

        if not contents or "," not in contents:
            return dbc.Alert(
                "SPC upload failed: malformed upload payload.",
                color="danger",
            )

        try:
            df = read_df_from_dash_upload(contents, filename)
            return dbc.Alert(
                f"SPC input loaded: {filename} ({len(df)} rows × {df.shape[1]} columns). Ready for extraction.",
                color="success",
            )
        except Exception as e:
            return dbc.Alert(f"Failed to read SPC input {filename}: {type(e).__name__}: {e}", color="danger")


    @app.callback(
        Output("store-df", "data"),
        Output("spc-import-msg", "children"),
        Input("btn-spc-extract", "n_clicks"),
        State("spc-upload", "contents"),
        State("spc-upload", "filename"),
        State("nadh-a1-sfx", "value"),
        State("nadh-t1-sfx", "value"),
        State("nadh-t2-sfx", "value"),
        State("nadh-ph-sfx", "value"),
        State("fad-a1-sfx", "value"),
        State("fad-t1-sfx", "value"),
        State("fad-t2-sfx", "value"),
        State("fad-ph-sfx", "value"),
        prevent_initial_call=True,
    )
    def on_spc_extract(
        _n,
        spc_contents,
        spc_filename,
        nadh_a1_sfx, nadh_t1_sfx, nadh_t2_sfx, nadh_ph_sfx,
        fad_a1_sfx, fad_t1_sfx, fad_t2_sfx, fad_ph_sfx,
    ):
        try:
            df_input = read_df_from_dash_upload(spc_contents, spc_filename)

            nadh_cfg = AscSuffixConfig(a1=nadh_a1_sfx, t1=nadh_t1_sfx, t2=nadh_t2_sfx, photons=nadh_ph_sfx)
            fad_cfg  = AscSuffixConfig(a1=fad_a1_sfx,  t1=fad_t1_sfx,  t2=fad_t2_sfx,  photons=fad_ph_sfx)

            df_cells = extract_spc_from_excel(df_input, nadh_cfg=nadh_cfg, fad_cfg=fad_cfg)
            df_cells = ensure_outlier_col(df_cells)

            return df_to_store(df_cells), f"SPC extraction complete: {len(df_cells):,} cells."
        except Exception as e:
            return no_update, f"SPC extraction failed: {type(e).__name__}: {e}"



    @app.callback(
        Output("dd-metric", "options"),
        Output("dd-group", "options"),
        Output("dd-hue", "options"),
        Output("dd-metric", "value"),
        Output("dd-group", "value"),
        Input("store-df", "data"),
        State("dd-metric", "value"),
        State("dd-group", "value"),
    )
    def sync_controls_from_store(store, metric_current, group_current):
        none_opt = [{"label": "— none —", "value": "— none —"}]
        if not store:
           
            return [], [], none_opt, None, None

        df = store_to_df(store)
        metrics, groups = infer_candidates(df)

        metric_opts = [{"label": c, "value": c} for c in metrics]
        group_opts  = [{"label": c, "value": c} for c in groups]
        hue_opts    = none_opt + group_opts

        metric_valid = set(metrics)
        group_valid  = set(groups)

        # ✅ keep current selections if still valid
        metric_val = no_update if metric_current in metric_valid else (metrics[0] if metrics else None)
        group_val  = no_update if group_current in group_valid else (groups[0] if groups else None)

        return metric_opts, group_opts, hue_opts, metric_val, group_val


