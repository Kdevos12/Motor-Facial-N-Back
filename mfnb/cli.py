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


def cmd_calibrate(args) -> int:
    from .motion.calibration import CALIBRATION_FILE, calibrate_all, save_calibration, user_calibration_file
    from .motion.library import get_library
    lib = get_library()
    items = [i for i in lib.items.values() if args.bundled or i.source not in ("procedural", "cmu")]
    if not items:
        print("Nothing to calibrate: bundled moves are already calibrated (use --bundled to redo them).")
        return 0
    data = calibrate_all(items, progress=lambda k, n: print(f"  {k}/{n}"), pool=list(lib.items.values()))
    path = CALIBRATION_FILE if args.bundled else user_calibration_file()
    save_calibration(data, path)
    print(f"Calibrated {len(data)} items -> {path}")
    return 0


def cmd_import_dataset(args) -> int:
    from .motion.importers.datasets import RECIPES, import_dataset
    r = RECIPES[args.name]
    print(f"Importing {r.title} (licence: {r.licence}) for personal use...")
    import_dataset(args.name, config.home() / "cache")
    print("Run `mfnb calibrate` to compute acceptance thresholds for the new clips, then restart the app.")
    return 0


def cmd_import_bvh(args) -> int:
    from pathlib import Path

    from .motion.importers.datasets import import_files
    from .motion.importers.pack import user_pack_dir
    files = []
    for f in args.files:
        p = Path(f)
        files += sorted(p.glob("**/*.bvh")) if p.is_dir() else [p]
    def classify(path):
        return args.category, args.subcategory or "imported", f"{args.name or path.stem}", args.max_clips
    out = user_pack_dir() / f"{args.pack}.pack.json.gz"
    import_files(files, classify, args.pack, args.licence, args.pack, out)
    print("Run `mfnb calibrate`, then restart the app.")
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
    cal = sub.add_parser("calibrate", help="compute per-move acceptance thresholds for imported clips")
    cal.add_argument("--bundled", action="store_true", help="recompute the bundled library's thresholds (developers)")
    ds = sub.add_parser("import-dataset", help="import a large open mocap dataset locally (personal use)")
    ds.add_argument("name", choices=["bandai", "lafan1"])
    ib = sub.add_parser("import-bvh", help="import your own BVH files (any common rig)")
    ib.add_argument("files", nargs="+", help="BVH files or folders")
    ib.add_argument("--category", required=True, help="library category, e.g. 'dance' or 'kicks'")
    ib.add_argument("--subcategory", default=None)
    ib.add_argument("--name", default=None, help="display name (default: file name)")
    ib.add_argument("--pack", default="my-moves", help="pack name in ~/.mfnb/packs")
    ib.add_argument("--licence", default="own recording")
    ib.add_argument("--max-clips", type=int, default=12)
    c = sub.add_parser("import-cmu", help="import clips from the CMU motion capture database (BVH)")
    c.add_argument("--source", help="folder with CMU BVH files (default: download the curated subjects)")
    c.add_argument("--subjects", help="comma-separated subject numbers (default: curated list)")
    c.add_argument("--out", help="pack file to write (default: bundled pack)")
    args = p.parse_args(argv)
    handlers = {None: cmd_serve, "serve": cmd_serve, "fetch-assets": cmd_fetch_assets, "library": cmd_library,
                "calibrate": cmd_calibrate, "import-cmu": cmd_import_cmu, "import-dataset": cmd_import_dataset,
                "import-bvh": cmd_import_bvh}
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
