"""Facial scoring on real MediaPipe output: 15 people's posed photos (Yale Face Database), each scored against their
own neutral photos, as the app does with the 2-s neutral of the camera check. Guards against scoring that only
works on synthetic responses (the cause of the 'everything is wrong' bug)."""
from collections import defaultdict
from pathlib import Path

import numpy as np
import pytest

from mfnb.face.blendshapes import DIMS, from_mediapipe
from mfnb.face.expressions import get_face_library
from mfnb.face.scoring import FaceCalibration, FaceTarget, score_face, thresholds

DATA = Path(__file__).parent / "data" / "yale_blendshapes.npz"


def both(*bases):
    return {f"{b}{s}" for b in bases for s in ("Left", "Right")}


# shapes a photo of this kind may legitimately show; an item using any other shape is a wrong answer
ALLOWED = {
    "happy": both("mouthSmile", "cheekSquint", "eyeSquint", "mouthUpperUp", "mouthLowerDown", "mouthDimple") | {"jawOpen"},
    "surprised": both("browOuterUp", "eyeWide", "mouthLowerDown") | {"browInnerUp", "jawOpen", "mouthFunnel"},
    "sad": both("mouthFrown", "mouthPress", "eyeLookDown", "browDown") | {"browInnerUp", "mouthShrugLower",
                                                                          "mouthShrugUpper", "mouthPucker"},
    "sleepy": both("eyeBlink", "eyeSquint", "eyeLookDown", "cheekSquint"),
    "wink": {"eyeBlinkLeft", "eyeSquintLeft", "cheekSquintLeft", "mouthSmileLeft", "mouthUpperUpLeft", "mouthDimpleLeft"},
}
INTENDED = {"happy": {("face.smile", False), ("face.big_smile", False), ("emo.happy", False)},
            "surprised": {("emo.surprise", False), ("combo.brows_raise+jaw_open", False)},
            "sleepy": {("face.eyes_closed", False)}, "wink": {("face.wink_left", False)}, "sad": set()}


def wrong(lib, kind, iid, mirrored):
    """True when passing this item on this photo is clearly a mistake."""
    if kind == "neutral":
        return True
    if (iid, mirrored) in INTENDED[kind]:
        return False
    it = lib.get(iid)
    if kind == "wink" and it.sided and mirrored:
        return True
    dims = {DIMS[k] for k in np.nonzero(it.vector(mirrored))[0]}
    if not dims & ALLOWED[kind]:
        return True
    if dims <= ALLOWED[kind]:
        return kind != "wink" and it.sided    # e.g. a one-sided smile on a two-sided smile photo
    return True                               # uses a shape the photo does not show


@pytest.fixture(scope="module")
def results():
    z = np.load(DATA)
    scores, labels, subj = z["scores"].astype(float), z["labels"].astype(str), z["subject"]
    lib = get_face_library()
    pool = lib.filter(complexity=(1, 3), measured=set())      # the default pool of a user who never calibrated
    cands = [(it.id, m) for it in pool for m in ((False, True) if it.sided else (False,))]
    targets = {c: FaceTarget.of(lib.get(c[0]), c[1]) for c in cands}
    thr, gamma = thresholds(1.0)
    photos = {"happy": ["happy"], "surprised": ["surprised"], "sad": ["sad"], "sleepy": ["sleepy"], "wink": ["wink"],
              "neutral": ["glasses", "leftlight", "rightlight"]}
    out = []
    for s in np.unique(subj):
        def get(lbl):
            return from_mediapipe(scores[(subj == s) & (labels == lbl)])
        neutral = np.concatenate([get(lbl) for lbl in ("normal", "noglasses", "centerlight")])
        cal = FaceCalibration(neutral=np.median(neutral, 0),
                              deadzone=np.percentile(neutral, 90, 0) - np.percentile(neutral, 50, 0))
        for kind, lbls in photos.items():
            for lbl in lbls:
                frames = np.repeat(get(lbl), 12, 0)
                for c in cands:
                    ok = score_face(targets[c], frames, None, cal, threshold=thr, gamma=gamma)["target"]["score"] >= thr
                    out.append((kind, c, ok))
    return lib, out


def test_intended_expressions_pass(results):
    lib, rows = results
    per = defaultdict(list)
    for kind, c, ok in rows:
        if c in INTENDED.get(kind, ()):
            per[c[0]].append(ok)
    hits = np.mean([v for vs in per.values() for v in vs])
    assert hits >= 0.6, {k: np.mean(v) for k, v in per.items()}
    assert np.mean(per["face.smile"]) >= 0.8 and np.mean(per["face.eyes_closed"]) >= 0.9


def test_few_wrong_items_pass(results):
    lib, rows = results
    n_expr = 15 * 5
    wrong_expr = sum(ok and wrong(lib, kind, *c) for kind, c, ok in rows if kind != "neutral")
    wrong_neutral = sum(ok for kind, c, ok in rows if kind == "neutral")
    assert wrong_expr / n_expr <= 3.0
    assert wrong_neutral / 45 <= 1.5


def test_closing_both_eyes_is_not_a_wink(results):
    lib, rows = results
    assert not any(ok for kind, c, ok in rows if kind == "sleepy" and c[0] == "face.wink_left")
    assert sum(ok for kind, c, ok in rows if kind == "wink" and c == ("face.wink_left", True)) == 0
