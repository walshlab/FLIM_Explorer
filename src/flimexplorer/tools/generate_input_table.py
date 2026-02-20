# dash_io_table_generator_aggrid.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import pandas as pd

from dash import Dash, dcc, html, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from dataclasses import field


# ============================================================
# Pairing helpers
# ============================================================
def _common_prefix(a: str, b: str) -> str:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return a[:i]


def _common_suffix(a: str, b: str) -> str:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[-(i + 1)] == b[-(i + 1)]:
        i += 1
    return a[len(a) - i :] if i > 0 else ""

def _filter_by_required_suffix(files: List[Path], required_suffix: str) -> List[Path]:
    s = (required_suffix or "").strip()
    if not s:
        return files
    return [p for p in files if p.name.endswith(s)]

def derive_base_stem(filename: str, required_suffix: str) -> str:
    """
    Remove the required suffix and normalize the base stem
    so it does NOT end with separators like '_', '-', or space.
    """
    name = filename

    if required_suffix and name.endswith(required_suffix):
        name = name[: -len(required_suffix)]

    # remove extension if still present
    if name.lower().endswith(".asc"):
        name = name[:-4]

    # normalize trailing separators
    return name.rstrip("_- ")

def infer_tokens_from_examples(nadh_ex: str, fad_ex: str) -> Tuple[str, str, str, str]:
    """
    Returns prefix, suffix, nadh_token, fad_token such that:
      nadh_ex == prefix + nadh_token + suffix
      fad_ex  == prefix + fad_token  + suffix
    """
    prefix = _common_prefix(nadh_ex, fad_ex)
    suffix = _common_suffix(nadh_ex, fad_ex)
    if nadh_ex == fad_ex:
        return prefix, suffix, "", ""
    n_mid = nadh_ex[len(prefix) : len(nadh_ex) - len(suffix) if len(suffix) else len(nadh_ex)]
    f_mid = fad_ex[len(prefix) : len(fad_ex) - len(suffix) if len(suffix) else len(fad_ex)]
    return prefix, suffix, n_mid, f_mid


def list_files(folder: Path, ext: str = ".asc", recursive: bool = False) -> List[Path]:
    if recursive:
        return sorted([p for p in folder.rglob(f"*{ext}") if p.is_file()])
    return sorted([p for p in folder.glob(f"*{ext}") if p.is_file()])


def parse_folder_value(folder_name: str, rule: str) -> str:
    """
    rule:
      - "full": use folder_name as-is
      - "underscore_suffix": take substring after first underscore (if present), else full
    """
    if rule == "underscore_suffix":
        if "_" in folder_name:
            return folder_name.split("_", 1)[1].strip()
    return folder_name.strip()


# ============================================================
# Core builder
# ============================================================
@dataclass
class IOTableConfig:
    # FLIM folders
    same_flim_folder: bool
    nadh_folder: Path
    fad_folder: Path

    # Masks
    mask_folder: Path
    mask_suffix: str
    mask_example_name: str
    masks_mirror_structure: bool = False

    # Pairing rule
    same_file_stem: bool = True
    nadh_example_name: Optional[str] = None
    fad_example_name: Optional[str] = None

    # Categoricals
    categorical_vars: List[str] = field(default_factory=list)  # additional categoricals (manual fill)
    cat_from_folders: bool = False
    folder_depth: int = 0  # 0/1/2
    folder_level1_var: str = "Time"
    folder_level2_var: str = "Treatment"
    folder_parse_rule: str = "full"  # "full" or "underscore_suffix"

    nadh_required_suffix: str = ""
    fad_required_suffix: str = ""


def _filter_by_token(files: List[Path], token: str) -> List[Path]:
    """Keep only files whose filename contains token (if token is non-empty)."""
    if not token:
        return files
    return [p for p in files if token in p.name]


