# core/stats_annotate.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

def _parse_combo(lbl: str):
    if isinstance(lbl, str) and " | " in lbl:
        a,b = lbl.split(" | ", 1)
        return a.strip(), b.strip()
    return str(lbl).strip(), None

def _extract_pos_map(fig: go.Figure) -> dict[str, float]:
 
    pos = {}
    for tr in fig.data:
 
        if not hasattr(tr, "x") or tr.x is None:
            continue
        xs = np.asarray(tr.x, dtype=float)
        if xs.size == 0:
            continue
        x0 = float(xs[0])
  
        name = getattr(tr, "name", None)

    meta = getattr(fig.layout, "meta", None)
    if isinstance(meta, dict) and "pos_map" in meta and isinstance(meta["pos_map"], dict):
        return {str(k): float(v) for k,v in meta["pos_map"].items() if v is not None}
    return pos

def annotate_significance(
    fig: go.Figure,
    stats_df: pd.DataFrame,
    pos_map: dict[str, float],
    y_data: np.ndarray,
    draw_bars: bool = True,
    annotate_only_sig: bool = True,
    alpha: float = 0.05,
    headroom: float = 0.22,
    step: float = 0.05,
    cap: float = 0.06,
    inset: float = 0.08,
    global_shift: float = 0.0,
    spacing: float = 1.0,
) -> go.Figure:


    # --- helper to clear old annotations ---
    def _clear():
        fig.layout.shapes = ()
        fig.data = tuple([tr for tr in fig.data if getattr(tr, "meta", None) != "sigstars"])

    if stats_df is None or stats_df.empty:
        _clear()
        return fig

    # spacing guard
    spacing = float(spacing or 1.0)
    spacing = max(0.25, min(spacing, 5.0))

    # Clear old stars/shapes
    _clear()

    # y stats
    y = np.asarray(y_data, float)
    y = y[np.isfinite(y)]
    y_min = float(np.min(y)) if y.size else 0.0
    y_max = float(np.max(y)) if y.size else 1.0
    delta = max(1e-12, y_max - y_min)

    # Effective vertical geometry
    headroom_eff = headroom * spacing
    step_eff = step * spacing
    cap_eff = cap * spacing

  
    step_eff = max(step_eff, 0.03)   
    cap_eff  = max(cap_eff,  0.05)

    cap_h = cap_eff * delta
    step_h = step_eff * delta

 
    inset_eff = float(inset) * (0.85 + 0.25 * spacing)  
    inset_eff = max(0.0, min(inset_eff, 0.45))  

    # Extend y-range
    fig.update_yaxes(range=[y_min, y_max + headroom_eff * delta])

    # Build x lookup
    def x_of(lbl: str) -> float:
        if lbl in pos_map:
            return float(pos_map[lbl])
        a, _b = _parse_combo(lbl)
        if a in pos_map:
            return float(pos_map[a])
        return np.nan

    sdf = stats_df.copy()

    # Filter to significant only if requested
    p_adj = pd.to_numeric(sdf.get("p_adj", np.nan), errors="coerce")
    if annotate_only_sig:
        sdf = sdf[p_adj < float(alpha)].copy()
        p_adj = pd.to_numeric(sdf.get("p_adj", np.nan), errors="coerce")

    if sdf.empty:
        _clear()
        return fig

    # --- speed knobs ---
    MAX_STRICT_STACK = 120  # tune
    strict_stack = len(sdf) <= MAX_STRICT_STACK

    # Compute x1/x2 fast (no apply)
    g1 = sdf["group1"].astype(str).to_numpy()
    g2 = sdf["group2"].astype(str).to_numpy()
    x1 = np.array([x_of(v) for v in g1], dtype=float)
    x2 = np.array([x_of(v) for v in g2], dtype=float)

    ok = np.isfinite(x1) & np.isfinite(x2)
    if not np.any(ok):
        return fig

    sdf = sdf.loc[ok].copy()
    x1 = x1[ok]
    x2 = x2[ok]

    xL = np.minimum(x1, x2)
    xR = np.maximum(x1, x2)
    span = np.abs(x2 - x1)

    sdf["_x1"] = x1
    sdf["_x2"] = x2
    sdf["_xL"] = xL
    sdf["_xR"] = xR
    sdf["_span"] = span
    sdf["_p_adj_num"] = pd.to_numeric(sdf.get("p_adj", np.nan), errors="coerce")

    # Place widest spans first (stable)
    sdf = sdf.sort_values(["_span", "_p_adj_num"], ascending=[False, True], kind="mergesort")

    placed = []  # list of (xL, xR, yTop)
    def overlap(aL, aR, bL, bR):
        return (aL < bR) and (bL < aR)

    star_x, star_y, star_t, star_cd = [], [], [], []

    base_y0 = y_max + 0.03 * delta + global_shift * delta

    for _, r in sdf.iterrows():
        xL = float(r["_xL"])
        xR = float(r["_xR"])
        x1 = float(r["_x1"])
        x2 = float(r["_x2"])

        # Default placement
        y0 = base_y0
        y_top = y0 + cap_h

        if strict_stack:
            
            overlaps = [pTop for (pL, pR, pTop) in placed if overlap(xL, xR, pL, pR)]
            if overlaps:
                y0 = max(overlaps) + step_h
                y_top = y0 + cap_h
        else:
            # fast mode
            y0 = base_y0 + step_h * len(placed)
            y_top = y0 + cap_h

        placed.append((xL, xR, y_top))

        g1s = str(r.get("group1", ""))
        g2s = str(r.get("group2", ""))

        star_x.append(0.5 * (x1 + x2))
        star_y.append(y_top)
        star_t.append(r.get("stars", ""))
        star_cd.append([
            g1s, g2s,
            r.get("test", ""),
            r.get("effect", np.nan),
            r.get("p", np.nan),
            r.get("p_adj", np.nan),
            r.get("n1", np.nan),
            r.get("n2", np.nan),
        ])

        if draw_bars:
            xL_in = xL + inset_eff
            xR_in = xR - inset_eff
            y_high = y0 + cap_h
            path = (
                f"M {xL} {y0} "
                f"L {xL} {y_high} "
                f"L {xL_in} {y_high} "
                f"L {xR_in} {y_high} "
                f"L {xR} {y_high} "
                f"L {xR} {y0}"
            )
            fig.add_shape(
                type="path",
                path=path,
                xref="x",
                yref="y",
                line=dict(color="black", width=1.6),
                layer="above",
            )

    if star_x:
        fig.add_trace(go.Scatter(
            x=star_x, y=star_y,
            mode="text",
            text=star_t,
            textposition="top center",
            hovertemplate=(
                "<b>%{customdata[0]}</b> ↔ <b>%{customdata[1]}</b><br>"
                "test: %{customdata[2]}<br>"
                "effect: %{customdata[3]:.4g}<br>"
                "p: %{customdata[4]:.3g}<br>"
                "p_adj: %{customdata[5]:.3g}<br>"
                "n1: %{customdata[6]} &nbsp; n2: %{customdata[7]}<extra></extra>"
            ),
            customdata=np.asarray(star_cd, dtype=object),
            showlegend=False,
            meta="sigstars",
            name="sig-stars",
        ))

    sdf.drop(columns=["_x1", "_x2", "_xL", "_xR", "_span", "_p_adj_num"], inplace=True, errors="ignore")
    return fig
