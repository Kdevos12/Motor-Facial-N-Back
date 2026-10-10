# Motor & Facial N-Back — Design Spec (v1)

Date: 2026-10-10 · Status: draft for review

## 1. Intent

A local, user-friendly training app with two webcam-based working-memory games:

- **Motor N-Back** — a stick figure shows a movement; you must *perform* the movement shown
  N trials earlier. Goals: (1) train the action-observation / mirror system, (2) train motor
  working memory. Optional twists: variable N (±1 per trial), random chirality instruction
  ("switch sides"), and an experimental sequence mode ("do N-2 then N").
- **Facial N-Back** — same paradigm with facial expressions (no twists in v1).

Plus a **dashboard** (mastered moves/expressions, N progression, accuracy) and a **library
browser**. Not a research tool (no study protocol, no export-first design); English UI.

### Constraints stated by the user
- Python-first, web UI, 100% local.
- Training space is ~2–3 m²: no long-range footwork, no high spinning kicks.
- Large, varied library (variety drives transfer), organised by category/sub-category,
  composition complexity, and lower-body flexibility requirement.
- Individual differences must be accounted for.
- The response window must be **2–3× the stimulus duration** (default 2.5×).

### Decisions taken (Q&A)
| Topic | Decision |
|---|---|
| CV location | Hybrid: browser runs webcam + MediaPipe (JS/WASM); Python (FastAPI) runs library, N-back engine, scoring, persistence |
| Motor stimulus | Animated 3D stick figure rendered from motion data |
| Library sources | Procedural keyframe primitives + automatic composition; open mocap import (CMU) |
| Trial flow | Watch then perform; first N trials are watch-only |
| Individual differences | Body calibration, flexibility/space profile, laterality & view, pacing & tolerance |
| Feedback | Discreet per-trial colour cue; detailed report at end of block |
| N progression | User preference: adaptive by block (default) or manual |
| Face stimulus | Stylised 2D face driven by the 52 MediaPipe blendshapes |

## 2. Architecture

```
Browser (localhost)                         Python (FastAPI, 127.0.0.1)
┌──────────────────────────────┐            ┌───────────────────────────────────┐
│ webcam → MediaPipe Pose/Face │  REST/JSON │ library (motor + facial)          │
│ stick-figure + face renderer │ ─────────► │ N-back engine (plans, adaptation) │
│ session runner (timing)      │ ◄───────── │ scoring (DTW / blendshape sim.)   │
│ dashboard, library, settings │            │ progress & mastery (SQLite)       │
└──────────────────────────────┘            └───────────────────────────────────┘
```

- Frontend: vanilla ES modules, no build step, served by FastAPI. Hand-written SVG charts.
- MediaPipe Tasks Vision (pinned `@mediapipe/tasks-vision@0.10.35`) + `pose_landmarker_full`
  and `face_landmarker` models are downloaded once into the data dir (`~/.mfnb/assets`) on
  first launch (or `mfnb fetch-assets`), then served locally. Fully offline afterwards.
- Persistence: SQLite (`~/.mfnb/mfnb.db`, override with `MFNB_HOME`).
- Launch: `pip install -e .` then `mfnb` → starts server, opens the browser.

### Python package layout (`mfnb/`)
| Module | Responsibility |
|---|---|
| `motion/skeleton.py` | Canonical 19-joint skeleton, bones, L/R mirror map, MediaPipe index map |
| `motion/rig.py` | Direction-based forward kinematics: pose spec → 3D joints; auto-grounding |
| `motion/keyframes.py` | Keyframed move → sampled 30 fps sequence (slerp + easing) |
| `motion/primitives/*.py` | Authored primitives per category (data, small DSL) |
| `motion/composer.py` | Combos from primitives; complexity/footprint/flexibility tagging |
| `motion/importers/` | BVH parser, CMU converter, segmentation, footprint filter |
| `motion/scoring.py` | Normalisation, bone-direction features, DTW, tolerance, lure detection |
| `face/blendshapes.py` | 52 names, mirror map, regions |
| `face/expressions.py` | Expression atoms + procedural combinations |
| `face/scoring.py` | Calibrated blendshape similarity |
| `nback/plan.py` | Block plan generation (items, offsets, chirality, sequence mode) |
| `nback/adaptive.py` | Block-level N adaptation |
| `progress/` | Mastery model, dashboard aggregation |
| `storage/db.py` | SQLite schema + queries |
| `server/` | FastAPI app + routes |
| `cli.py` | `mfnb` (serve), `fetch-assets`, `import-cmu`, `library-stats` |

