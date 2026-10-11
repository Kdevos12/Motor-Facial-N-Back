# Motor & Facial N-Back

Webcam-based working-memory training, 100% local:

- **Motor N-Back**: a 3D stick figure shows a move; you perform the move shown **N trials
  earlier**. It trains the action-observation (mirror) system and motor working memory.
- **Facial N-Back**: same game with facial expressions shown on a stylised face.

Each block adapts N to your accuracy (or you choose N yourself). A dashboard tracks your
N, your accuracy and the moves and expressions you have mastered.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
mfnb                                                     # opens http://127.0.0.1:8765
```

To update later, from the folder where you cloned it (your profiles and progress in `~/.mfnb` are kept):

```bash
git pull
source .venv/bin/activate && pip install -e .     # only needed when dependencies change; harmless otherwise
mfnb                                              # or: mfnb --port 8790 if 8765 is taken
```

Then reload the page with Ctrl+Shift+R so the browser takes the new version.

On first launch the app downloads MediaPipe (about 25 MB, once) into `~/.mfnb/assets`.
After that it works offline. Everything (profiles, progress) stays in `~/.mfnb`; set
`MFNB_HOME` to use another folder.

No camera handy? Open `http://127.0.0.1:8765/?simulate` to run the **demo mode**: a
simulated user performs the moves, so you can see the full loop.

### Camera setup (motor)

- Whole body in view (feet included): about **2.8 m** from a laptop webcam, **1.7 m** from a
  phone in portrait. Camera around hip height. Clear about 1.5 × 1.5 m (the library is
  filtered for 2–3 m² by default).
- Camera too close, or training seated? Choose **Upper body** framing (Settings or the
  training page): head to mid-thigh in view, only arm and trunk moves, legs not scored.
- **Use your phone as the camera, over Wi-Fi, no cable**: install a camera app on the phone
  (IP Webcam on Android), then Settings → Cameras → *Phone over Wi-Fi* and type the address
  it shows. On a residence Wi-Fi that keeps devices apart, connect the computer to the
  phone's hotspot and press *Find my phone*. No driver needed. A USB cable (scrcpy) also
  works. See [the guide](mfnb/web/help/phone-camera.md), also in the app. Each game can use
  its own camera (e.g. the phone for moves, the laptop webcam for faces), with rotation for
  a phone mounted sideways.
- **Face the screen**, not the camera. The camera may be off to one side (best within 30°,
  up to 45°): each motor block starts with 2 s standing still facing the screen, which
  measures the camera's angle, and scoring corrects for it.
- The first time you use a camera, the app asks you to raise your right hand (or turn
  your head to the left) to check that its picture is not mirrored.
- Even, front lighting. The app checks that you are in frame before each block.

## How a block works

1. **Watch** — the stick figure plays a move (left limbs blue, right limbs orange).
2. The first N trials are watch-only. After that, each trial shows a new move **and** asks
   you to perform the move from N trials back (`2-back`, or `copy it now` when N = 0).
3. **Perform** — you get 2–3× the move's duration (default 2.5×, at least +3 s).
4. A discreet colour flash tells you how it went (green / amber / red); the detailed report
   with side-by-side replay comes at the end of the block.
5. Adaptive N: ≥ 85% correct → N + 1, < 60% → N − 1.

Optional twists (motor): **variable N** (N ± 1 on some trials), **switch sides**
(perform the mirror image), and an experimental **sequence mode** ("do N−2 then N").

## The move library

| Source | Items | Notes |
|---|---|---|
| Procedural (bundled) | 626 (263 primitives + combos) | static postures, boxing, **evasion & defense**, kicks & knees, **taekwondo**, karate, **shadow grappling** (judo uchikomi, wrestling, clinch), tai chi & qigong, dance, fitness, everyday & sports |
| CMU mocap (bundled) | 319 clips | tai chi, shadow boxing, karate kata, kicks, blocks, Indian dance, Charleston, stretching, sports |
| `mfnb import-dataset bandai` | ~94 clips | Bandai Namco Research Motion Dataset (styled gestures, punch, kick, dance) |
| `mfnb import-dataset lafan1` | ~130 clips | Ubisoft LaFAN1 (dance, fight) |
| `mfnb import-bvh FILES --category dance` | yours | any BVH (Mixamo, Rokoko, CMU, …), joints recognised automatically |

Every item is tagged with category, composition complexity (1–5), lower-body flexibility
(low/medium/high), footprint, reach and rotation. Your profile filters by flexibility,
space and "turning your back to the camera". Any item can be excluded from training.

