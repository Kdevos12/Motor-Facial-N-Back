"""Entrypoint used by the Android host to run the local API server."""
from __future__ import annotations

import os
import threading
from pathlib import Path

_asset_download = {"running": False, "error": ""}


def _download_assets(root: Path) -> None:
    from . import assets

    _asset_download["running"] = True
    try:
        assets.fetch(root)
    except Exception as exc:
        _asset_download["error"] = str(exc)
        raise
    finally:
        _asset_download["running"] = False


def start(home: str, web_dir: str) -> None:
    os.environ["MFNB_HOME"] = home
    os.environ["MFNB_WEB_DIR"] = web_dir
    os.environ["MFNB_ANDROID"] = "1"

    import uvicorn

    from . import assets, config
    from .server.app import create_app

    app = create_app()
    if not assets.status(config.assets_dir())["ready"]:
        threading.Thread(target=_download_assets, args=(config.assets_dir(),), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
