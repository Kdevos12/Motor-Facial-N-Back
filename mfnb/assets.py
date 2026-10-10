"""Download (once) and serve the browser-side computer-vision assets.

MediaPipe Tasks Vision (JS + WASM) comes from the npm registry, the models from Google's
model storage. Everything is pinned and checked by SHA-256, then served from the local data
directory, so the app runs offline afterwards.
"""
from __future__ import annotations

import hashlib
import io
import shutil
import tarfile
import urllib.request
from pathlib import Path

TASKS_VISION_VERSION = "0.10.35"
TASKS_VISION_URL = f"https://registry.npmjs.org/@mediapipe/tasks-vision/-/tasks-vision-{TASKS_VISION_VERSION}.tgz"
TASKS_VISION_SHA256 = "84597a25e13d123b5f4cbe768bb72e97a2c28c7a465f0ace287d8cbe5246bff0"
MODELS = {
    "pose_landmarker_full.task": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/"
        "pose_landmarker_full.task",
        "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1"),
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"),
}
BUNDLE_FILES = ["vision_bundle.mjs", "wasm/vision_wasm_internal.js", "wasm/vision_wasm_internal.wasm",
                "wasm/vision_wasm_nosimd_internal.js", "wasm/vision_wasm_nosimd_internal.wasm"]


def expected_files(root: Path) -> list[Path]:
    return [root / "tasks-vision" / f for f in BUNDLE_FILES] + [root / "models" / m for m in MODELS]


def status(root: Path) -> dict:
    missing = [str(p.relative_to(root)) for p in expected_files(root) if not p.exists()]
    return {"ready": not missing, "missing": missing, "version": TASKS_VISION_VERSION,
            "hint": "Run `mfnb fetch-assets` while online (about 25 MB, one time)." if missing else ""}


def _download(url: str, sha256: str, progress=None) -> bytes:
    if progress:
        progress(f"Downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256:
        raise RuntimeError(f"checksum mismatch for {url}: {digest}")
    return data


def fetch(root: Path, progress=None) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    tv = root / "tasks-vision"
    if not all((tv / f).exists() for f in BUNDLE_FILES):
        data = _download(TASKS_VISION_URL, TASKS_VISION_SHA256, progress)
        tmp = root / "tasks-vision.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for f in BUNDLE_FILES:
                member = tar.getmember(f"package/{f}")
                dest = tmp / f
                dest.parent.mkdir(parents=True, exist_ok=True)
                src = tar.extractfile(member)
                if src is None:
                    raise RuntimeError(f"missing {f} in package")
                dest.write_bytes(src.read())
        shutil.rmtree(tv, ignore_errors=True)
        tmp.rename(tv)
    models = root / "models"
    models.mkdir(exist_ok=True)
    for name, (url, sha) in MODELS.items():
        if not (models / name).exists():
            (models / name).write_bytes(_download(url, sha, progress))
    return status(root)
