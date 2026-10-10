# Motor & Facial N-Back v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local web app (Python backend + browser webcam CV) for motor and facial N-back training, with a large procedural + imported motion library, sequence-alignment scoring, adaptive N and a progress dashboard.

**Architecture:** FastAPI serves a vanilla-JS single-page app and a JSON API. The browser runs MediaPipe Pose/Face Landmarker and sends canonical landmark sequences to the server, which owns the library, block plans, scoring (subsequence DTW) and SQLite persistence.

**Tech Stack:** Python ≥ 3.10, FastAPI, uvicorn, numpy, dtaidistance, sqlite3 (stdlib), pytest/httpx; browser: ES modules, Canvas 2D, SVG, `@mediapipe/tasks-vision@0.10.35`.

**Spec:** `docs/superpowers/specs/2026-10-10-motor-facial-n-back-design.md`

## Global Constraints

- UI copy in English; 100% local (server binds 127.0.0.1; assets cached in `~/.mfnb/assets`, `MFNB_HOME` overrides).
- Space limit default 2–3 m² → default max footprint radius 0.9 m; no spinning kicks.
- Response window = `max(response_multiplier × stimulus, stimulus + 3 s)`, multiplier default 2.5, range 2.0–3.0.
- Adaptive N: accuracy ≥ 0.85 → N+1, < 0.60 → N−1 (min 1), else same; manual mode allows N ≥ 0.
- Block length default `20 + N` trials; trials `< offset` are watch-only.
- Canonical skeleton = 19 MediaPipe joints, metres, y up, x = subject's left (camera right), z toward camera.
- Mastered = ≥ 3 successes, EWMA(α = 0.3) ≥ 0.8, successes on ≥ 2 distinct days.

## Review Focus

1. Pool smaller than the no-repeat window (heavy filters / many exclusions) → plan still generated, repeats allowed, no crash (`test_plan_small_pool`).
2. Response with tracking lost (no person / low visibility) → trial marked invalid, not counted in accuracy (`test_score_invalid_when_low_visibility`).
3. Response far shorter than target (user stopped early) or all-idle → low score, no exception (`test_score_short_and_idle_response`).
4. Mirror instruction on a symmetric item → never issued (`test_plan_no_mirror_on_symmetric`).
5. First launch offline without assets → server still starts, UI shows the `mfnb fetch-assets` hint (`test_assets_status_endpoint`).

---

### Task 1: Skeleton, rig and keyframes
**Files:** `mfnb/motion/skeleton.py`, `mfnb/motion/rig.py`, `mfnb/motion/keyframes.py`, `tests/test_rig.py`
**Produces:** `JOINTS`, `MEDIAPIPE_INDEX`, `MIRROR_PERM`, `BONES`, `mirror_seq(seq)->ndarray`; `pose_to_joints(pose: PoseState, body: BodyDims)->ndarray(19,3)`; `sample_keys(keys, fps=30)->ndarray(T,19,3)` (grounded).
- [ ] Tests: bone lengths preserved for any pose; lowest foot at y≈0; `mirror_seq(mirror_seq(x)) == x`; mirrored left jab equals authored right jab.
- [ ] Implement, run `pytest tests/test_rig.py`, commit.

### Task 2: Primitive library + composer
**Files:** `mfnb/motion/primitives/*.py` (one module per category), `mfnb/motion/composer.py`, `mfnb/motion/library.py`, `tests/test_library.py`
**Produces:** `MotionItem` dataclass (id, name, category, subcategory, complexity, flexibility, body_part, sided, static, stance_based, duration_s, footprint_m, rotation_deg, source, segments, keyposes); `MotionLibrary.items`, `.get(id)`, `.frames(id)`, `.filter(profile_settings)`.
- [ ] Tests: ≥ 150 primitives, ≥ 500 items; every item has valid tags; footprint of procedural items ≤ 0.9 m; ids unique; all categories of the spec present.
- [ ] Implement, run, commit.

### Task 3: Motor scoring
**Files:** `mfnb/motion/scoring.py`, `tests/test_scoring.py`
**Produces:** `score_motor(targets: list[ndarray], response: ndarray, visibility: ndarray, *, static: bool, tolerance: Tolerance) -> MotorScore(score, valid, per_bone, keyposes)`; `calibrate_threshold(item_frames, negatives)->float`.
- [ ] Tests: identity ≈ 1; time-warped + noisy copy ≥ 0.7; different move < threshold; mirrored target detected; idle/short response low; low visibility → invalid.
- [ ] Implement, run, commit.

### Task 4: Facial library + scoring
**Files:** `mfnb/face/blendshapes.py`, `mfnb/face/expressions.py`, `mfnb/face/scoring.py`, `tests/test_face.py`
**Produces:** `BLENDSHAPES` (52 names), `mirror_bs(vec)`, `FaceItem`, `FaceLibrary`, `score_face(target, frames, calib) -> FaceScore`.
- [ ] Tests: ≥ 100 expressions, names unique; identity ≈ 1; wrong expression low; neutral baseline subtraction works.
- [ ] Implement, run, commit.

### Task 5: N-back engine, adaptation, mastery
**Files:** `mfnb/nback/plan.py`, `mfnb/nback/adaptive.py`, `mfnb/progress/mastery.py`, `tests/test_nback.py`
**Produces:** `make_plan(pool, n, n_trials, rng, *, variable_n, chirality_p, sequence_p, sided) -> list[TrialPlan]`; `next_n(n, accuracy, mode)`; `update_stats(stats, score, success, day)`, `status(stats)`.
- [ ] Tests incl. Review Focus 1 and 4; variable-N offsets within ±1 and ≥ 0; adaptation thresholds.
- [ ] Implement, run, commit.

### Task 6: Storage + API
**Files:** `mfnb/config.py`, `mfnb/storage/db.py`, `mfnb/server/*.py`, `mfnb/assets.py`, `mfnb/cli.py`, `pyproject.toml`, `tests/test_api.py`
**Produces:** REST API (`/api/profiles`, `/api/library/{motor|facial}`, `/api/blocks`, `/api/blocks/{id}/trials/{i}/response`, `/api/blocks/{id}/finish`, `/api/dashboard/{pid}`, `/api/assets/status`), `mfnb` CLI.
- [ ] Tests: full block round-trip with synthetic responses; dashboard aggregates; Review Focus 5.
- [ ] Implement, run, commit.

### Task 7: Web app — shell, vision, stick figure, motor session
**Files:** `mfnb/web/index.html`, `mfnb/web/css/app.css`, `mfnb/web/js/**`
- [ ] Profile/setting screens, camera check, stick-figure renderer (L/R colours, view modes, side inset), session runner (watch → instruction → countdown → response 2.5× → cue), block report.
- [ ] Simulation mode (`?simulate=1`) replays targets as fake landmarks for camera-less testing.
- [ ] Playwright smoke test runs one simulated block; commit.

### Task 8: Web app — facial session, dashboard, library browser
- [ ] 2D face avatar from blendshapes, face calibration, facial runner; dashboard charts; library browser with previews and exclusions; Playwright smoke; commit.

### Task 9: CMU import + bundled pack
**Files:** `mfnb/motion/importers/bvh.py`, `cmu.py`, `segment.py`, `mfnb/motion/data/cmu_pack.json.gz`, `tests/test_import.py`
- [ ] Tests: BVH fixture parses; FK matches expected; segmentation and footprint filter.
- [ ] Build pack from curated CMU subjects; library loads it; commit.

### Task 10: Docs
- [ ] README (install, run, camera setup, open-source credits & licences); final full test run; push.
