# flimexplorer/layouts/components.py
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
import dash_ag_grid as dag
import plotly.graph_objects as go


def plotting_layout() -> dbc.Card:
    return dbc.Card(
        className="shadow-sm",
        children=[
            dbc.CardHeader(
                dbc.Row(
                    [
                        dbc.Col(html.Span("Plot Controls")),
                        dbc.Col(
                            dbc.Button(
                                "Show / hide",
                                id="btn-collapse-plot-controls",
                                color="secondary",
                                outline=True,
                                size="sm",
                                className="ms-auto",
                            ),
                            width="auto",
                        ),
                    ],
                    align="center",
                    justify="between",
                )
            ),
            dbc.Collapse(
                id="collapse-plot-controls",
                is_open=True,  # start open; set False if you want collapsed by default
                children=dbc.CardBody(
                    [
                        html.Label("Metric (y)"),
                        dcc.Dropdown(id="dd-metric", options=[], value=None, clearable=False, persistence=True, persistence_type="memory"),
                        html.Br(),

                        html.Label("Primary (x)"),
                        dcc.Dropdown(id="dd-group", options=[], value=None, clearable=False, persistence=True, persistence_type="memory"),
                        html.Br(),

                        html.Label("Secondary (hue)"),
                        dcc.Dropdown(
                            id="dd-hue",
                            options=[{"label": "— none —", "value": "— none —"}],
                            value="— none —",
                            clearable=False,
                            persistence=True,
                            persistence_type="memory",
                        ),
                        html.Hr(),

                        dbc.Switch(
                            id="sw-showpoints",
                            label="Show datapoints",
                            value=True,
                            className="mb-2",
                        ),
                        dbc.Switch(
                            id="sw-hide-outliers",
                            label="Hide outliers in plot",
                            value=False,
                            className="mb-2",
                        ),

                        dbc.Button(
                            id="btn-toggle-plot",
                            children=[html.I(className="bi bi-eye-slash me-2"), "Hide plot"],
                            color="warning",
                            className="w-10 mt-2",
                        ),

                        html.Hr(className="my-3"),

                        dbc.Accordion(
                            start_collapsed=True,
                            flush=True,
                            children=[
                                dbc.AccordionItem(
                                    title="Tokens & Patterns (overlay path construction)",
                                    children=[
                                        html.Div(
                                            "Used only to build overlay file paths.",
                                            className="text-muted small mb-2",
                                        ),
                                        dbc.Label("NADH photons pattern"),
                                        dcc.Input(
                                            id="pat-nadh",
                                            value="{stem}.asc",
                                            type="text",
                                            style={"width": "100%"},
                                        ),
                                        html.Br(), html.Br(),
                                        dbc.Label("FAD photons pattern"),
                                        dcc.Input(
                                            id="pat-fad",
                                            value="{stem}.asc",
                                            type="text",
                                            style={"width": "100%"},
                                        ),
                                        html.Br(), html.Br(),
                                        dbc.Label("NADH color pattern"),
                                        dcc.Input(
                                            id="pat-cnadh",
                                            value="{stem}_color_Imag.bmp",
                                            type="text",
                                            style={"width": "100%"},
                                        ),
                                        html.Br(), html.Br(),
                                        dbc.Label("FAD color pattern"),
                                        dcc.Input(
                                            id="pat-cfad",
                                            value="{stem}_color_Imag.bmp",
                                            type="text",
                                            style={"width": "100%"},
                                        ),
                                        html.Br(), html.Br(),
                                        dbc.Label("Mask pattern"),
                                        dcc.Input(
                                            id="pat-mask",
                                            value="{stem}.png",
                                            type="text",
                                            style={"width": "100%"},
                                        ),
                                    ],
                                ),

                                dbc.AccordionItem(
                                    title="Advanced plot controls",
                                    children=[
                                        html.Label("Hue palette"),
                                        dcc.Dropdown(
                                            id="dd-palette",
                                            options=[
                                                {"label": "Plotly (default)", "value": "Plotly"},
                                                {"label": "D3", "value": "D3"},
                                                {"label": "G10", "value": "G10"},
                                                {"label": "T10", "value": "T10"},
                                                {"label": "Alphabet (many colors)", "value": "Alphabet"},
                                                {"label": "Dark24", "value": "Dark24"},
                                                {"label": "Light24", "value": "Light24"},
                                                {"label": "Set1", "value": "Set1"},
                                                {"label": "Pastel1", "value": "Pastel1"},
                                                {"label": "Bold", "value": "Bold"},
                                                {"label": "Safe (colorblind-ish)", "value": "Safe"},
                                                {"label": "Vivid", "value": "Vivid"},
                                            ],
                                            value="Plotly",
                                            clearable=False,
                                        ),
                                        html.Br(),

                                        dbc.Row(
                                            className="g-2",
                                            children=[
                                                dbc.Col(
                                                    md=6,
                                                    children=[
                                                        dbc.Label("Font family"),
                                                        dcc.Dropdown(
                                                            id="plot-font-family",
                                                            options=[
                                                                {"label": "System UI", "value": "system-ui"},
                                                                {"label": "Arial", "value": "Arial"},
                                                                {"label": "Helvetica", "value": "Helvetica"},
                                                                {"label": "Courier New", "value": "Courier New"},
                                                            ],
                                                            value="system-ui",
                                                            clearable=False,
                                                        ),
                                                    ],
                                                ),
                                                dbc.Col(
                                                    md=6,
                                                    children=[
                                                        dbc.Label("Font size"),
                                                        dcc.Dropdown(
                                                            id="plot-font-size",
                                                            options=[
                                                                {"label": "10", "value": 10},
                                                                {"label": "12", "value": 12},
                                                                {"label": "14", "value": 14},
                                                                {"label": "16", "value": 16},
                                                                {"label": "18", "value": 18},
                                                            ],
                                                            value=12,
                                                            clearable=False,
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),

                                        html.Hr(className="my-2"),

                                        dbc.Label("Y-axis label (optional)"),
                                        dcc.Input(
                                            id="axis-y-label",
                                            type="text",
                                            placeholder="Leave blank to use metric name. e.g., NADH &alpha;<sub>1</sub>",
                                            value="",
                                            style={"width": "100%"},
                                        ),

                                        dbc.Label("X-axis label (optional)"),
                                        dcc.Input(
                                            id="axis-x-label",
                                            type="text",
                                            placeholder="e.g., Treatment group",
                                            value="",
                                            style={"width": "100%"},
                                        ),
                                        html.Div(
                                            "Supports HTML: &alpha; &beta; &tau; <sub> </sub> <sup> </sup>.",
                                            className="text-muted small mt-1",
                                        ),

                                        html.Hr(className="my-2"),

                                        dbc.Row(
                                            className="g-2",
                                            children=[
                                                dbc.Col(
                                                    md=6,
                                                    children=[
                                                        dbc.Label("Insert into"),
                                                        dcc.Dropdown(
                                                            id="axis-insert-target",
                                                            options=[
                                                                {"label": "Y-axis label", "value": "y"},
                                                                {"label": "X-axis label", "value": "x"},
                                                            ],
                                                            value="y",
                                                            clearable=False,
                                                        ),
                                                    ],
                                                ),
                                                dbc.Col(
                                                    md=6,
                                                    children=[
                                                        dbc.Label("Insert symbols"),
                                                        dcc.Dropdown(
                                                            id="axis-insert",
                                                            options=[
                                                                {"label": "α", "value": "&alpha;"},
                                                                {"label": "β", "value": "&beta;"},
                                                                {"label": "γ", "value": "&gamma;"},
                                                                {"label": "Δ", "value": "&Delta;"},
                                                                {"label": "τ", "value": "&tau;"},
                                                                {"label": "μ", "value": "&mu;"},
                                                                {"label": "Ω", "value": "&Omega;"},
                                                                {"label": "±", "value": "&plusmn;"},
                                                                {"label": "×", "value": "&times;"},
                                                                {"label": "≤", "value": "&le;"},
                                                                {"label": "≥", "value": "&ge;"},
                                                                {"label": "Subscript template", "value": "<sub>1</sub>"},
                                                                {"label": "Superscript template", "value": "<sup>-1</sup>"},
                                                                {"label": "τ₁ template", "value": "&tau;<sub>1</sub>"},
                                                                {"label": "α₁ template", "value": "&alpha;<sub>1</sub>"},
                                                            ],
                                                            value=None,
                                                            placeholder="Pick to insert…",
                                                            clearable=True,
                                                        ),
                                                        html.Div(
                                                            "Tip: use <sub> </sub> and <sup> </sup> for indices/exponents.",
                                                            className="text-muted small mt-1",
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        html.Br(),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
            ),
        ],
    )

def overlay_section_layout() -> dbc.Card:
    return dbc.Card(
        className="shadow-sm mb-4",
        children=[
            dbc.Container(
                fluid=True,
                className="p-2",
                children=[
                    # Panels
                    dbc.Row(
                        className="g-2 mb-2",
                        children=[
                            dbc.Col(
                                width=12,
                                children=[
                                    dbc.Label("Panels to show"),
                                    dcc.Dropdown(
                                        id="ov-panels",
                                        options=[
                                            {"label": "NADH photons (intensity)", "value": "nadh"},
                                            {"label": "FAD photons (intensity)", "value": "fad"},
                                            {"label": "NADH color (FLIM)", "value": "cnadh"},
                                            {"label": "FAD color (FLIM)", "value": "cfad"},
                                        ],
                                        value=["nadh", "fad", "cnadh", "cfad"],
                                        multi=True,
                                        clearable=False,
                                    ),
                                ],
                            )
                        ],
                    ),

                    # Flip controls
                    dbc.Row(
                        className="g-2 mb-2",
                        children=[
                            dbc.Col(
                                md=6,
                                children=[
                                    dbc.Label("Flip INTENSITY image"),
                                    dbc.Checklist(
                                        id="mask-flip-int",
                                        options=[
                                            {"label": "Flip horizontally", "value": "h"},
                                            {"label": "Flip vertically", "value": "v"},
                                        ],
                                        value=[],
                                        inline=True,
                                        switch=True,
                                    ),
                                ],
                            ),
                            dbc.Col(
                                md=6,
                                children=[
                                    dbc.Label("Flip COLOR image"),
                                    dbc.Checklist(
                                        id="mask-flip-col",
                                        options=[
                                            {"label": "Flip horizontally", "value": "h"},
                                            {"label": "Flip vertically", "value": "v"},
                                        ],
                                        value=[],
                                        inline=True,
                                        switch=True,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dbc.Row(
                        className="g-2 mb-2",
                        children=[
                            dbc.Col(
                                md=12,
                                children=dbc.Switch(
                                    id="ov-show-paths",
                                    label="Show debug file paths (attempted/exists)",
                                    value=False,
                                ),
                            ),
                        ],
                    ),
                    html.Div(
                        id="overlay-errors",
                        className="text-warning small mb-2",
                        style={"whiteSpace": "pre-wrap"},
                    ),
                    html.Div(id="overlay-container", className="p-2"),
                ],
            ),
        ],
    )

def outliers_section_layout() -> dbc.Card:
    return dbc.Card(
        className="shadow-sm",
        children=[
            dbc.CardBody(
                dbc.Container(
                    fluid=True,
                    className="p-2",
                    children=[
                        dbc.Row(
                            className="g-2 mb-2",
                            children=[
                                dbc.Col(
                                    width="auto",
                                    children=dbc.Button(
                                        "Mark current selection as OUTLIERS",
                                        id="btn-flag",
                                        color="danger",
                                    ),
                                ),
                                dbc.Col(
                                    width="auto",
                                    children=dbc.Button(
                                        "Unmark current selection",
                                        id="btn-unflag",
                                        color="secondary",
                                        #outline=True,
                                    ),
                                ),
                                dbc.Col(
                                    children=html.Div(
                                        id="outlier-msg",
                                        className="text-muted mt-1",
                                    )
                                ),
                            ],
                        ),
                        dbc.Card(
                            className="shadow-sm",
                            children=[
                                dbc.CardHeader("Flagged outliers (select rows to unmark)"),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            className="g-2 mb-2",
                                            children=[
                                                dbc.Col(
                                                    width="auto",
                                                    children=dbc.Button(
                                                        "Unmark selected flagged rows",
                                                        id="btn-unflag-checked",
                                                        color="warning",
                                                    ),
                                                ),
                                                dbc.Col(
                                                    children=html.Div(
                                                        id="outlier-list-msg",
                                                        className="text-muted mt-1",
                                                    )
                                                ),
                                            ],
                                        ),
                                        dash_table.DataTable(
                                            id="outlier-table",
                                            columns=[],
                                            data=[],
                                            row_selectable="multi",
                                            selected_rows=[],
                                            page_size=12,
                                            style_table={"overflowX": "auto"},
                                            style_cell={
                                                "fontFamily": "system-ui",
                                                "fontSize": "12px",
                                                "textAlign": "left",
                                            },
                                            style_header={"fontWeight": "600"},
                                            sort_action="native",
                                            filter_action="native",
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ],
                )
            ),
        ]    
    )
   
def stats_section_layout() -> dbc.Container:
    return dbc.Container(
        fluid=True,
        className="p-2",
        children=[
            # -------------------------
            # RESULTS (top, full width)
            # -------------------------
             dbc.Row(
                className="g-3",
                children=[
                    dbc.Col(
                        md=12,
                        children=[
                            dbc.CardBody(
                                [
                                    # -------------------------
                                    # Primary controls (always visible)
                                    # -------------------------
                                    dbc.Row(
                                        className="g-2",
                                        children=[
                                            dbc.Col(
                                                md=6,
                                                children=[
                                                    dbc.Label("Scope (pairs)"),
                                                    dcc.Dropdown(
                                                        id="stats-scope",
                                                        options=[
                                                            {"label": "No comparisons", "value": "none"},
                                                            {"label": "Compare all groups", "value": "all"},
                                                            {"label": "Within X (across hue)", "value": "within_x"},
                                                            {"label": "Within hue (across X)", "value": "within_hue"},
                                                            {"label": "Across X, same hue", "value": "across_x_same_hue"},
                                                            {"label": "Same X, across hue", "value": "same_x_across_hue"},
                                                            {"label": "All A×B combos", "value": "all_combos"},
                                                        ],
                                                        value="all",
                                                        clearable=False,
                                                    ),
                                                ],
                                            ),
                                            dbc.Col(
                                                md=3,
                                                children=[
                                                    dbc.Label("Test mode"),
                                                    dcc.Dropdown(
                                                        id="stats-mode",
                                                        options=[
                                                            {"label": "Auto (Welch/MWU/Perm<5)", "value": "auto"},
                                                            {"label": "Welch t-test", "value": "welch"},
                                                            {"label": "Mann–Whitney U", "value": "mwu"},
                                                            {"label": "Permutation", "value": "perm"},
                                                        ],
                                                        value="auto",
                                                        clearable=False,
                                                    ),
                                                ],
                                            ),
                                            dbc.Col(
                                                md=3,
                                                children=[
                                                    dbc.Label("Multiplicity"),
                                                    dcc.Dropdown(
                                                        id="stats-mcomp",
                                                        options=[
                                                            {"label": "Holm", "value": "holm"},
                                                            {"label": "Bonferroni", "value": "bonferroni"},
                                                            {"label": "Benjamini–Hochberg", "value": "fdr_bh"},
                                                            {"label": "Šidák", "value": "sidak"},
                                                        ],
                                                        value="holm",
                                                        clearable=False,
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),

                                    html.Hr(className="my-3"),

                                    dbc.Row(
                                        className="g-2",
                                        children=[
                                            dbc.Col(
                                                md=4,
                                                children=dbc.Checklist(
                                                    id="stats-exclude-outliers",
                                                    options=[{"label": "Exclude flagged outliers from stats", "value": "ex"}],
                                                    value=["ex"],
                                                    switch=True,
                                                ),
                                            ),
                                            dbc.Col(
                                                md=4,
                                                children=dbc.Checklist(
                                                    id="stats-enable-annot",
                                                    options=[{"label": "Annotate plot", "value": "annot"}],
                                                    value=["annot"],
                                                    switch=True,
                                                ),
                                            ),
                                            dbc.Col(
                                                md=4,
                                                children=dbc.Checklist(
                                                    id="stats-draw-bars",
                                                    options=[{"label": "Draw brackets/bars", "value": "bars"}],
                                                    value=["bars"],
                                                    switch=True,
                                                ),
                                            ),
                                        ],
                                    ),

                                    # -------------------------
                                    # Advanced controls (collapsed)
                                    # -------------------------
                                    html.Hr(className="my-3"),
                                    dbc.Accordion(
                                        start_collapsed=True,
                                        flush=True,
                                        children=[
                                            dbc.AccordionItem(
                                                title="Advanced: thresholds & permutation settings",
                                                children=[
                                                    dbc.Row(
                                                        className="g-2",
                                                        children=[
                                                            dbc.Col(
                                                                md=2,
                                                                children=[
                                                                    dbc.Label("α"),
                                                                    dcc.Input(
                                                                        id="stats-alpha",
                                                                        type="number",
                                                                        value=0.05,
                                                                        step=0.005,
                                                                        min=0,
                                                                        max=1,
                                                                        style={"width": "100%"},
                                                                    ),
                                                                ],
                                                            ),
                                                            dbc.Col(
                                                                md=5,
                                                                children=[
                                                                    dbc.Label("Permutation N"),
                                                                    dcc.Dropdown(
                                                                        id="stats-perm-n",
                                                                        options=[
                                                                            {"label": "2000", "value": 2000},
                                                                            {"label": "5000", "value": 5000},
                                                                            {"label": "20000", "value": 20000},
                                                                        ],
                                                                        value=5000,
                                                                        clearable=False,
                                                                    ),
                                                                ],
                                                            ),
                                                            dbc.Col(
                                                                md=5,
                                                                children=[
                                                                    dbc.Label("Permutation seed"),
                                                                    dcc.Input(
                                                                        id="stats-perm-seed",
                                                                        type="number",
                                                                        value=0,
                                                                        step=1,
                                                                        style={"width": "100%"},
                                                                    ),
                                                                ],
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            dbc.AccordionItem(
                                                title="Advanced: plot, table & annotation filters",
                                                children=[
                                                    dbc.Row(
                                                        className="g-2",
                                                        children=[
                                                            dbc.Col(
                                                                md=6,
                                                                children=[
                                                                    dbc.Checklist(
                                                                        id="stats-table-only-sig",
                                                                        options=[{"label": "Show only significant in table", "value": "sig"}],
                                                                        value=[],
                                                                        switch=True,
                                                                    ),
                                                                    dbc.Checklist(
                                                                        id="stats-annot-only-sig",
                                                                        options=[{"label": "Annotate only significant", "value": "sig"}],
                                                                        value=["sig"],
                                                                        switch=True,
                                                                    ),

                                                                ],
                                                            ),
                                                            dbc.Col(
                                                                md=6,
                                                                children=[
                                                                    dbc.Checklist(
                                                                        id="stats-add-ci",
                                                                        options=[{"label": "Add bootstrap CI for effect size", "value": "ci"}],
                                                                        value=[],
                                                                        switch=True,
                                                                    ),
                                                                    dbc.Row(
                                                                        className="g-2 mt-1",
                                                                        children=[
                                                                            dbc.Col(
                                                                                md=6,
                                                                                children=[
                                                                                    dbc.Label("CI bootstrap N"),
                                                                                    dcc.Input(
                                                                                        id="stats-ci-boot",
                                                                                        type="number",
                                                                                        value=1000,
                                                                                        step=250,
                                                                                        min=100,
                                                                                        style={"width": "100%"},
                                                                                    ),
                                                                                ],
                                                                            ),
                                                                            dbc.Col(
                                                                                md=6,
                                                                                children=[
                                                                                    dbc.Label("CI seed"),
                                                                                    dcc.Input(
                                                                                        id="stats-ci-seed",
                                                                                        type="number",
                                                                                        value=123,
                                                                                        step=1,
                                                                                        style={"width": "100%"},
                                                                                    ),
                                                                                ],
                                                                            ),
                                                                            dbc.Row(
                                                                                className="g-2 mt-2",
                                                                                children=[
                                                                                    dbc.Col(
                                                                                        md=6,
                                                                                        children=[
                                                                                            dbc.Label("Annotation spacing"),
                                                                                            dcc.Slider(
                                                                                                id="stats-annot-spacing",
                                                                                                min=0.5,
                                                                                                max=2.5,
                                                                                                step=0.25,
                                                                                                value=1.0,
                                                                                                updatemode="mouseup",
                                                                                                marks={
                                                                                                    0.5: "Compact",
                                                                                                    1.0: "Default",
                                                                                                    1.5: "Spacious",
                                                                                                    2.5: "Very spacious",
                                                                                                },
                                                                                                tooltip={"placement": "bottom", "always_visible": False},
                                                                                            ),
                                                                                        ],
                                                                                    ),
                                                                                ],
                                                                            ),

                                                                        ],
                                                                    ),
                                                                ],
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                ]
                            )

                            ],
                    )
                ],
            ),
        
            dbc.Row(
                className="g-3",
                children=[
                    dbc.Col(
                        md=12,
                        children=[
                            dbc.Card(
                                className="shadow-sm",
                                children=[
                                    dbc.CardHeader("Results"),
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                className="g-2 align-items-center mb-2",
                                                children=[
                                                    dbc.Col(
                                                        width="auto",
                                                        children=dbc.Button(
                                                            "Compute stats",
                                                            id="btn-stats-run",
                                                            color="primary",
                                                        ),
                                                    ),
                                                    dbc.ButtonGroup(
                                                        [
                                                            dbc.Button("Annotate selected", id="btn-annot-selected", color="info", outline=True),
                                                            dbc.Button("Annotate all", id="btn-annot-all", color="info", outline=True),
                                                        ],
                                                        size="sm",
                                                    ),

                                                    dbc.Col(
                                                        children=html.Span(
                                                            id="stats-msg",
                                                            className="text-muted ms-2",
                                                        )
                                                    ),
                                                ],
                                            ),
                                            dbc.Card(
                                                className="mb-3",
                                                children=[
                                                    dbc.CardHeader("Methods summary"),
                                                    dbc.CardBody(
                                                        html.Pre(
                                                            id="stats-summary",
                                                            children="Run statistics to generate a methods summary.",
                                                            className="small text-muted",
                                                            style={
                                                                "whiteSpace": "pre-wrap",
                                                                "margin": 0,
                                                                "minHeight": "90px",
                                                            },
                                                        )
                                                    ),
                                                ],
                                            ),
                                            dag.AgGrid(
                                                id="stats-table",
                                                rowData=[],
                                                columnDefs=[],
                                                className="ag-theme-alpine-dark",
                                                defaultColDef={
                                                    "sortable": True,
                                                    "filter": True,
                                                    "resizable": True,   # ✅ this is the key
                                                    "floatingFilter": True,
                                                },
                                                dashGridOptions={
                                                        "rowSelection": "multiple",
                                                        "rowMultiSelectWithClick": True,
                                                        "suppressRowClickSelection": True,
                                                        "animateRows": False,
                                                },
                                                style={"height": "460px", "width": "100%"},
                                            ),

                                            
                                            html.Div(
                                                id="stats-warnings",
                                                className="text-muted mt-2",
                                                style={"whiteSpace": "pre-wrap"},
                                            ),
                                        ]
                                    ),
                                ],
                            ),
                        ],
                    )
                ],
            ),

            html.Hr(),

           
           ],
    )

def export_section_layout() -> dbc.Card:
    return dbc.Card(
        class_name="shadow-sm mb-4",
        children=[
            dbc.CardHeader(html.H4("Export", className="mb-0")),
            dbc.CardBody(
                dbc.Container(
                    fluid=True,
                    className="p-2",
                    children=[
                        # 1) Export flagged outliers (existing)
                        dbc.Card(
                            className="shadow-sm mb-3",
                            children=[
                                dbc.CardHeader("Export flagged outliers"),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            className="g-2 align-items-center",
                                            children=[
                                                dbc.Col(
                                                    width="auto",
                                                    children=dbc.Button(
                                                        "Download flagged outliers (.xlsx)",
                                                        id="btn-export-outliers",
                                                        color="success",
                                                    ),
                                                ),
                                                dbc.Col(children=html.Div(id="export-msg", className="text-muted")),
                                            ],
                                        ),
                                        dcc.Download(id="download-outliers-xlsx"),
                                    ]
                                ),
                            ],
                        ),

                        # 2) Export full dataframe (includes outliers col)
                        dbc.Card(
                            className="shadow-sm mb-3",
                            children=[
                                dbc.CardHeader("Export full dataframe"),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            className="g-2 align-items-center",
                                            children=[
                                                dbc.Col(
                                                    width="auto",
                                                    children=dbc.Button(
                                                        "Download full table (.xlsx)",
                                                        id="btn-export-full-df",
                                                        color="primary",
                                                        
                                                    ),
                                                ),
                                                dbc.Col(children=html.Div(id="export-full-msg", className="text-muted")),
                                            ],
                                        ),
                                        dcc.Download(id="download-full-df-xlsx"),
                                    ]
                                ),
                            ],
                        ),

                        # 3) Export PNG overlays for flagged outliers (zipped)
                        dbc.Card(
                            className="shadow-sm",
                            children=[
                                dbc.CardHeader("Export flagged outlier overlay PNGs"),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            className="g-2 align-items-center",
                                            children=[
                                                dbc.Col(
                                                    width="auto",
                                                    children=dbc.Button(
                                                        "Download outlier overlay PNGs (.zip)",
                                                        id="btn-export-outlier-overlays",
                                                        color="info",
                                                        
                                                    ),
                                                ),
                                                dbc.Col(children=html.Div(id="export-overlays-msg", className="text-muted")),
                                            ],
                                        ),
                                        dcc.Download(id="download-outlier-overlays-zip"),
                                        html.Div(
                                            "Uses the NADH photons overlay + mask outline for each flagged outlier row.",
                                            className="text-muted small mt-2",
                                        ),
                                    ]
                                ),
                            ],
                        ),
                        dbc.Card(
                            className="shadow-sm mt-3",
                            children=[
                                dbc.CardHeader("Export current plot (publication quality)"),
                                dbc.CardBody([
                                    dbc.Row(className="g-2", children=[
                                        dbc.Col(width="auto", children=dbc.Button("Download SVG", id="btn-export-plot-svg", color="secondary")),
                                        dbc.Col(width="auto", children=dbc.Button("Download PDF", id="btn-export-plot-pdf", color="secondary")),
                                        dbc.Col(width="auto", children=dbc.Button("Download PNG (hi-res)", id="btn-export-plot-png", color="primary")),
                                        dbc.Col(children=html.Div(id="export-plot-msg", className="text-muted")),
                                    ]),
                                    dcc.Download(id="download-plot"),
                                ])
                            ]
                        ),

                        # 4) Export stats
                        dbc.Card(
                            className="shadow-sm mb-3",
                            children=[
                                dbc.CardHeader("Export statistics"),
                                dbc.CardBody(
                                    [
                                        html.Div(
                                            [
                                                html.Div("Label exported file with:", className="text-muted small mb-1"),
                                                html.Div(id="export-stats-label", className="small"),
                                            ],
                                            className="mb-2",
                                        ),
                                        dbc.Row(
                                            className="g-2 align-items-center",
                                            children=[
                                                dbc.Col(
                                                    width="auto",
                                                    children=dbc.Button(
                                                        "Download stats (.xlsx)",
                                                        id="btn-export-stats",
                                                        color="secondary",
                                                        outline=False,
                                                    ),
                                                ),
                                                dbc.Col(children=html.Div(id="export-stats-msg", className="text-muted")),
                                            ],
                                        ),
                                        dcc.Download(id="download-stats-xlsx"),
                                    ]
                                ),
                            ],
                        ),

                    ],
                ),
            
            )
        ],
    )