def build_io_table(cfg: IOTableConfig, asc_ext: str = ".asc") -> pd.DataFrame:
    cfg.categorical_vars = cfg.categorical_vars or []

    folder_cats: List[str] = []
    if cfg.cat_from_folders:
        if cfg.folder_depth >= 1:
            folder_cats.append(cfg.folder_level1_var.strip() or "Level1")
        if cfg.folder_depth >= 2:
            folder_cats.append(cfg.folder_level2_var.strip() or "Level2")

    all_cat_cols = []
    seen = set()
    for c in folder_cats + cfg.categorical_vars:
        c = c.strip()
        if c and c not in seen:
            all_cat_cols.append(c)
            seen.add(c)

    recursive_for_files = bool((cfg.cat_from_folders and cfg.folder_depth > 0) or cfg.masks_mirror_structure)

    # --- list NADH candidates (may include FAD if same folder!) ---
    nadh_candidates = list_files(cfg.nadh_folder, ext=asc_ext, recursive=recursive_for_files)
    nadh_candidates = _filter_by_required_suffix(nadh_candidates, cfg.nadh_required_suffix)

    if not nadh_candidates:
        raise FileNotFoundError(
            f"No NADH files matched suffix '{cfg.nadh_required_suffix}' under: {cfg.nadh_folder}"
        )
    def _set_folder_cats(row: dict, rel_parent: Path):
        if cfg.cat_from_folders and cfg.folder_depth > 0:
            parts = list(rel_parent.parts)
            if cfg.folder_depth >= 1 and len(parts) >= 1:
                row[f"cat__{folder_cats[0]}"] = parse_folder_value(parts[0], cfg.folder_parse_rule)
            if cfg.folder_depth >= 2 and len(parts) >= 2:
                row[f"cat__{folder_cats[1]}"] = parse_folder_value(parts[1], cfg.folder_parse_rule)

    # ----------------------------
    # Template mode (no auto-pair)
    # ----------------------------
    if not cfg.same_file_stem:
        rows = []
        for nf in nadh_candidates:
            rel_parent = nf.parent.relative_to(cfg.nadh_folder) if recursive_for_files else Path(".")
            mask_dir = (cfg.mask_folder / rel_parent) if (cfg.masks_mirror_structure and recursive_for_files) else cfg.mask_folder

            base_stem = derive_base_stem(nf.name, cfg.nadh_required_suffix)
            mask_path = mask_dir / f"{base_stem}{cfg.mask_suffix}"

            row = {
                "NADH_folder": str(nf.parent) if recursive_for_files else str(cfg.nadh_folder),
                "nadh_stem": nf.name,
                "FAD_folder": str(cfg.fad_folder),
                "fad_stem": "",
                "mask_path": str(mask_path),
            }
            _set_folder_cats(row, rel_parent)

            for cat in cfg.categorical_vars:
                cat = cat.strip()
                if cat:
                    row[f"cat__{cat}"] = row.get(f"cat__{cat}", "")
            rows.append(row)

        return pd.DataFrame(rows)

    # ----------------------------
    # Auto pairing mode
    # ----------------------------
    if not cfg.nadh_example_name or not cfg.fad_example_name:
        raise ValueError("Auto-pairing requires both NADH and FAD example filenames.")

    _, _, nadh_token, fad_token = infer_tokens_from_examples(cfg.nadh_example_name, cfg.fad_example_name)
    if not nadh_token and not fad_token:
        raise ValueError("Could not infer NADH vs FAD token from examples (examples look identical).")

    # If NADH+FAD are in same folder, candidates include both → filter!
    nadh_files = _filter_by_token(nadh_candidates, nadh_token)

    # list FAD candidates
    fad_candidates = list_files(cfg.fad_folder, ext=asc_ext, recursive=recursive_for_files)
    fad_candidates = _filter_by_required_suffix(fad_candidates, cfg.fad_required_suffix)

    fad_files = _filter_by_token(fad_candidates, fad_token)

    if not nadh_files:
        raise FileNotFoundError(
            f"Found {len(nadh_candidates)} *{asc_ext} files, but none matched NADH token '{nadh_token}'. "
            "Check your example NADH filename."
        )
    if not fad_files:
        raise FileNotFoundError(
            f"Found {len(fad_candidates)} *{asc_ext} files, but none matched FAD token '{fad_token}'. "
            "Check your example FAD filename."
        )

    # Map by (relative parent folder, filename) so pairing works in subfolders
    fad_by_key: Dict[Tuple[str, str], Path] = {}
    for fp in fad_files:
        rel_parent = fp.parent.relative_to(cfg.fad_folder) if recursive_for_files else Path(".")
        fad_by_key[(str(rel_parent), fp.name)] = fp

    rows = []
    missing_fad = []

    for nf in nadh_files:
        # expected FAD filename by swapping token
        expected_fad_name = nf.name.replace(nadh_token, fad_token) if (nadh_token in nf.name) else nf.name

        rel_parent = nf.parent.relative_to(cfg.nadh_folder) if recursive_for_files else Path(".")
        fad_path = fad_by_key.get((str(rel_parent), expected_fad_name))
        fad_stem = fad_path.name if fad_path else ""
        fad_folder_for_row = str(fad_path.parent) if (fad_path and recursive_for_files) else str(cfg.fad_folder)

        if not fad_path:
            missing_fad.append((str(rel_parent), nf.name, expected_fad_name))

        mask_dir = (cfg.mask_folder / rel_parent) if (cfg.masks_mirror_structure and recursive_for_files) else cfg.mask_folder

        # mask base: remove NADH token and strip extension
        base_stem = derive_base_stem(
            nf.name,
            cfg.nadh_required_suffix,
        )
        mask_name = f"{base_stem}{cfg.mask_suffix}"
        mask_path = mask_dir / mask_name

        row = {
            "NADH_folder": str(nf.parent) if recursive_for_files else str(cfg.nadh_folder),
            "nadh_stem": nf.name,                 # <-- stays NADH now
            "FAD_folder": fad_folder_for_row if recursive_for_files else str(cfg.fad_folder),
            "fad_stem": fad_stem,
            "mask_path": str(mask_path),
        }
        _set_folder_cats(row, rel_parent)

        for cat in cfg.categorical_vars:
            cat = cat.strip()
            if cat:
                row[f"cat__{cat}"] = row.get(f"cat__{cat}", "")

        rows.append(row)

    df = pd.DataFrame(rows)

    if missing_fad:
        warn_lines = ["WARNING: Some FAD files were not found in the matched relative folder; fad_stem left blank.", ""]
        for rel, nadh_name, expected in missing_fad[:25]:
            warn_lines.append(f"[{rel}] NADH: {nadh_name}  | expected FAD: {expected}")
        if len(missing_fad) > 25:
            warn_lines.append(f"... plus {len(missing_fad) - 25} more")
        warn_text = "\n".join(warn_lines)

        df_warn = pd.DataFrame([{
            "NADH_folder": warn_text,
            "nadh_stem": "",
            "FAD_folder": "",
            "fad_stem": "",
            "mask_path": "",
        }])
        df = pd.concat([df_warn, df], ignore_index=True)

    return df

