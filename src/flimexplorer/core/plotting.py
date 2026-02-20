# core/plotting.py
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative


def _resolve_hover_columns(d: pd.DataFrame, metric_col: str) -> list[str]:
    """
    Resolve hover columns using alias groups.
    Returns actual column names present in d, in display order,
    without duplicates.
    """

    # Normalize helper (case + spaces + underscores)
    def _norm(s: str) -> str:
        return s.lower().replace(" ", "").replace("_", "")

    # Canonical name -> list of acceptable aliases
    ALIASES = {
        metric_col: [metric_col],

        "ORR": ["ORR", "orr", "Optical Redox Ratio"],
        "FLIRR": ["FLIRR", "flirr"],

        "NADH_a1": [
            "NADH_a1", "NADH a1", "NADH alpha1", "NADH α1",
            "NADHa1", "NADH_alpha1",
        ],
        "NADH_t1": [
            "NADH_t1", "NADH t1", "NADH tau1", "NADH τ1",
            "NADHt1", "NADH_tau1",
        ],
        "NADH_t2": [
            "NADH_t2", "NADH t2", "NADH tau2", "NADH τ2",
            "NADHt2", "NADH_tau2",
        ],

        "FAD_a1": [
            "FAD_a1", "FAD a1", "FAD alpha1", "FAD α1",
            "FADa1", "FAD_alpha1",
        ],
        "FAD_t1": [
            "FAD_t1", "FAD t1", "FAD tau1", "FAD τ1",
            "FADt1", "FAD_tau1",
        ],
        "FAD_t2": [
            "FAD_t2", "FAD t2", "FAD tau2", "FAD τ2",
            "FADt2", "FAD_tau2",
        ],

        "mask_id": ["mask_id", "mask id", "MaskID", "cell_id", "cell id"],
        "Common Name": ["Common Name", "common name", "Sample", "Condition", "Treatment"],
    }

    # Build normalized lookup of dataframe columns
    norm_cols = {_norm(c): c for c in d.columns}

    resolved: list[str] = []

    for canonical, aliases in ALIASES.items():
        for a in aliases:
            key = _norm(a)
            if key in norm_cols:
                col = norm_cols[key]
                if col not in resolved:
                    resolved.append(col)
                break  # stop after first match per canonical group

    return resolved

