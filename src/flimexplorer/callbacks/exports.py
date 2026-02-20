# flimexplorer/callbacks/exports.py
from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dash import Dash, Input, Output, State, dcc, ctx, no_update

from flimexplorer.core.io_table import ensure_outlier_col
from flimexplorer.core.paths import PathPatterns, resolve_paths_for_row
from flimexplorer.core.overlays import load_gray, load_mask, render_overlay_png
from flimexplorer.app_utils import store_to_df


def register(app: Dash) -> None:

    @app.callback(
        Output("download-stats-xlsx", "data"),
        Output("export-stats-msg", "children"),
        Input("btn-export-stats", "n_clicks"),
        State("store-stats", "data"),
        prevent_initial_call=True,
    )
    def export_stats(_n, stats_store):
        if not stats_store or not isinstance(stats_store, dict):
            return no_update, "No stats available. Run “Compute stats” first."

        stats_all = stats_store.get("stats_all", [])
        stats_table = stats_store.get("stats_table", [])
        cfg = stats_store.get("cfg", {})

        if not stats_all:
            return no_update, "Stats are empty. Run “Compute stats” first."

        # -------------------------
        # Main stats tables
        # -------------------------
        df_all = pd.DataFrame.from_records(stats_all)
        df_table = pd.DataFrame.from_records(stats_table) if stats_table else pd.DataFrame()

        # -------------------------
        # Analysis metadata / labels
        # -------------------------
        analysis_info = {
            "metric (dependent variable)": stats_store.get("metric"),
            "group (independent variable)": stats_store.get("group"),
            "hue (secondary independent)": stats_store.get("hue") or "— none —",
            "comparison scope": stats_store.get("scope"),
            "alpha": cfg.get("alpha"),
            "test mode": cfg.get("mode"),
            "multiple comparison correction": cfg.get("mcomp"),
            "exclude flagged outliers": cfg.get("exclude_flagged_outliers"),
            "annotate only significant": cfg.get("annotate_only_significant"),
            "export timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        df_info = pd.DataFrame(
            {"parameter": analysis_info.keys(), "value": analysis_info.values()}
        )

        # -------------------------
        # Write Excel
        # -------------------------
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as xl:
            df_info.to_excel(xl, index=False, sheet_name="analysis_info")
            df_all.to_excel(xl, index=False, sheet_name="stats_all")

            if not df_table.empty:
                df_table.to_excel(xl, index=False, sheet_name="stats_table")

        bio.seek(0)


        metric = stats_store.get("metric", "metric")
        group = stats_store.get("group", "group")
        filename = f"stats_{metric}_by_{group}.xlsx".replace(" ", "_")

        return dcc.send_bytes(bio.getvalue(), filename), f"Exported {len(df_all)} comparisons."


    @app.callback(
        Output("download-outliers-xlsx", "data"),
        Output("export-msg", "children"),
        Input("btn-export-outliers", "n_clicks"),
        State("store-df", "data"),
        prevent_initial_call=True,
    )
    def export_outliers(_n, store):
        if not store:
            return no_update, "No data loaded."

        df = store_to_df(store)
        df = ensure_outlier_col(df)

        out = df[df["outliers"] == True].copy()
        if out.empty:
            return no_update, "No flagged outliers to export."

        out = out.reset_index().rename(columns={"_rowid": "__rowid__"})

        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as xl:
            out.to_excel(xl, index=False, sheet_name="flagged_outliers")
        bio.seek(0)

        filename = "flagged_outliers.xlsx"
        return dcc.send_bytes(bio.getvalue(), filename), f"Exported {len(out)} flagged outlier rows."


    @app.callback(
        Output("download-full-df-xlsx", "data"),
        Output("export-full-msg", "children"),
        Input("btn-export-full-df", "n_clicks"),
        State("store-df", "data"),
        prevent_initial_call=True,
    )
    def export_full_df(_n, store):
        if not store:
            return no_update, "No data loaded."

        df = store_to_df(store)
        df = ensure_outlier_col(df)

        out = df.reset_index().rename(columns={"_rowid": "__rowid__"})

        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as xl:
            out.to_excel(xl, index=False, sheet_name="full_table")
        bio.seek(0)

        return dcc.send_bytes(bio.getvalue(), "full_dataframe_with_outliers.xlsx"), f"Exported {len(out)} rows."

    @app.callback(
        Output("download-outlier-overlays-zip", "data"),
        Output("export-overlays-msg", "children"),
        Input("btn-export-outlier-overlays", "n_clicks"),
        State("store-df", "data"),
        State("pat-nadh", "value"),
        State("pat-fad", "value"),
        State("pat-cnadh", "value"),
        State("pat-cfad", "value"),
        State("pat-mask", "value"),
        prevent_initial_call=True,
    )
    def export_outlier_overlay_pngs(_n, store, p_nadh, p_fad, p_cnadh, p_cfad, p_mask):
        if not store:
            return no_update, "No data loaded."

        df = store_to_df(store)
        df = ensure_outlier_col(df)

        flagged = df[df["outliers"] == True].copy()
        if flagged.empty:
            return no_update, "No flagged outliers."

        pat = PathPatterns(
            nadh_photons=p_nadh,
            fad_photons=p_fad,
            color_nadh=p_cnadh,
            color_fad=p_cfad,
            mask=p_mask,
        )

        zip_buf = io.BytesIO()
        written = 0
        missing = 0

        with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rid, row in flagged.iterrows():
                try:
                    paths = resolve_paths_for_row(row, pat)

                    # We export NADH photons overlay (with outlines)
                    nadh_path = paths.get("nadh")
                    msk_path = paths.get("msk")
                    if not nadh_path or not msk_path:
                        missing += 1
                        continue

                    img = load_gray(nadh_path)
                    msk_raw = load_mask(msk_path)

                    cell_id = None
                    if "mask_id" in row.index and pd.notna(row["mask_id"]):
                        try:
                            cell_id = int(row["mask_id"])
                        except Exception:
                            cell_id = None

                    title = f"Outlier row {rid}"
                    data_uri = render_overlay_png(img, msk_raw, cell_id, title)

                    # data_uri looks like: "data:image/png;base64,...."
                    if not (isinstance(data_uri, str) and "base64," in data_uri):
                        missing += 1
                        continue
                    b64 = data_uri.split("base64,", 1)[1]
                    png_bytes = base64.b64decode(b64)

                    # Original filename -> use the photons path basename
                    base = Path(str(nadh_path)).name  # includes extension
                    # Convert to stem and append suffix
                    out_name = f"{Path(base).stem}_outlier_overlay.png"

                    # Avoid collisions
                    if out_name in zf.namelist():
                        out_name = f"{Path(base).stem}_row{rid}_outlier_overlay.png"

                    zf.writestr(out_name, png_bytes)
                    written += 1

                except Exception:
                    missing += 1
                    continue

        zip_buf.seek(0)
        msg = f"Exported {written} overlay PNG(s)."
        if missing:
            msg += f" Skipped {missing} (missing files or errors)."

        return dcc.send_bytes(zip_buf.getvalue(), "outlier_overlays.zip"), msg


    @app.callback(
        Output("download-spc-xlsx", "data"),
        Input("btn-spc-download", "n_clicks"),
        State("store-df", "data"),
        prevent_initial_call=True,
    )
    def download_spc_results(_n, store): 
        if not store:
            return no_update

        df = store_to_df(store).reset_index().rename(columns={"_rowid": "__rowid__"})

        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as xl:
            df.to_excel(xl, index=False, sheet_name="per_cell")
        bio.seek(0)

        return dcc.send_bytes(bio.getvalue(), "spc_per_cell_results.xlsx")


    @app.callback(
        Output("download-spc-template-xlsx", "data"),
        Input("btn-spc-template", "n_clicks"),
        prevent_initial_call=True,
    )
    def download_spc_template(_n):
        """
        Generates an example SPC import template as an Excel file.
        """
    
        template = pd.DataFrame(
            [
                {
                    "NADH_folder": r"C:\\path\\to\\nadh_folder",                 
                    "nadh_stem": r"Sample_001_NADH FLIM1.asc",              
                    "fad_folder": r"C:\\path\\to\\nadh_folder",         
                    "fad_stem": r"Sample_001_FAD FLIM1.asc",          
                    "mask_path": r"C:\\path\\to\\mask.png",          
                    "Categorical Independent Variable": r"Time 1, Concentration 1, Replicate 1",                                 
                }
            ]
        )

        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as xl:
            template.to_excel(xl, index=False, sheet_name="spc_template")
        bio.seek(0)

        return dcc.send_bytes(bio.getvalue(), "spc_import_template.xlsx")


    @app.callback(
        Output("download-plot", "data"),
        Output("export-plot-msg", "children"),
        Input("btn-export-plot-svg", "n_clicks"),
        Input("btn-export-plot-pdf", "n_clicks"),
        Input("btn-export-plot-png", "n_clicks"),
        State("store-fig", "data"),
        State("dd-metric", "value"),
        State("dd-group", "value"),
        State("dd-hue", "value"),
        prevent_initial_call=True,
    )
    def export_plot(_svg, _pdf, _png, fig_json, metric, group, hue):
        if not fig_json:
            return no_update, "No plot available to export yet."

        trig = ctx.triggered_id
        ext = "png"
        if trig == "btn-export-plot-svg":
            ext = "svg"
        elif trig == "btn-export-plot-pdf":
            ext = "pdf"

        fig = go.Figure(fig_json)

        label = f"{metric or 'metric'}__x={group or 'group'}__hue={hue or 'none'}"
        safe = "".join(ch if ch.isalnum() or ch in "._-=" else "_" for ch in label)
        filename = f"flimexplorer_plot__{safe}.{ext}"

        bio = io.BytesIO()
        if ext == "png":
         
            fig.write_image(bio, format="png", scale=4)
        else:
            fig.write_image(bio, format=ext)
        bio.seek(0)

        return dcc.send_bytes(bio.getvalue(), filename), f"Exported {filename}"