# ============================================================
# Dash app
# ============================================================

def L(label: str) -> html.Div:
    return html.Div(label, className="mb-1", style={"fontWeight": 600})


def df_to_aggrid_payload(df: pd.DataFrame) -> dict:
    col_defs = [
        {
            "headerName": c,
            "field": c,
            "filter": True,
            "sortable": True,
            "resizable": True,
            "wrapText": True,
            "autoHeight": True,
        }
        for c in df.columns
    ]
    return {"columns": col_defs, "rows": df.to_dict("records")}
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "IO Table Generator FLIM pairing"
server = app.server  # optional for gunicorn, do NOT overwrite app

app.layout = dbc.Container(
    fluid=True,
    className="py-3",
    children=[
        #dcc.Store(id="store-df-payload"),  # holds {"columns":[...], "rows":[...]}
        dcc.Store(id="store-df-raw"),
        dcc.Store(id="store-df-final"),
        #dcc.Store(id="store-cat-maps", data={}),
        dcc.Store(id="store-meta", data={}),  # holds {"lvl1_col": "...", "lvl2_col": "...", "has_lvl2": True/False}

        dbc.Row([
            dbc.Col([
                html.H3("FLIM IO-table Excel Generator (Dash AG Grid viewer)"),
                html.Div(
                    "Build the IO table, inspect it in an interactive grid (filter/sort), then download Excel.",
                    className="text-muted mb-3"
                ),
            ], width=12)
        ]),

        # --- Controls (same as before, condensed for brevity) ---
        dbc.Row([
            dbc.Col([
                dbc.Card(className="shadow-sm", children=[
                    dbc.CardHeader("Folders"),
                    dbc.CardBody([
                        dbc.Switch(id="sw-same-folder", label="NADH and FAD share the same base folder", value=True, className="mb-2"),
                        L("FLIM base folder (if same)"),
                        dbc.Input(id="in-flim-folder", placeholder=r"C:\path\to\flim_base", type="text"),
                        html.Div(className="my-2"),
                        dbc.Row([
                            dbc.Col([L("NADH base folder (if different)"), dbc.Input(id="in-nadh-folder", placeholder=r"C:\path\to\nadh_base", type="text")], md=6),
                            dbc.Col([L("FAD base folder (if different)"), dbc.Input(id="in-fad-folder", placeholder=r"C:\path\to\fad_base", type="text")], md=6),
                        ], className="g-2"),
                        html.Hr(),
                        L("Mask base folder"),
                        dbc.Input(id="in-mask-folder", placeholder=r"C:\path\to\mask_base", type="text"),
                        html.Div(className="my-2"),
                        dbc.Row([
                            dbc.Col([L("Mask suffix"), dbc.Input(id="in-mask-suffix", type="text", value="_cp_masks.png")], md=4),
                            dbc.Col([L("Example mask file"), dbc.Input(id="in-mask-example", type="text", placeholder="Sample_001_cp_masks.png")], md=8),
                        ], className="g-2"),
                        html.Div(className="my-2"),
                        dbc.Switch(id="sw-mask-mirror", label="Masks mirror folder structure", value=False),
                    ]),
                ])
            ], md=6),

            dbc.Col([
                dbc.Card(className="shadow-sm", children=[
                    dbc.CardHeader("Pairing + Categoricals"),
                    

                    
                    dbc.CardBody([
                        L("Only include files that end with these suffixes (recommended)"),
                        dbc.Row([
                            dbc.Col([
                                L("NADH filename suffix"),
                                dbc.Input(id="in-nadh-suffix", type="text", value="NADH FLIM1.asc",
                                        placeholder="e.g., NADH FLIM1.asc"),
                            ], md=6),
                            dbc.Col([
                                L("FAD filename suffix"),
                                dbc.Input(id="in-fad-suffix", type="text", value="FAD FLIM2.asc",
                                        placeholder="e.g., FAD FLIM2.asc"),
                            ], md=6),
                        ], className="g-2"),
                        dbc.Switch(id="sw-same-stem", label="Auto-pair NADH ↔ FAD from naming token", value=True, className="mb-2"),
                        dbc.Row([
                            dbc.Col([L("Example NADH filename"), dbc.Input(id="in-nadh-example", type="text", placeholder="Sample_001_NADH FLIM1.asc")], md=6),
                            dbc.Col([L("Example FAD filename"), dbc.Input(id="in-fad-example", type="text", placeholder="Sample_001_FAD FLIM2.asc")], md=6),
                        ], className="g-2"),
                        html.Div(id="pairing-hint", className="mt-2 text-muted"),
                        html.Hr(),
                        dbc.Switch(id="sw-cat-folders", label="Auto-fill categoricals from folder/subfolder structure", value=True, className="mb-2"),
                        dbc.Row([
                            dbc.Col([
                                L("Folder depth"),
                                dcc.Dropdown(
                                    id="dd-folder-depth",
                                    options=[
                                        {"label": "0 (none)", "value": 0},
                                        {"label": "1 level", "value": 1},
                                        {"label": "2 levels", "value": 2},
                                    ],
                                    value=2,
                                    clearable=False,
                                ),
                            ], md=6),
                            dbc.Col([
                                L("Folder parse rule"),
                                dcc.Dropdown(
                                    id="dd-folder-parse",
                                    options=[
                                        {"label": "Use full folder name", "value": "full"},
                                        {"label": "Use suffix after first '_' (folder1_1hr → 1hr)", "value": "underscore_suffix"},
                                    ],
                                    value="underscore_suffix",
                                    clearable=False,
                                ),
                            ], md=6),
                        ], className="g-2"),
                        html.Div(className="my-2"),
                        dbc.Row([
                            dbc.Col([L("Level 1 variable name"), dbc.Input(id="in-level1-var", type="text", value="Time")], md=6),
                            dbc.Col([L("Level 2 variable name"), dbc.Input(id="in-level2-var", type="text", value="Treatment")], md=6),
                        ], className="g-2"),
                        html.Hr(),
                        L("Additional categorical columns (comma-separated)"),
                        dbc.Input(id="in-cat-names", type="text", placeholder="Dose, Batch", value=""),

                        # Build table button    
                        html.Hr(),

                        dbc.Row([
                            dbc.Col(
                                dbc.Button(
                                    "Build table",
                                    id="btn-build",
                                    color="primary",
                                    className="w-100",
                                    n_clicks=0,
                                ),
                                width=12,
                            ),
                        ]),

                        html.Div(
                            "Build the IO table using the settings above. You can customize categorical labels after building.",
                            className="text-muted small mt-1",
                        ),


                    ]),
                ])
            ], md=6),
        ], className="g-3"),

        # --- Category mapping editor ---
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Button(
                            "Customize categorical labels",
                            id="btn-toggle-mapping",
                            color="secondary",
                            outline=True,
                            className="mb-2",
                            n_clicks=0,
                        ),

                        dbc.Collapse(
                            id="collapse-cat-mapping",
                            is_open=False,
                            children=dbc.Card(
                                className="shadow-sm",
                                children=[
                                    dbc.CardHeader("Customize categorical labels (optional)"),
                                    dbc.CardBody(
                                        [
                                            html.Div(
                                                className="text-muted small mb-2",
                                                children="Edit labels for folder-derived categorical values (Level 1 and Level 2). "
                                                        "Applies to the main table + Excel download."
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dbc.Button(
                                                            "Apply mappings",
                                                            id="btn-apply-maps",
                                                            color="primary",
                                                            n_clicks=0,
                                                        ),
                                                        md="auto",
                                                    ),
                                                    dbc.Col(
                                                        html.Div(id="map-status", className="small"),
                                                        md=True,
                                                    ),
                                                ],
                                                className="g-2 mb-2",
                                            ),

                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Div("Level 1 mapping", style={"fontWeight": 600}),
                                                            dag.AgGrid(
                                                                id="grid-map-l1",
                                                                columnDefs=[
                                                                    {"headerName": "value (parsed)", "field": "value", "editable": False},
                                                                    {"headerName": "label (edit)", "field": "label", "editable": True},
                                                                ],
                                                                rowData=[],
                                                                defaultColDef={
                                                                    "resizable": True,
                                                                    "filter": True,
                                                                    "sortable": True,
                                                                    "flex": 1,
                                                                    "minWidth": 160,
                                                                },
                                                                dashGridOptions={"pagination": True, "paginationPageSize": 15},
                                                                className="ag-theme-alpine-dark",
                                                                style={"height": "330px", "width": "100%"},
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),

                                                    dbc.Col(
                                                        [
                                                            html.Div("Level 2 mapping", style={"fontWeight": 600}),
                                                            dag.AgGrid(
                                                                id="grid-map-l2",
                                                                columnDefs=[
                                                                    {"headerName": "value (parsed)", "field": "value", "editable": False},
                                                                    {"headerName": "label (edit)", "field": "label", "editable": True},
                                                                ],
                                                                rowData=[],
                                                                defaultColDef={
                                                                    "resizable": True,
                                                                    "filter": True,
                                                                    "sortable": True,
                                                                    "flex": 1,
                                                                    "minWidth": 160,
                                                                },
                                                                dashGridOptions={"pagination": True, "paginationPageSize": 15},
                                                                className="ag-theme-alpine-dark",
                                                                style={"height": "330px", "width": "100%"},
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                ],
                                                className="g-2",
                                            ),
                                        ]
                                    ),
                                ],
                            ),
                        ),
                    ],
                    width=12,
                ),
            ],
            className="g-3 mt-2",
        ),

       
        # --- Build + Download ---
        dbc.Row([
            dbc.Col([
                dbc.Card(className="shadow-sm", children=[
                    dbc.CardHeader("Generate"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([L("Output filename"), dbc.Input(id="in-out-name", type="text", value="io_table.xlsx")], md=5),
                            dbc.Col([L("ASC extension"), dbc.Input(id="in-asc-ext", type="text", value=".asc")], md=3),
                            
                            dbc.Col([
                                html.Div(style={"height": 10}),
                                dbc.Button("Download Excel", id="btn-download", color="success", className="mt-3", n_clicks=0),
                            ], md=2),
                        ], className="g-2"),
                        html.Hr(),
                        html.Div(id="status", className="small"),
                        dcc.Download(id="dl-xlsx"),
                    ]),
                ])
            ], width=12),
        ], className="g-3 mt-2"),

 
        # --- Data summary ---
        dbc.Row([
            dbc.Col([
                dbc.Card(className="shadow-sm", children=[
                    dbc.CardHeader("Data summary"),
                    dbc.CardBody(
                        id="data-summary",
                        children=html.Div("Build the table to see a summary.", className="text-muted")
                    ),
                ])
            ], width=12),
        ], className="g-3 mt-2"),

        # --- AG Grid Viewer ---
        dbc.Row([
            dbc.Col([
                dbc.Card(className="shadow-sm", children=[
                    dbc.CardHeader("DataFrame Viewer"),
                    dbc.CardBody([
                        dag.AgGrid(
                            id="grid",
                            columnDefs=[],
                            rowData=[],
                            defaultColDef={
                                "filter": True,
                                "sortable": True,
                                "resizable": True,
                                "minWidth": 140,
                                "flex": 1,
                            },
                            dashGridOptions={
                                "pagination": True,
                                "paginationPageSize": 25,
                                "animateRows": False,
                                "rowSelection": "multiple",
                                "suppressFieldDotNotation": True,
                            },
                            style={"height": "600px", "width": "100%"},
                            className="ag-theme-alpine-dark",  # works nicely with cyborg
                        ),
                        html.Div(className="text-muted mt-2 small",
                                 children="Tip: use column filter menus to quickly subset rows, then download Excel."),
                    ]),
                ])
            ], width=12),
        ], className="g-3 mt-2"),
    ]
)