def _hex_to_rgba(hex_color: str, a: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"

def _get_palette_colors(palette_name: str | None) -> list[str]:
    """
    palette_name corresponds to attributes on plotly.colors.qualitative.
    Falls back to qualitative.Plotly if missing/invalid.
    """
    if not palette_name or palette_name == "Plotly":
        return list(qualitative.Plotly)

    pal = getattr(qualitative, palette_name, None)
    if pal is None:
        return list(qualitative.Plotly)

    # Some palettes are tuples; normalize to list
    return list(pal)

def make_violin_figure(
    df: pd.DataFrame,
    metric_col: str,
    group_col: str,
    hue_col: str | None,
    show_points: bool,
    hide_outliers: bool,
    palette: str | None = "Plotly",
):
    d = df.copy()

    if hide_outliers and "outliers" in d.columns:
        d = d[d["outliers"] == False]

    fig = go.Figure()
    pos_map: dict[str, float] = {}
    tickvals: list[float] = []
    ticktext: list[str] = []
    x_title = group_col
    
    # ---------------------------------
    # Columns to show on hover (if present)
    # ---------------------------------
    HOVER_CANDIDATES = [
        metric_col,
        "ORR", "FLIRR",
        "NADH_a1", "NADH_t1", "NADH_t2", "NADH alpha1","NADH a1","NADH_alpha1",
        "FAD_a1", "FAD_t1", "FAD_t2",
        "mask_id",
        "Common Name",
    ]
    hover_cols = [c for c in HOVER_CANDIDATES if c in d.columns] # Choose which columns appear on hover (only those that exist)

    colors = _get_palette_colors(palette)  # Get colors from selected palette

    # =========================
    # NO HUE
    # =========================
    if not hue_col or hue_col not in d.columns or hue_col == group_col:
        groups = list(d[group_col].dropna().unique())
        x_base = {g: i for i, g in enumerate(groups)}
        tickvals = [float(x_base[g]) for g in groups] 
        ticktext = [str(g) for g in groups]

        color_map = {g: colors[i % len(colors)] for i, g in enumerate(groups)}

        for g in groups:
            sub = d[d[group_col] == g]
            xpos = x_base[g]
            pos_map[str(g)] = float(xpos)

            c = color_map[g]

            fig.add_trace(go.Violin(
                x=[xpos] * len(sub),
                y=sub[metric_col],
                name=str(g),
                legendgroup=str(g),
                showlegend=False,
                width=0.6,
                hoverinfo="skip",
                line=dict(color=c),
                fillcolor=_hex_to_rgba(c, 0.35),
            ))

            if show_points and not sub.empty:
                sub_cd = sub.copy()
                sub_cd["_rowid"] = sub_cd.index.astype(int)

                # Always keep _rowid first
                cd_cols = ["_rowid"] + hover_cols
                customdata = sub_cd[cd_cols].to_numpy()

                hover_lines = [
                    f"<b>{g}</b>",
                    "row: %{customdata[0]}",
                ]

                # metric value (guaranteed at index 1)
                hover_lines.append(
                    f"{metric_col}: %{{customdata[1]:.4g}}"
                )

                # remaining hover fields
                for j, col in enumerate(cd_cols[2:], start=2):
                    hover_lines.append(f"{col}: %{{customdata[{j}]}}")

                fig.add_trace(go.Scatter(
                    x=[xpos] * len(sub),
                    y=sub[metric_col],
                    mode="markers",
                    legendgroup=str(g),
                    showlegend=False,
                    marker=dict(
                        size=7,
                        line=dict(width=0.5, color="black"),
                        color=c,
                    ),
                    ids=sub_cd["_rowid"].astype(str),
                    customdata=customdata,
                    hovertemplate="<br>".join(hover_lines) + "<extra></extra>",
                ))


    # =========================
    # WITH HUE
    # =========================
    else:
        groups = list(d[group_col].dropna().unique())
        hues = list(d[hue_col].dropna().unique())

        x_base = {g: i for i, g in enumerate(groups)}
        tickvals = [float(x_base[g]) for g in groups]   # centers
        ticktext = [str(g) for g in groups]             

        span = 0.6
        offsets = np.linspace(-span / 2, span / 2, len(hues))
        hue_offset = dict(zip(hues, offsets))

        color_map = {h: colors[i % len(colors)] for i, h in enumerate(hues)}

        for h in hues:
            first = True
            c = color_map[h]
            for g in groups:
                sub = d[(d[group_col] == g) & (d[hue_col] == h)]
                if sub.empty:
                    continue

                xpos = x_base[g] + hue_offset[h]
                pos_map[f"{g} | {h}"] = float(xpos)

                fig.add_trace(go.Violin(
                    x=[xpos] * len(sub),
                    y=sub[metric_col],
                    name=str(h),
                    legendgroup=str(h),
                    showlegend=first,
                    width=0.10,
                    hoverinfo="skip",
                    line=dict(color=c),
                    fillcolor=_hex_to_rgba(c, 0.35),
                ))
                first = False

                if show_points and not sub.empty:
                    sub_cd = sub.copy()
                    sub_cd["_rowid"] = sub_cd.index.astype(int)

                    cd_cols = ["_rowid"] + hover_cols
                    customdata = sub_cd[cd_cols].to_numpy()

                    hover_lines = [
                        f"<b>{g}</b>",
                        f"{hue_col}: {h}",
                        "row: %{customdata[0]}",
                        f"{metric_col}: %{{customdata[1]:.4g}}",
                    ]

                    for j, col in enumerate(cd_cols[2:], start=2):
                        hover_lines.append(f"{col}: %{{customdata[{j}]}}")

                    fig.add_trace(go.Scatter(
                        x=[xpos] * len(sub),
                        y=sub[metric_col],
                        mode="markers",
                        legendgroup=str(h),
                        showlegend=False,
                        marker=dict(
                            size=7,
                            line=dict(width=0.5, color="black"),
                            color=c,
                        ),
                        ids=sub_cd["_rowid"].astype(str),
                        customdata=customdata,
                        hovertemplate="<br>".join(hover_lines) + "<extra></extra>",
                    ))


    fig.update_layout(
        height=480,
        margin=dict(l=40, r=10, t=40, b=40),
        yaxis_title=metric_col,
        dragmode="zoom",
        clickmode="event+select",
        uirevision="keep",
        meta={"pos_map": pos_map},
    )

    fig.update_xaxes(
        type="linear",
        tickmode="array",
        tickvals=tickvals,
        ticktext=ticktext,
        title=x_title,
    )

    return fig