## 3. Motion representation

**Canonical skeleton** (19 joints, a MediaPipe subset): nose, ears, shoulders, elbows, wrists,
index tips, hips, knees, ankles, foot tips. Frame: metres, y up, x = camera-right (= subject's
left when facing the camera), z toward the camera. MediaPipe world landmarks map as
`(x, -y, -z)`.

**Authoring (procedural)** — a pose is a set of *bone directions* in body-local frames
(`fwd`, `up`, `out`, … or vectors) plus scalars (torso lean/side-bend/twist, pelvis yaw,
root offset). FK chains bone lengths along directions; the figure is auto-grounded (lowest
foot on the floor), which gives squats, lunges and kicks for free. Keyframes are interpolated
with slerp + smoothstep. Primitives are authored once; the mirror (other side) is computed.

**Composition** — primitives sharing a "home" pose (guard, neutral stance, horse stance…)
are chained into combos of 2–4 segments → hundreds of items.

**Tags per item**: `category`, `subcategory`, `complexity` 1–5 (1 = static posture,
2 = single movement, 3 = 2-part combo or simultaneous arm+leg, 4 = 3-part, 5 = 4+ part),
`flexibility` low/medium/high, `footprint_m` (computed), `rotation_deg` (computed), `duration_s`, `body_part`
(upper/lower/full), `sided` (has a meaningful mirror), `source` (procedural/cmu).

**Categories (v1 target ≥ 150 primitives, ≥ 500 items with combos)**:

| Category | Sub-categories / examples |
|---|---|
| Static postures | yoga, martial stances, gestures, balance holds |
| Boxing | jab, cross, hooks, uppercuts, body shots, elbows; combos |
| Evasion & defense | slips, rolls (bob & weave), pull-back, duck, shoulder roll, parries, catch; slip-and-counter combos |
| Kicks & knees | front, push (teep), low/mid roundhouse, side, knees, checks — no spinning kicks |
| Taekwondo | stances (ap/dwit kubi, juchum seogi, beom seogi), makki blocks, jireugi punches, sonnal strikes, ap/dollyo/yeop/naeryo/bandal/mireo chagi, in-place poomsae fragments |
| Karate | uke blocks, zuki punches, geri kicks, kata fragments |
| Shadow grappling | solo mimicry of partner techniques: judo uchikomi (seoi nage, osoto gari, o goshi, uchi mata entries, kuzushi pulls), wrestling (level change, short penetration step, sprawl, snap-down, arm drag, pummeling), clinch (collar tie, Thai plum + knees, body lock, frames) |
| Tai chi & qigong | Ba Duan Jin, cloud hands, single whip, white crane, brush knee… |
| Dance | in-place moves, arm patterns, ballet port de bras, pliés |
| Fitness | squats, lunges, raises, twists, mobility drills |
| Everyday & sports | gestures, throws, swings (golf, tennis, baseball) |

Kick height and flexibility are tagged (high kicks only appear for `flexibility = high`).
Moves that turn the back to the camera (e.g. a full seoi nage entry) carry `rotation_deg`;
in-place adaptations (≤ 90° turn) are the default because monocular pose tracking confuses
left/right when the user faces away. A profile switch allows the full-turn versions.

No open mocap dataset was found for taekwondo, boxing defense or standing grappling
(taekwondo poomsae datasets exist in papers but are not released; grappling data is either
two-person research data without a clear licence, e.g. Harmony4D, or commercial). These
categories are therefore authored procedurally; the importer remains open for any future
BVH source.

**Open-data import** — CMU Graphics Lab mocap (BVH via the MIT-licensed `adventuring/mocap`
GitHub mirror; CMU terms: free use, no resale). Pipeline: parse BVH → canonical joints →
30 fps → segment at rest pauses (fallback 4 s windows) → keep 1.5–6 s clips whose footprint
fits the space limit → re-centre/face camera → tag from a curated subject→category table.
Converted clips ship in the repo as a compact pack; the importer is a CLI for adding more.

## 4. N-back engine