# ----------------------------
# UI toggles
# ----------------------------
@app.callback(
    Output("in-flim-folder", "disabled"),
    Output("in-nadh-folder", "disabled"),
    Output("in-fad-folder", "disabled"),
    Input("sw-same-folder", "value"),
)
def toggle_folder_inputs(same_folder: bool):
    if same_folder:
        return False, True, True
    return True, False, False


@app.callback(
    Output("in-nadh-example", "disabled"),
    Output("in-fad-example", "disabled"),
    Output("pairing-hint", "children"),
    Input("sw-same-stem", "value"),
)
def toggle_example_inputs(auto_pair: bool):
    if auto_pair:
        return False, False, "Provide example NADH/FAD filenames so the app can infer the channel token and auto-pair."
    return True, True, "Auto-pairing is OFF: fad_stem will be blank and you’ll fill it manually."


# ----------------------------
# Build: create df + update grid + store
# ----------------------------


@app.callback(
    Output("store-df-raw", "data"),
    Output("store-df-final", "data"),
    Output("store-meta", "data"),
    Output("status", "children"),
    Output("map-status", "children"),
    Input("btn-build", "n_clicks"),
    Input("btn-apply-maps", "n_clicks"),
    State("store-df-raw", "data"),
    State("store-meta", "data"),
    State("grid-map-l1", "rowData"),
    State("grid-map-l2", "rowData"),
    # ---- all the build States ----
    State("sw-same-folder", "value"),
    State("in-flim-folder", "value"),
    State("in-nadh-folder", "value"),
    State("in-fad-folder", "value"),
    State("in-mask-folder", "value"),
    State("in-mask-suffix", "value"),
    State("in-mask-example", "value"),
    State("sw-mask-mirror", "value"),
    State("sw-same-stem", "value"),
    State("in-nadh-example", "value"),
    State("in-fad-example", "value"),
    State("sw-cat-folders", "value"),
    State("dd-folder-depth", "value"),
    State("in-level1-var", "value"),
    State("in-level2-var", "value"),
    State("dd-folder-parse", "value"),
    State("in-cat-names", "value"),
    State("in-asc-ext", "value"),
    State("in-nadh-suffix", "value"),
    State("in-fad-suffix", "value"),

    prevent_initial_call=True,
)
def build_or_apply(
    n_build,
    n_apply,
    raw_records,
    meta,
    map_l1_rows,
    map_l2_rows,
    same_folder,
    flim_folder,
    nadh_folder,
    fad_folder,
    mask_folder,
    mask_suffix,
    mask_example,
    masks_mirror,
    same_stem,
    nadh_example,
    fad_example,
    cat_from_folders,
    folder_depth,
    level1_var,
    level2_var,
    folder_parse_rule,
    cat_names,
    asc_ext,
    nadh_required_suffix, 
    fad_required_suffix,
):
    triggered = ctx.triggered_id  # "btn-build" or "btn-apply-maps"

    # -----------------------
    # APPLY MAPPINGS branch
    # -----------------------
    if triggered == "btn-apply-maps":
        if not raw_records or not meta:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                dbc.Alert("Build the table first.", color="warning"),
            )

        df = pd.DataFrame(raw_records)

        def to_map(rows):
            m = {}
            for r in (rows or []):
                old = r.get("value")
                new = r.get("label")
                if old is None:
                    continue
                m[str(old)] = str(new) if new is not None else ""
            return m

        lvl1_col = (meta or {}).get("lvl1_col")
        lvl2_col = (meta or {}).get("lvl2_col")

        if lvl1_col and lvl1_col in df.columns:
            m1 = to_map(map_l1_rows)
            df[lvl1_col] = df[lvl1_col].astype(str).map(lambda x: m1.get(x, x))

        if lvl2_col and lvl2_col in df.columns:
            m2 = to_map(map_l2_rows)
            df[lvl2_col] = df[lvl2_col].astype(str).map(lambda x: m2.get(x, x))

        # raw/meta unchanged; final updated
        return (
            no_update,                 # store-df-raw
            df.to_dict("records"),     # store-df-final
            no_update,                 # store-meta
            dbc.Alert("Mappings applied.", color="success"),  # status
            "",                        # map-status (or put info here instead)
        )

    # -----------------------
    # BUILD branch
    # -----------------------
    try:
        if same_folder:
            if not flim_folder:
                raise ValueError("Please provide the FLIM base folder path.")
            base = Path(str(flim_folder).strip().strip('"'))
            nadh_p = base
            fad_p = base
        else:
            if not nadh_folder or not fad_folder:
                raise ValueError("Please provide both NADH base folder and FAD base folder paths.")
            nadh_p = Path(str(nadh_folder).strip().strip('"'))
            fad_p = Path(str(fad_folder).strip().strip('"'))

        if not mask_folder:
            raise ValueError("Please provide the mask base folder path.")
        mask_p = Path(str(mask_folder).strip().strip('"'))

        manual_cats = []
        if cat_names:
            manual_cats = [c.strip() for c in str(cat_names).split(",") if c.strip()]

        asc_ext = (asc_ext or ".asc").strip()
        if not asc_ext.startswith("."):
            asc_ext = "." + asc_ext

        cfg = IOTableConfig(
            same_flim_folder=bool(same_folder),
            nadh_folder=nadh_p,
            fad_folder=fad_p,
            mask_folder=mask_p,
            mask_suffix=(mask_suffix or "").strip(),
            mask_example_name=(mask_example or "").strip(),
            masks_mirror_structure=bool(masks_mirror),
            same_file_stem=bool(same_stem),
            nadh_example_name=(nadh_example or "").strip() if same_stem else None,
            fad_example_name=(fad_example or "").strip() if same_stem else None,
            categorical_vars=manual_cats,
            cat_from_folders=bool(cat_from_folders),
            folder_depth=int(folder_depth or 0),
            folder_level1_var=(level1_var or "Level1"),
            folder_level2_var=(level2_var or "Level2"),
            folder_parse_rule=folder_parse_rule or "full",
            nadh_required_suffix=(nadh_required_suffix or "").strip(),
            fad_required_suffix=(fad_required_suffix or "").strip(),
        )

        df = build_io_table(cfg, asc_ext=asc_ext)
        raw_records_new = df.to_dict("records")

        lvl1_col = None
        lvl2_col = None
        if cfg.cat_from_folders and cfg.folder_depth >= 1:
            lvl1_col = f"cat__{(cfg.folder_level1_var.strip() or 'Level1')}"
        if cfg.cat_from_folders and cfg.folder_depth >= 2:
            lvl2_col = f"cat__{(cfg.folder_level2_var.strip() or 'Level2')}"

        meta_new = {"lvl1_col": lvl1_col, "lvl2_col": lvl2_col, "has_lvl2": bool(lvl2_col)}

        return (
            raw_records_new,   # store-df-raw
            raw_records_new,   # store-df-final
            meta_new,          # store-meta
            dbc.Alert(f"Built table with {len(df)} rows and {len(df.columns)} columns.", color="success"),
            "",                # map-status cleared
        )

    except Exception as e:
        return (
            no_update,
            no_update,
            no_update,
            dbc.Alert(str(e), color="danger"),
            "",  # map-status
        )

