# flimexplorer/app.py
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Dash, dcc

from flimexplorer.layouts.pages import welcome_layout, import_layout, explorer_layout
from flimexplorer.callbacks.register import register_callbacks

APP_TITLE = "FLIMExplorer"


def create_app() -> Dash:
    app = Dash(
        __name__,
        title=APP_TITLE,
        external_stylesheets=[dbc.themes.CYBORG],
        suppress_callback_exceptions=True,
    )

    app.layout = dbc.Container(
        [
            dcc.Store(id="store-df", data=None),
            dcc.Store(id="store-selected", data=[]),
            dcc.Store(id="store-stats", data=None),
            dcc.Store(id="ui-hide-plot", data=False),
            dcc.Store(id="axis-active", data="y"),
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="store-paper-mode", data=False),
            dcc.Store(id="store-fig", data=None),

            dcc.Tabs(
                id="main-tabs",
                value="tab-welcome",
                children=[
                    dcc.Tab(label="Welcome", value="tab-welcome", children=[welcome_layout()]),
                    dcc.Tab(label="Import", value="tab-import", children=[import_layout()]),
                    dcc.Tab(label="Explorer", value="tab-explorer", children=[explorer_layout()]),
                ],
            ),
        ],
        fluid=True,
        id="app-root",
    )

    register_callbacks(app)
    return app
    
if __name__ == "__main__":
    app = create_app()
    app.run()    
