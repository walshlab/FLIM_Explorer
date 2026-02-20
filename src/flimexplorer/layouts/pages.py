# flimexplorer/layouts/pages.py
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
import plotly.graph_objects as go

from flimexplorer.layouts.components import (
    plotting_layout,
)

APP_TITLE = "FLIMExplorer"


def welcome_layout() -> dbc.Container:
    return dbc.Container(
        fluid=True,
        className="py-4",
        children=[
            # -------------------------------------------------
            # Header
            # -------------------------------------------------
            dbc.Row(
                className="mb-4",
                children=[
                    dbc.Col(
                        md=12,
                        children=[
                            html.H1(
                                "FLIMExplorer",
                                className="mb-2",
                            ),
                            html.H5(
                                "Interactive visualization and analysis of single-cell autofluorescence fluorescence lifetime microscopy data",
                                className="text-muted",
                            ),
                        ],
                    )
                ],
            ),

            # -------------------------------------------------
            # What is this?
            # -------------------------------------------------
            dbc.Card(
                className="shadow-sm mb-4",
                children=[
                    dbc.CardHeader("What is this tool?"),
                    dbc.CardBody(
                        [
                            html.P(
                                "FLIMExplorer is an interactive analysis and visualization environment for exploring "
                                "cell-resolved autofluorescence FLIM endpoints, linking quantitative measurements "
                                "back to raw images, and performing appropriate statistical comparisons across "
                                "experimental conditions.",
                                className="mb-2",
                            ),
                            html.P(
                                "Unlike population-averaged assays, this tool is designed to preserve and interrogate "
                                "single-cell heterogeneity in metabolic and structural imaging data.",
                                className="mb-0 text-muted",
                            ),
                        ]
                    ),
                ],
            ),

            # -------------------------------------------------
            # What can you do?
            # -------------------------------------------------
            dbc.Card(
                className="shadow-sm mb-4",
                children=[
                    dbc.CardHeader("What can you do here?"),
                    dbc.CardBody(
                        dbc.Row(
                            className="g-3",
                            children=[
                                dbc.Col(
                                    md=6,
                                    children=html.Ul(
                                        [
                                            html.Li("Explore distributions of single-cell FLIM endpoints (e.g. NAD(P)H, FAD, ORR, FLIRR)"),
                                            html.Li("Visualize group and condition-dependent heterogeneity"),
                                            html.Li("Link per-cell measurements back to intensity and FLIM images"),
                                        ]
                                    ),
                                ),
                                dbc.Col(
                                    md=6,
                                    children=html.Ul(
                                        [
                                            html.Li("Flag and manage outlier cells"),
                                            html.Li("Run appropriate statistical comparisons with multiple-comparison correction"),
                                            html.Li("Export figures, statistics, and flagged cells for downstream use"),
                                        ]
                                    ),
                                ),
                            ],
                        )
                    ),
                ],
            ),

            # -------------------------------------------------
            # Typical workflow
            # -------------------------------------------------
            dbc.Card(
                className="shadow-sm mb-4",
                children=[
                    dbc.CardHeader("Typical workflow"),
                    dbc.CardBody(
                        html.Ol(
                            [
                                html.Li("Import a per-cell table (CSV/XLSX) or import metadata (CSV/XLSX) to extract one from SPCImage outputs"),
                                html.Li("Select a FLIM metric and grouping variables"),
                                html.Li("Explore distributions and single-cell variability"),
                                html.Li("Inspect image overlays for selected cells"),
                                html.Li("Run statistical comparisons across conditions"),
                                html.Li("Export results, statistics, and flagged outliers"),
                            ],
                            className="mb-0",
                        )
                    ),
                ],
            ),

            # -------------------------------------------------
            # Import guidance
            # -------------------------------------------------
            dbc.Card(
                className="shadow-sm mb-4",
                children=[
                    dbc.CardHeader("Which import option should I use?"),
                    dbc.CardBody(
                        dbc.Row(
                            className="g-3",
                            children=[
                                dbc.Col(
                                    md=6,
                                    children=[
                                        html.H6("Table Import (CSV/XLSX)"),
                                        html.P(
                                            "Use this option if you already have a per-cell table of FLIM endpoint measurements "
                                            "exported from another pipeline.",
                                            className="mb-1",
                                        ),
                                        
                                    ],
                                ),
                                dbc.Col(
                                    md=6,
                                    children=[
                                        html.H6("Cell-wise Extraction"),
                                        html.P(
                                            "Use this option if you have SPCImage outputs and want to generate a "
                                            "per-cell table directly from ASC files and segmentation masks.",
                                            className="mb-0",
                                        ),
                                        html.P(
                                            "This is the recommended starting point for most users.",
                                            className="text-muted mb-0",
                                        ),
                                    ],
                                ),
                            ],
                        )
                    ),
                    dbc.CardBody(
                        [
                             dbc.Row(
                                className="g-2 mt-2 align-items-center",
                                children=[
                                    dbc.Col(
                                        width="auto",
                                        children=dbc.Button(
                                            "Download Import for Extraction template (.xlsx)",
                                            id="btn-spc-template",
                                            color="primary",
                                            outline=True,
                                            size="sm",
                                        ),
                                    ),
                                    dbc.Col(
                                        children=html.Div(
                                            "Use this template to format the SPC import sheet (edit paths + stem).",
                                            className="text-muted small",
                                        )
                                    ),
                                ],
                            ),

                            #html.Div(id="spc-upload-msg", className="text-muted mt-2"),

                            dcc.Download(id="download-spc-template-xlsx"),
                        ]
                    ),
                ],
            ),

            # -------------------------------------------------
            # Footer / citation
            # -------------------------------------------------
            dbc.Card(
                className="shadow-sm",
                children=[
                    dbc.CardBody(
                        [
                            html.P(
                                [
                                    html.B("Citation & usage"),
                                    html.Br(),
                                    "If you use this tool in a publication, please cite the corresponding manuscript "
                                    "or software repository.",
                                ],
                                className="mb-2",
                            ),
                            html.P(
                                "For questions, issues, or feature requests, please contact the authors or open an issue "
                                "on the project repository.",
                                className="text-muted mb-0",
                            ),
                        ]
                    ),
                ],
            ),
        ],
    )