# ----------------------------
# Render final table in AG Grid

@app.callback(
    Output("grid", "columnDefs"),
    Output("grid", "rowData"),
    Input("store-df-final", "data"),
)
def render_final_table(final_records):
    if not final_records:
        return [], []
    df = pd.DataFrame(final_records)
    payload = df_to_aggrid_payload(df)
    return payload["columns"], payload["rows"]

# ----------------------------
# Download: use stored df payload (exactly what’s shown in grid)
# ----------------------------
@app.callback(
    Output("dl-xlsx", "data"),
    Input("btn-download", "n_clicks"),
    State("store-df-final", "data"),
    State("in-out-name", "value"),
    prevent_initial_call=True,
)
def on_download(n, final_records, out_name):
    if not final_records:
        return no_update
    df = pd.DataFrame(final_records)
    filename = (out_name or "io_table.xlsx").strip()
    if not filename.lower().endswith(".xlsx"):
        filename += ".xlsx"
    return dcc.send_data_frame(df.to_excel, filename=filename, index=False)

@app.callback(
    Output("grid-map-l1", "rowData"),
    Output("grid-map-l2", "rowData"),
    Input("store-df-raw", "data"),
    Input("store-meta", "data"),
)
def load_mapping_tables(raw_records, meta):
    if not raw_records or not meta:
        return [], []

    df = pd.DataFrame(raw_records)
    lvl1_col = meta.get("lvl1_col")
    lvl2_col = meta.get("lvl2_col")

    def make_rows(col):
        if not col or col not in df.columns:
            return []
        uniq = sorted([v for v in df[col].dropna().unique().tolist() if str(v).strip() != ""])
        return [{"value": v, "label": v} for v in uniq]

    return make_rows(lvl1_col), make_rows(lvl2_col)

