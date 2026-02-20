
import argparse
import threading
import webbrowser
from flimexplorer.app import create_app as create_main_app
from flimexplorer.tools.generate_input_table import create_app as create_io_table_app

def main():
    p = argparse.ArgumentParser(prog="flimexplorer")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", default=8050, type=int)
    p.add_argument("--debug", action="store_true")

    # choose which Dash app to run
    p.add_argument(
        "--tool",
        default="main",
        choices=["main", "io-table"],
        help="Which GUI to launch.",
    )

    args = p.parse_args()

    # pick the app
    if args.tool == "io-table":
        app = create_io_table_app()
        title = "FLIM IO Table Generator"
    else:
        app = create_main_app()
        title = "FLIMExplorer"

    # open browser after a short delay so server is up
    url = f"http://{args.host}:{args.port}"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    print(f"\nLaunching: {title}")
    print(f"URL: {url}\n")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
