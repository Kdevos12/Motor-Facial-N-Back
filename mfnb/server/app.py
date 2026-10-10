"""FastAPI application: JSON API + the static web app + locally cached CV assets."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import numpy as np
from pydantic import BaseModel, Field

from .. import __version__, assets, config
from ..face.blendshapes import DIMS as FACE_DIMS
from ..face.blendshapes import NAMES as FACE_NAMES
from ..face.expressions import FACE_CATEGORIES
from ..motion.library import CATEGORIES
from ..motion.skeleton import meta as skeleton_meta
from ..storage.db import Store
from .service import ServiceError, Trainer

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    settings: dict[str, Any] | None = None


class ProfilePatch(BaseModel):
    name: str | None = None
    settings: dict[str, Any] | None = None


class BlockIn(BaseModel):
    profile_id: int
    modality: str
    n: int | None = None
    overrides: dict[str, Any] | None = None
    seed: int | None = None


class ResponseIn(BaseModel):
    frames: list = Field(default_factory=list)
    visibility: list | None = None
    times: list[float] | None = None


class BodyCalibrationIn(BaseModel):
    frames: list


class FaceCalibrationIn(BaseModel):
    neutral: list
    prompts: dict[str, list] | None = None
    wink_left: list | None = None


class ExclusionIn(BaseModel):
    excluded: bool


def create_app(store: Store | None = None, trainer: Trainer | None = None, assets_root: Path | None = None) -> FastAPI:
    store = store or Store(config.db_path())
    trainer = trainer or Trainer(store)
    assets_root = assets_root or config.assets_dir()
    app = FastAPI(title="Motor & Facial N-Back", version=__version__)
    app.state.trainer = trainer

    @app.exception_handler(ServiceError)
    async def _service_error(_, exc: ServiceError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    def need_profile(pid: int) -> dict:
        prof = store.get_profile(pid)
        if prof is None:
            raise HTTPException(404, "profile not found")
        return prof

    @app.get("/api/meta")
    def meta():
        return {"version": __version__, "skeleton": skeleton_meta(), "motor_categories": CATEGORIES,
                "face_categories": FACE_CATEGORIES, "face_names": FACE_NAMES, "face_dims": FACE_DIMS,
                "default_settings": config.DEFAULT_SETTINGS,
                "library": {"motor": trainer.motor.stats(), "facial": trainer.face.stats()}}

    @app.get("/api/assets/status")
    def assets_status():
        return assets.status(assets_root)

    # profiles
    @app.get("/api/profiles")
    def list_profiles():
        return store.list_profiles()

    @app.post("/api/profiles")
    def create_profile(body: ProfileIn):
        return store.create_profile(body.name.strip(), body.settings)

    @app.get("/api/profiles/{pid}")
    def get_profile(pid: int):
        return need_profile(pid)

    @app.patch("/api/profiles/{pid}")
    def patch_profile(pid: int, body: ProfilePatch):
        need_profile(pid)
        return store.update_profile(pid, body.name, body.settings)

    @app.delete("/api/profiles/{pid}")
    def delete_profile(pid: int):
        need_profile(pid)
        store.delete_profile(pid)
        return {"ok": True}

    @app.put("/api/profiles/{pid}/calibration/body")
    def calibrate_body(pid: int, body: BodyCalibrationIn):
        need_profile(pid)
        return trainer.calibrate_body(pid, body.frames)

    @app.put("/api/profiles/{pid}/calibration/face")
    def calibrate_face(pid: int, body: FaceCalibrationIn):
        need_profile(pid)
        return trainer.calibrate_face(pid, body.neutral, body.prompts, body.wink_left)

    @app.put("/api/profiles/{pid}/exclusions/{modality}/{item_id}")
    def set_exclusion(pid: int, modality: str, item_id: str, body: ExclusionIn):
        need_profile(pid)
        store.set_excluded(pid, modality, item_id, body.excluded)
        return {"ok": True}

    # library
    @app.get("/api/library/motor")
    def motor_library(profile_id: int | None = None):
        excluded = store.exclusions(profile_id, "motor") if profile_id else set()
        stats = store.get_stats(profile_id, "motor") if profile_id else {}
        available = None
        if profile_id:
            available = {i.id for i in trainer.motor_pool(need_profile(profile_id), {"categories": [], "complexity": [1, 5]})}
        out = []
        for it in trainer.motor.items.values():
            d = it.meta()
            f = it.frames
            peak = int(np.argmax(np.linalg.norm(f - f[:1], axis=-1).sum(-1))) if not it.static else len(f) - 1
            d["thumb"] = np.round(f[peak], 3).tolist()
            d["excluded"] = it.id in excluded
            d["status"] = (stats.get(it.id) or {}).get("status", "new")
            d["available"] = True if available is None else it.id in available
            out.append(d)
        return out

    @app.get("/api/library/motor/{item_id}")
    def motor_item(item_id: str):
        if item_id not in trainer.motor.items:
            raise HTTPException(404, "unknown move")
        return trainer.motor_item_payload(item_id)

    @app.get("/api/library/facial")
    def face_library(profile_id: int | None = None):
        excluded = store.exclusions(profile_id, "facial") if profile_id else set()
        stats = store.get_stats(profile_id, "facial") if profile_id else {}
        out = []
        for it in trainer.face.items.values():
            d = it.meta()
            d["excluded"] = it.id in excluded
            d["status"] = (stats.get(it.id) or {}).get("status", "new")
            out.append(d)
        return out

    @app.get("/api/library/facial/{item_id}")
    def face_item(item_id: str):
        if item_id not in trainer.face.items:
            raise HTTPException(404, "unknown expression")
        return trainer.face_item_payload(item_id)

    # blocks
    @app.post("/api/blocks")
    def start_block(body: BlockIn):
        need_profile(body.profile_id)
        return trainer.start_block(body.profile_id, body.modality, body.n, body.overrides, body.seed)

    @app.get("/api/blocks/{bid}")
    def get_block(bid: int, report: bool = False):
        return trainer.block_report(bid) if report else trainer.block_payload(bid)

    @app.post("/api/blocks/{bid}/trials/{idx}/response")
    def submit(bid: int, idx: int, body: ResponseIn):
        return trainer.submit_response(bid, idx, body.model_dump())

    @app.post("/api/blocks/{bid}/finish")
    def finish(bid: int):
        return trainer.finish_block(bid)

    # progress
    @app.get("/api/dashboard/{pid}")
    def dashboard(pid: int):
        need_profile(pid)
        return trainer.dashboard(pid)

    @app.get("/api/progress/{pid}/{modality}")
    def progress(pid: int, modality: str):
        need_profile(pid)
        return trainer.item_progress(pid, modality)

    # static files: locally cached MediaPipe assets + the web app
    assets_root.mkdir(parents=True, exist_ok=True)
    app.mount("/assets", StaticFiles(directory=str(assets_root)), name="assets")
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    return app