@app.callback(
    Output("collapse-cat-mapping", "is_open"),
    Input("btn-toggle-mapping", "n_clicks"),
    State("collapse-cat-mapping", "is_open"),
    prevent_initial_call=True,
)
def toggle_mapping_panel(n, is_open):
    return not is_open

@app.callback(
    Output("btn-apply-maps", "disabled"),
    Input("store-df-raw", "data"),
)
def disable_apply_if_no_table(raw_records):
    return not bool(raw_records)
@app.callback(
    Output("data-summary", "children"),
    Input("store-df-final", "data"),
)
def update_data_summary(final_records):
    if not final_records:
        return html.Div("Build the table to see a summary.", className="text-muted")

    df = pd.DataFrame(final_records)

    blocks = []

    # --------------------
    # Overall counts
    # --------------------
    n_rows = len(df)

    n_nadh = df["nadh_stem"].nunique() if "nadh_stem" in df.columns else 0
    n_fad  = df["fad_stem"].replace("", pd.NA).dropna().nunique() if "fad_stem" in df.columns else 0

    blocks.append(
        html.Ul([
            html.Li(f"Total paired rows: {n_rows}"),
            html.Li(f"Unique NADH files: {n_nadh}"),
            html.Li(f"Unique FAD files: {n_fad}"),
        ])
    )

    # --------------------
    # Categorical breakdowns
    # --------------------
    cat_cols = [c for c in df.columns if c.startswith("cat__")]

    for col in cat_cols:
        counts = (
            df[col]
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .sort_index()
        )

        if counts.empty:
            continue

        blocks.append(html.Hr())
        blocks.append(html.H6(f"Counts by {col.replace('cat__', '')}"))

        blocks.append(
            dbc.Table(
                [
                    html.Thead(html.Tr([html.Th("Group"), html.Th("Count")])),
                    html.Tbody([
                        html.Tr([html.Td(k), html.Td(v)])
                        for k, v in counts.items()
                    ]),
                ],
                bordered=True,
                size="sm",
                className="mb-0",
            )
        )

    return blocks


def create_app():

    return app

if __name__ == "__main__":
    create_app().run(debug=True)