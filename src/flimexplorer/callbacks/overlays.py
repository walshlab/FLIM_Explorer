# flimexplorer/callbacks/overlays.py
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import List

from dash import Dash, Input, Output, html, callback_context, no_update

from flimexplorer.core.paths import PathPatterns, resolve_paths_for_row
from flimexplorer.core.overlays import load_gray, load_color, load_mask, render_overlay_png
from flimexplorer.app_utils import store_to_df
import dash_bootstrap_components as dbc

def register(app: Dash) -> None:

    @app.callback(
        Output("overlay-container", "children"),
        Output("overlay-errors", "children"),
        Input("store-df", "data"),
        Input("store-selected", "data"),
        Input("pat-nadh", "value"),
        Input("pat-fad", "value"),
        Input("pat-cnadh", "value"),
        Input("pat-cfad", "value"),
        Input("pat-mask", "value"),
        Input("ov-panels", "value"),
        Input("mask-flip-int", "value"),
        Input("mask-flip-col", "value"),
        Input("ov-show-paths", "value"),
    )
    def update_overlays(
        store,
        selected,
        p_nadh,
        p_fad,
        p_cnadh,
        p_cfad,
        p_mask,
        ov_panels,
        mask_flip_int,
        mask_flip_col,
        ov_show_paths,
        
    ):
        if not store:
            return "No data.", ""
        selected = selected or []
        if not selected:
            return "Select point(s) to preview overlays.", ""

        df = store_to_df(store)
        MAX_ROWS = 12
        if len(selected) > MAX_ROWS:
            selected = selected[:MAX_ROWS]

        ov_panels = set(ov_panels or [])
        flips_int = set(mask_flip_int or [])
        flips_col = set(mask_flip_col or [])

        def _flip_image(img, flips):
            if img is None:
                return None
            out = img
            if "h" in flips:
                out = np.fliplr(out)
            if "v" in flips:
                out = np.flipud(out)
            return out


        all_errors: List[str] = []
        row_blocks = []


        slot_order = [("nadh", "NADH photons"), ("fad", "FAD photons"), ("cnadh", "NADH color"), ("cfad", "FAD color")]

        for idx in selected:
            if idx not in df.index:
                continue

            row = df.loc[idx]

            pat = PathPatterns(
                nadh_photons=p_nadh,
                fad_photons=p_fad,
                color_nadh=p_cnadh,
                color_fad=p_cfad,
                mask=p_mask,
            )
            paths = resolve_paths_for_row(row, pat)

            attempted = paths.get("_attempted", {})
            exists_map = paths.get("_exists", {})

            order = [
                ("nadh",  "NADH photons"),
                ("fad",   "FAD photons"),
                ("cnadh", "NADH color"),
                ("cfad",  "FAD color"),
                ("msk",   "Mask"),
            ]

            lines = []
            for k, label in order:
                p = attempted.get(k)
                ok = exists_map.get(k, False)
                mark = "✓" if ok else "✗"
                lines.append(f"{mark} {label}: {p}")

            # ---- Show stem candidates for debugging ----
            att = attempted.get("cnadh_attempts")
            if att:
                lines.append("")
                lines.append("Tried NADH color paths:")
                for p in att:
                    lines.append(f"  • {p}")

            att = attempted.get("cfad_attempts")
            if att:
                lines.append("")
                lines.append("Tried FAD color paths:")
                for p in att:
                    lines.append(f"  • {p}")
            att = attempted.get("nadh_attempts")
            if att:
                lines.append("")
                lines.append("Tried NADH intensity paths:")
                for p in att:
                    lines.append(f"  • {p}")

            att = attempted.get("fad_attempts")
            if att:
                lines.append("")
                lines.append("Tried FAD intensity paths:")
                for p in att:
                    lines.append(f"  • {p}")



            sanity_block = html.Pre(
                "\n".join(lines),
                className="small",
                style={
                    "whiteSpace": "pre-wrap",
                    "margin": "0 0 8px 0",
                    "padding": "8px",
                    "borderRadius": "6px",
                    "background": "#111",
                    "color": "#ddd",
                },
            )


            msk_raw = load_mask(paths["msk"]) if paths.get("msk") else None

            cell_id = None
            if "mask_id" in row.index and pd.notna(row["mask_id"]):
                try:
                    cell_id = int(row["mask_id"])
                except Exception:
                    cell_id = None

            # build 4 fixed slots; if missing, keep blank placeholder
            slot_children = []
            for key, title_short in slot_order:
                want = (key in ov_panels)
                if not want:
                    # blank (but keeps grid position)
                    slot_children.append(html.Div())
                    continue

                path = paths.get(key)
                if not path:
                    all_errors.append(f"Row {idx}: missing path for {title_short} ({key})")
                    slot_children.append(html.Div())
                    continue

                try:
                    if key in ("nadh", "fad"):
                        img = load_gray(path)
                        img = _flip_image(img, flips_int)
                        title = f"Row {idx} • {title_short}"
                        src = render_overlay_png(img, msk_raw, cell_id, title)
                        slot_children.append(html.Img(src=src, style={"width": "100%"}))
                    else:
                        img = load_color(path)
                        img = _flip_image(img, flips_col)
                        title = f"Row {idx} • {title_short}"
                        src = render_overlay_png(img, msk_raw, cell_id, title)
                        slot_children.append(html.Img(src=src, style={"width": "100%"}))
                except Exception as e:
                    all_errors.append(f"Row {idx}: {title_short} failed: {e}")
                    slot_children.append(html.Div())

            grid = html.Div(
                slot_children,
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "gap": "10px",
                    "alignItems": "start",
                },
            )

            # -------------------------
            # Build card body contents
            # -------------------------
            body_children = []

            expected_keys = ("nadh", "fad", "cnadh", "cfad", "msk")
            missing_any = not all(
                exists_map.get(k, False)
                for k in expected_keys
                if attempted.get(k)  
            )

            if ov_show_paths or missing_any:
                body_children.append(sanity_block)

            body_children.append(grid)

            row_blocks.append(
                dbc.Card(
                    className="mb-3",
                    children=[
                        dbc.CardHeader(f"Selected row {idx}"),
                        dbc.CardBody(body_children),
                    ],
                )
            )

        if not row_blocks:
            return "None of the selected rows exist in the table.", "\n".join(all_errors[:50])

        err_text = "\n".join(all_errors[:50])
        if len(all_errors) > 50:
            err_text += f"\n… (+{len(all_errors) - 50} more)"

        header = html.Div(
            f"Showing overlays for {len(row_blocks)} selected row(s).",
            className="text-muted mb-2",
        )
        return html.Div([header] + row_blocks), err_text