The non-commercial datasets are imported **on your machine** and are not redistributed
(see licences below). After an import, run `mfnb calibrate` and restart the app.

The facial library has 295 expressions: emotions, upper/lower-face actions, gaze,
asymmetric expressions and combinations.

## Individual differences

- **Body calibration**: measures your proportions.
- **Face calibration** (about a minute): measures how far each facial movement goes on
  your face and unlocks the mouth movements the tracker can see on it. Your resting face
  is also recorded at the start of every facial block.
- **Flexibility & space**: control which moves you are given and how tolerant the scoring
  is with leg angles.
- **Stance & view**: orthodox or southpaw stance; the stimulus can be shown as a mirror,
  facing you, or from behind. You can also turn the figure and add a side-view inset.
- **Framing & camera**: whole body or upper body; one camera per game; the camera's real
  angle is measured and corrected at the start of each motor block.
- **Pacing & tolerance**: stimulus speed, response window (2–3×), pause between trials,
  strictness, and how many times each stimulus is shown.

## How scoring works

The browser runs MediaPipe Pose/Face Landmarker and sends landmark sequences to the local
Python server.

- **Motor**: bone directions (body-size invariant; depth down-weighted) are aligned with
  the target by **subsequence DTW** (`dtaidistance`). Idle time and tempo don't matter.
  The score combines accuracy along the alignment with how well every **key pose** was
  reproduced. Each move has its own acceptance threshold, calibrated against near-miss
  moves (an idea from the Jackknife recogniser). Recent other moves are scored as **lures**:
  doing the wrong item from the buffer is reported as such. The response is first rotated
  from the camera's viewpoint to the screen's (measured at the start of the block, plus
  your heading in the relaxed moment after GO); neither correction looks at the target, so
  a move without its turn or on the wrong side is not rotated into a pass. Upper-body
  framing scores only the arms and trunk, with its own thresholds.
- **Facial**: MediaPipe blendshapes, read from your own resting face. Over the best 0.5 s,
  an expression passes when it resembles what the tracker reports for that expression on
  you (similarity ≥ 0.60), **every key part** moved at least 35% of the way to your maximum
  (so a combination cannot pass on one half), and one-sided parts (a wink, one eyebrow)
  moved more on their side. Strictness scales both. Shapes MediaPipe never outputs only
  shape the avatar. Checked on real MediaPipe output of 15 people's posed photos
  (`tests/test_face_real.py`).

## Development

```bash
pip install -e '.[dev]'
pytest                                  # unit + API tests
mfnb serve --no-browser &               # then, with Playwright installed:
python tests/e2e/smoke.py               # runs a motor and a facial block in demo mode
mfnb calibrate --bundled                # recompute bundled thresholds after editing moves
mfnb import-cmu                         # rebuild the bundled CMU pack
```

Code map: `mfnb/motion` (rig, primitives, library, scoring, importers), `mfnb/face`,
`mfnb/nback` (block plans, adaptation), `mfnb/progress`, `mfnb/storage` (SQLite),
`mfnb/server` (FastAPI), `mfnb/web` (vanilla JS front end). Design notes are in `docs/`.

## Credits & licences

- Code: MIT (see `LICENSE`).
- [MediaPipe](https://github.com/google-ai-edge/mediapipe) Tasks Vision and models, Apache-2.0.
- [CMU Graphics Lab Motion Capture Database](http://mocap.cs.cmu.edu). The data is free to
  use but may not be resold. BVH files come from the MIT-licensed
  [adventuring/mocap](https://github.com/adventuring/mocap) mirror. Bundled in
  `mfnb/motion/data/cmu.pack.json.gz`.
- Imported locally, not bundled:
  - [Bandai Namco Research Motion Dataset](https://github.com/BandaiNamcoResearchInc/Bandai-Namco-Research-Motiondataset)
    (CC BY-NC 4.0).
  - [Ubisoft La Forge LaFAN1](https://github.com/ubisoft/ubisoft-laforge-animation-dataset)
    (CC BY-NC-ND 4.0).
- [Yale Face Database](http://cvc.cs.yale.edu/cvc/projects/yalefaces/yalefaces.html)
  (Belhumeur, Hespanha & Kriegman, 1997): MediaPipe blendshape scores of its photos (no
  images) in `tests/data/` for the facial regression test.
- Ideas: [Mime Flow](https://github.com/lguibr/Mimeflow) (MIT; weighted bone-direction
  features); Jackknife, Taranta et al., CHI 2017 (per-template rejection thresholds,
  reimplemented from the paper); A-MAL, ICCVW 2019 (key poses);
  [dtaidistance](https://github.com/wannesm/dtaidistance) (Apache-2.0).
