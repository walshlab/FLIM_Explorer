# flimexplorer/callbacks/stats.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dash import Dash, Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate

from flimexplorer.core.stats_engine import StatsConfig, compute_pairwise_stats
from flimexplorer.core.stats_annotate import annotate_significance
from flimexplorer.app_utils import store_to_df


def register(app: Dash) -> None:

    @app.callback(
        Output("store-stats", "data"),
        Output("stats-summary", "children"),
        Output("stats-table", "rowData"),
        Output("stats-table", "columnDefs"),
        Output("stats-msg", "children"),
        Output("stats-warnings", "children"),
        Input("btn-stats-run", "n_clicks"),
        State("store-df", "data"),
        State("dd-metric", "value"),
        State("dd-group", "value"),
        State("dd-hue", "value"),
        State("stats-scope", "value"),
        State("stats-mode", "value"),
        State("stats-mcomp", "value"),
        State("stats-alpha", "value"),
        State("stats-perm-n", "value"),
        State("stats-perm-seed", "value"),
        State("stats-exclude-outliers", "value"),
        State("stats-table-only-sig", "value"),
        State("stats-annot-only-sig", "value"),
        State("stats-add-ci", "value"),
        State("stats-ci-boot", "value"),
        State("stats-ci-seed", "value"),
        prevent_initial_call=True,
    )
    def run_stats(
        _n,
        store,
        metric,
        group,
        hue,
        scope,
        mode,
        mcomp,
        alpha,
        perm_n,
        perm_seed,
        ex_outliers,
        table_only_sig,
        annot_only_sig,
        add_ci,
        ci_boot,
        ci_seed,
    ):
        if not store or not metric or not group:
            return None, "Load data + select Metric/Group first.", [], [], "Missing inputs.", ""

        df = store_to_df(store)

        cfg = StatsConfig(
            mode=mode,
            alpha=float(alpha or 0.05),
            mcomp=mcomp,
            perm_n=int(perm_n or 5000),
            perm_seed=int(perm_seed or 0),
            exclude_flagged_outliers=("ex" in (ex_outliers or [])),
            show_only_significant_table=("sig" in (table_only_sig or [])),
            annotate_only_significant=("sig" in (annot_only_sig or [])),
            add_effect_ci=("ci" in (add_ci or [])),
            ci_boot_n=int(ci_boot or 1000),
            ci_seed=int(ci_seed or 123),
        )

        hue_col = None if hue in (None, "— none —") else hue

        stats_df, summary = compute_pairwise_stats(
            df=df,
            metric_col=metric,
            group_col=group,
            hue_col=hue_col,
            scope=scope,
            cfg=cfg,
        )

        # -------------------------
        # Keep full stats for annotation
        # -------------------------
        stats_all = stats_df.copy()

        # Columns to show in the table
        show_cols = [
            "group1",
            "group2",
            "n1",
            "n2",
            "test",
            "effect_label",
            "effect",
            "ci_low",
            "ci_high",
            "p",
            "p_adj",
            "stars",
            "warnings",
        ]
        show_cols = [c for c in show_cols if (not stats_all.empty and c in stats_all.columns)]

        # -------------------------
        # Filter ONLY table view (optional)
        # -------------------------
        stats_table = stats_all.copy()
        if cfg.show_only_significant_table and not stats_table.empty and "p_adj" in stats_table.columns:
            p_adj_num = pd.to_numeric(stats_table["p_adj"], errors="coerce")
            stats_table = stats_table[p_adj_num < cfg.alpha].copy()

        row_data = stats_table[show_cols].to_dict("records") if (not stats_table.empty and show_cols) else []

        # -------------------------
        # AG Grid ColumnDefs
        # -------------------------
        width_map = {
            "group1": 220,
            "group2": 220,
            "warnings": 320,
            "effect_label": 140,
            "test": 120,
            "stars": 90,
            "p": 110,
            "p_adj": 110,
            "effect": 120,
            "ci_low": 110,
            "ci_high": 110,
            "n1": 90,
            "n2": 90,
        }

        column_defs = []
        for i, c in enumerate(show_cols):
            col = {
                "headerName": c,
                "field": c,
                "resizable": True,
                "sortable": True,
                "filter": True,
                "minWidth": 80,
                "width": int(width_map.get(c, 120)),
                "wrapText": True if c in ("warnings", "group1", "group2") else False,
                "autoHeight": True if c in ("warnings", "group1", "group2") else False,
            }
            if i == 0:
                col.update(
                    {
                        "checkboxSelection": True,
                        "headerCheckboxSelection": True,
                        "headerCheckboxSelectionFilteredOnly": True,
                    }
                )
            column_defs.append(col)

        # -------------------------
        # Warnings summary (based on ALL comparisons)
        # -------------------------
        warn_text = ""
        if not stats_all.empty and "warnings" in stats_all.columns:
            warn_count = int((stats_all["warnings"].astype(str).str.len() > 0).sum())
            warn_text = f"Warnings present in {warn_count} comparisons." if warn_count else ""

        msg = f"Computed {len(stats_all)} comparisons. Showing {len(stats_table)} in table."

        store_stats = {
            "stats_all": stats_all.to_dict("records") if not stats_all.empty else [],
            "stats_table": stats_table.to_dict("records") if not stats_table.empty else [],
            "cfg": cfg.__dict__,
            "metric": metric,
            "group": group,
            "hue": hue_col,
            "scope": scope,
        }

        return store_stats, summary, row_data, column_defs, msg, warn_text


    @app.callback(
        Output("graph", "figure", allow_duplicate=True),
        Input("btn-annot-selected", "n_clicks"),
        Input("btn-annot-all", "n_clicks"),
        State("graph", "figure"),
        State("store-df", "data"),
        State("store-stats", "data"),
        State("stats-table", "selectedRows"),
        State("stats-enable-annot", "value"),
        State("stats-draw-bars", "value"),
        State("stats-annot-only-sig", "value"),
        State("stats-alpha", "value"),
        State("stats-annot-spacing", "value"),
        prevent_initial_call=True,
    )
    def annotate_from_table_or_all(
        _n_sel,
        _n_all,
        fig_json,
        store,
        stats_store,
        selected_rows,
        enable_annot,
        draw_bars,
        annot_only_sig,
        alpha,
        annot_spacing,  
    ):
        if not stats_store or not fig_json or not store:
            return no_update
        if "annot" not in (enable_annot or []):
            return no_update

        df = store_to_df(store)
        fig = go.Figure(fig_json)

        sdf = pd.DataFrame.from_records(stats_store.get("stats_all", stats_store.get("stats", [])))

        if sdf.empty:
            return fig

        trig = callback_context.triggered_id

        # Filter stats if "Annotate selected"
        if trig == "btn-annot-selected" and selected_rows:
            chosen = pd.DataFrame.from_records(selected_rows)
            if {"group1", "group2"}.issubset(chosen.columns) and {"group1", "group2"}.issubset(sdf.columns):
                key = set(tuple(x) for x in chosen[["group1", "group2"]].astype(str).itertuples(index=False, name=None))
                sdf = sdf[
                    [tuple(x) in key for x in sdf[["group1", "group2"]].astype(str).itertuples(index=False, name=None)]
                ].copy()

        # pos_map from plot meta
        pos_map = {}
        try:
            if isinstance(fig.layout.meta, dict):
                pos_map = fig.layout.meta.get("pos_map", {}) or {}
        except Exception:
            pos_map = {}

        if not pos_map:
            return fig

        metric = stats_store.get("metric")
        y_data = pd.to_numeric(df[metric], errors="coerce").to_numpy() if metric in df.columns else np.array([])

        fig2 = annotate_significance(
            fig=fig,
            stats_df=sdf,
            pos_map=pos_map,
            y_data=y_data,
            draw_bars=("bars" in (draw_bars or [])),
            annotate_only_sig=("sig" in (annot_only_sig or [])),
            alpha=float(alpha or 0.05),
            spacing=float(annot_spacing or 1.0), 
        )
        return fig2
