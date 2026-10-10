"""Command line: `mfnb` starts the app; sub-commands manage assets and the library."""
from __future__ import annotations

import argparse
import sys
import threading
import webbrowser

from . import __version__, assets, config


def cmd_serve(args) -> int:
    import uvicorn

    from .server.app import create_app

    st = assets.status(config.assets_dir())
    if not st["ready"] and not args.offline:
        print("First launch: downloading MediaPipe (about 25 MB, one time)...")
        try:
            assets.fetch(config.assets_dir(), progress=print)
        except Exception as exc:  # keep going: the UI explains how to fix it
            print(f"Could not download the computer-vision assets: {exc}\n"
                  "The app will start, but the camera features need `mfnb fetch-assets` once online.")
    print("Building the move library...")
    app = create_app()
    url = f"http://{args.host}:{args.port}/"
    print(f"Motor & Facial N-Back {__version__} running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def cmd_fetch_assets(_args) -> int:
    st = assets.fetch(config.assets_dir(), progress=print)
    print("Assets ready." if st["ready"] else f"Missing: {st['missing']}")
    return 0 if st["ready"] else 1


def cmd_library(_args) -> int:
    from .face.expressions import get_face_library
    from .motion.library import get_library
    lib = get_library()
    print("Motor library:", lib.stats())
    print("Facial library:", get_face_library().stats())
    return 0


def cmd_calibrate(_args) -> int:
    from .motion.calibration import calibrate, save_calibration
    from .motion.library import get_library
    lib = get_library()
    data = calibrate(list(lib.items.values()), progress=lambda k, n: print(f"  {k}/{n}"))
    save_calibration(data)
    print(f"Calibrated {len(data)} items.")
    return 0


def cmd_import_cmu(args) -> int:
    from .motion.importers.cmu import import_cmu
    return import_cmu(args)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mfnb", description="Motor & Facial N-Back training app")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("serve", help="start the app (default)")
    for target in (p, s):
        target.add_argument("--host", default="127.0.0.1")
        target.add_argument("--port", type=int, default=config.DEFAULT_PORT)
        target.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
        target.add_argument("--offline", action="store_true", help="do not try to download assets")
    sub.add_parser("fetch-assets", help="download MediaPipe JS/WASM and models")
    sub.add_parser("library", help="print library statistics")
    sub.add_parser("calibrate", help="recompute per-move acceptance thresholds")
    c = sub.add_parser("import-cmu", help="import clips from the CMU motion capture database (BVH)")
    c.add_argument("--source", help="folder with CMU BVH files (default: download the curated subjects)")
    c.add_argument("--subjects", help="comma-separated subject numbers (default: curated list)")
    c.add_argument("--out", help="pack file to write (default: bundled pack)")
    args = p.parse_args(argv)
    handlers = {None: cmd_serve, "serve": cmd_serve, "fetch-assets": cmd_fetch_assets, "library": cmd_library,
                "calibrate": cmd_calibrate, "import-cmu": cmd_import_cmu}
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