- **Block** = `20 + N` trials by default (configurable). Trials `0..N-1` are watch-only.
- **Trial** (motor): stimulus (`duration × playback speed`, played once, optional repeat) →
  instruction banner → "3-2-1" → **response window = max(2.5 × stimulus, stimulus + 3 s)**
  (multiplier 2–3× configurable) → discreet colour cue → inter-trial pause.
- **Instructions per trial** (a list of targets): standard `[offset=N]`; variable-N
  `offset = N + δ`, δ ∈ {−1, 0, +1}; chirality `mirror=true` with probability p; sequence
  mode `[offset=N-2, offset=N]` (experimental, off by default).
- **Item sampling**: from the profile-filtered pool, no repeats within the N+2 window.
- **Adaptation** (if preference = adaptive): accuracy ≥ 85% → N+1; < 60% → N−1 (min 1);
  else stay. Manual mode: user picks N (N=0 = pure imitation practice).
- Facial uses the same engine with twists disabled.

## 5. Scoring

**Motor** (server, numpy):
1. Client sends the response window's canonical joints + visibility + timestamps.
2. Features per frame: unit bone directions (≈16 bones; head/hands/feet down-weighted;
   z down-weighted because monocular depth is noisy; low visibility → low weight). Bone
   directions are body-size invariant (body calibration feeds proportions to the renderer
   and normalises pelvis displacement by leg length).
3. Trim idle time by motion energy; resample to a fixed length; DTW with a Sakoe-Chiba band;
   static postures use the best sustained 0.8 s hold instead.
4. Error → score in [0, 1] using per-bone angular tolerances; lower-body tolerance is
   scaled by the flexibility profile; global strictness slider.
5. **Lure check**: the response is also scored against the other recent stimuli; the trial is
   correct if the target score ≥ threshold (default 0.7) and the target is the best match
   (±0.03). The report says "you performed trial t-1's move" when applicable.

**Facial**: calibrated blendshapes `clip((r − neutral) × gain, 0, 1)`; best 0.5 s window;
score = 0.7 × cosine + 0.3 × (1 − mean abs diff on active dims). Calibration = 3 s neutral
+ 5 maximal prompts (gains) + a left-wink check to verify L/R mapping.

## 6. Individual differences (profile)

- **Body calibration**: 3 s neutral stance → bone lengths (renderer proportions, leg length).
- **Flexibility & space**: low/medium/high lower-body flexibility filters items and scales
  leg tolerance; space limit filters by footprint; "allow turning away from camera" (off by
  default) unlocks full-turn techniques.
- **Laterality & view**: dominant side / guard (orthodox/southpaw, which flips stance-based
  items), stimulus view = mirror (default) / facing / from behind; L/R limb colour coding.
- **Pacing & tolerance**: playback speed, response multiplier (2–3×), inter-trial pause,
  strictness, block length, show move names (off by default), self-view during response.
- **Exclusions**: any item can be disabled (injury, dislike).
- Multiple local profiles.

## 7. Progress & dashboard

- Per item and profile: attempts, successes, EWMA score, last seen. Status: *new* →
  *learning* (≥ 1 success) → *mastered* (≥ 3 successes, EWMA ≥ 0.8, seen in ≥ 2 days).
- Dashboard: KPIs (sessions, minutes, current/best N per modality, streak), N over time,
  accuracy per block, mastery by category, mastered item gallery (animated thumbnails),
  recent blocks. Block report: per-trial target vs. response replay, per-bone error.

## 8. Error handling

- Camera denied / missing → clear screen with retry; body not fully in frame → pre-block
  check blocks start; tracking lost during a response → trial marked *invalid* (not counted).
- Assets missing and offline → actionable message with the `mfnb fetch-assets` command.
- Server-side validation via pydantic; client shows API errors inline.

## 9. Testing

- pytest: rig (bone lengths preserved, grounding), keyframe interpolation, mirror symmetry,
  library integrity (all items valid, tags present, footprint within limits), scoring
  (identity ≈ 1, mirror swap detected, noise robustness, lure detection, time warping),
  plan generation (offsets, no-repeat window, variable N bounds), adaptation, mastery,
  BVH parsing on a fixture, API round-trips (TestClient).
- Browser: Playwright smoke test (pages load, MediaPipe initialises, a block runs with
  scripted fake landmarks).

## 10. Out of scope (v1)

Recording studio, video stimuli, multi-person, cloud sync, study/export features, facial
twists (variable N, chirality, sequences).