def import_layout() -> dbc.Container:
    
    upload_card = dbc.Card(
        className="shadow-sm",
        children=[
            dbc.CardHeader("Import (CSV/XLSX)"),
            dbc.CardBody(
                [
                    dcc.Upload(
                        id="upload",
                        accept=".csv,.xlsx,.xls,.xlsm",
                        children=html.Div(["Drag & Drop or ", html.B("Select a CSV/XLSX")]),
                        className="p-3 border rounded text-center",
                        style={"cursor": "pointer"},
                        multiple=False,
                    ),
                    html.Div(id="upload-msg", className="text-muted mt-2"),
                ]
            ),
        ],
    )

    spc_extract_section = dbc.Container(
        [
            dbc.Card(
                className="shadow-sm mb-3",
                children=[
                    dbc.CardHeader("SPC input Excel (paths to ASC + mask)"),
                    dbc.CardBody(
                        [
                            dcc.Upload(
                                id="spc-upload",
                                accept=".xlsx,.xls,.xlsm,.csv",
                                children=html.Div(["Drag & Drop or ", html.B("Select SPC Excel/CSV")]),
                                className="p-3 border rounded text-center",
                                style={"cursor": "pointer"},
                                multiple=False,
                            ),
                            html.Div(id="spc-upload-msg", className="text-muted mt-2"),
                        ]
                    ),
                ],
            ),
            dbc.Card(
                className="shadow-sm mb-3",
                children=[
                    dbc.CardHeader("ASC filename patterns"),
                    dbc.CardBody(
                        [
                            dbc.Alert(
                                "Use {stem} as the base name (without extension). All patterns must end in .asc.",
                                color="info",
                                className="mb-3",
                            ),
                            dbc.Row(
                                className="g-2",
                                children=[
                                    dbc.Col(
                                        md=6,
                                        children=[
                                            html.H6("NADH"),
                                            dbc.Label("a1"),
                                            dcc.Input(id="nadh-a1-sfx", value="{stem}_a1[%].asc", type="text", style={"width": "100%"}),
                                            dbc.Label("t1"),
                                            dcc.Input(id="nadh-t1-sfx", value="{stem}_t1.asc", type="text", style={"width": "100%"}),
                                            dbc.Label("t2"),
                                            dcc.Input(id="nadh-t2-sfx", value="{stem}_t2.asc", type="text", style={"width": "100%"}),
                                            dbc.Label("photons"),
                                            dcc.Input(id="nadh-ph-sfx", value="{stem}_photons.asc", type="text", style={"width": "100%"}),
                                        ],
                                    ),
                                    dbc.Col(
                                        md=6,
                                        children=[
                                            html.H6("FAD (optional)"),
                                            dbc.Label("a1"),
                                            dcc.Input(id="fad-a1-sfx", value="{stem}_a1[%].asc", type="text", style={"width": "100%"}),
                                            dbc.Label("t1"),
                                            dcc.Input(id="fad-t1-sfx", value="{stem}_t1.asc", type="text", style={"width": "100%"}),
                                            dbc.Label("t2"),
                                            dcc.Input(id="fad-t2-sfx", value="{stem}_t2.asc", type="text", style={"width": "100%"}),
                                            dbc.Label("photons"),
                                            dcc.Input(id="fad-ph-sfx", value="{stem}_photons.asc", type="text", style={"width": "100%"}),
                                        ],
                                    ),
                                ],
                            ),
                        ]
                    ),
                ],
            ),
            dbc.Card(
                className="shadow-sm",
                children=[
                    dbc.CardBody(
                        [
                            dbc.Row(
                                className="g-2 align-items-center",
                                children=[
                                    dbc.Col(width="auto", children=dbc.Button("Extract SPC → per-cell table", id="btn-spc-extract", color="primary")),
                                    dbc.Col(width="auto", children=dbc.Button("Download extracted per-cell (.xlsx)", id="btn-spc-download", color="success", outline=True)),
                                ],
                            ),
                            html.Div(id="spc-import-msg", className="text-muted mt-2"),
                            dcc.Download(id="download-spc-xlsx"),
                        ]
                    )
                ],
            ),
        ],
        fluid=True,
        className="py-2",
    )

    return dbc.Container(
        [
            html.H2("Import", className="my-3"),
            dbc.Alert(
                [
                    html.B("How to use this page"),
                    html.Ul(
                        [
                            html.Li("Use Table import to load a CSV/XLSX containing per-cell measurements."),
                            html.Li("Use SPC Extract only if you have SPCImage output and want to generate a per-cell table."),
                            html.Li("Both methods produce the same type of table for downstream plotting and analysis."),
                            html.Li("For example SPCImage Excel templates, see the 'Examples' folder in the GitHub repo."),
                            html.Li("After importing, switch to the 'Explorer' tab to visualize and analyze your data."),
                        ],
                        className="mb-0",
                    ),
                ],
                color="info",
                className="mb-3",
            ),

            # --- Collapsible: Table import ---
            dbc.Button(
                "Table import (CSV/XLSX)",
                id="btn-collapse-table-import",
                color="info",
                outline=True,
                className="w-100 text-start mb-2",
            ),
            dbc.Collapse(
                dbc.Card(dbc.CardBody([upload_card]), className="shadow-sm mb-3"),
                id="collapse-table-import",
                is_open=True,
            ),

            # --- Collapsible: SPC extract ---
            dbc.Button(
                "SPCImage Extract (per-cell averaging from ASCII text images and cell mask)",
                id="btn-collapse-spc",
                color="info",
                outline=True,
                className="w-100 text-start mb-2",
            ),
            dbc.Collapse(
                dbc.Card(dbc.CardBody([spc_extract_section]), className="shadow-sm mb-3"),
                id="collapse-spc",
                is_open=False,
            ),
        ],
        fluid=True,
        className="py-2",
    )



def explorer_layout() -> dbc.Container:

    return dbc.Container(
        [
            html.H2(APP_TITLE, className="my-3"),

            # TOP ROW: Plot controls 
            dbc.Row(
                className="g-3 mb-3",
                children=[
                    dbc.Col(plotting_layout()),

                ],
            ),

            # PLOT + DETAILS
            dbc.Row(
                className="g-3 mb-3",
                children=[
                    # --- PLOT COLUMN (toggleable) ---
                    dbc.Col(
                        id="col-plot",
                        md=6,
                        children=[
                            dbc.Card(
                                className="shadow-sm",
                                children=[
                                    dbc.CardHeader(
                                        dbc.Row(
                                            [
                                                dbc.Col("Violin plot"),
                                            ],
                                            align="center",
                                            justify="between",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="graph",
                                                figure=go.Figure(),
                                                clear_on_unhover=True,
                                                config={
                                                    "displaylogo": False,
                                                    "modeBarButtonsToAdd": ["select2d", "lasso2d"],
                                                },
                                                style={"height": "520px"},
                                            )
                                        ]
                                    ),
                                ],
                            )
                        ],
                    ),

                    # DETAILS COLUMN (RIGHT, TABS)
                    dbc.Col(
                        md=6,
                        id = "col-details",
                        children =[
                            dbc.Card(
                                className="shadow-sm",
                                children=[
                                    dbc.CardHeader("Modules"),
                                    dbc.CardBody(
                                        [
                                            html.Div(id="modules-container")
                                        ]
                                    ),
                                ],
                            ),
                            
                        ],
                    ),
                ],
            ),

            # SELECTED ROWS TABLE
            dbc.Card(
                className="shadow-sm mb-4",
                children=[
                    dbc.CardHeader("Selected Rows"),
                    dbc.CardBody(
                        [
                            dash_table.DataTable(
                                id="table",
                                columns=[],
                                data=[],
                                page_size=10,
                                style_table={"overflowX": "auto", "maxHeight": "360px", "overflowY": "auto"},
                                style_cell={"fontFamily": "system-ui", "fontSize": "12px", "textAlign": "left"},
                                style_header={"fontWeight": "600"},
                            )
                        ]
                    ),
                ],
            ),
        ],
        fluid=True,
        className="py-2",
    )
