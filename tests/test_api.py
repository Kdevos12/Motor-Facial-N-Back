import numpy as np
import pytest
from fastapi.testclient import TestClient

from mfnb.server.app import create_app
from mfnb.sim import synth_face_neutral, synth_face_response, synth_response
from mfnb.storage.db import Store


@pytest.fixture()
def client(tmp_path):
    app = create_app(store=Store(tmp_path / "t.db"), assets_root=tmp_path / "assets")
    return TestClient(app)


def make_profile(client, **settings):
    r = client.post("/api/profiles", json={"name": "Alex", "settings": settings or None})
    assert r.status_code == 200
    return r.json()


def test_meta_and_assets_status(client):
    meta = client.get("/api/meta").json()
    assert meta["skeleton"]["joints"][0] == "nose" and len(meta["face_dims"]) == 51
    st = client.get("/api/assets/status").json()
    assert st["ready"] is False and "fetch-assets" in st["hint"]
    assert client.get("/").status_code == 200


def test_profile_settings_merge(client):
    p = make_profile(client)
    assert p["settings"]["response_multiplier"] == 2.5
    p2 = client.patch(f"/api/profiles/{p['id']}", json={"settings": {"motor": {"n": 3}, "flexibility": "low"}}).json()
    assert p2["settings"]["motor"]["n"] == 3 and p2["settings"]["motor"]["block_base"] == 20
    assert p2["settings"]["flexibility"] == "low"


def run_motor_block(client, pid, n, good=True, seed=0):
    block = client.post("/api/blocks", json={"profile_id": pid, "modality": "motor", "n": n, "seed": seed}).json()
    rng = np.random.default_rng(seed)
    results = []
    for tr in block["trials"]:
        if tr["watch_only"]:
            continue
        tgt = tr["targets"][0]
        item = block["items"][tgt["item_id"]]
        frames = np.array(item["frames"])
        if tgt["effective_mirror"]:
            from mfnb.motion.skeleton import mirror_seq
            frames = mirror_seq(frames)
        if not good:
            frames = np.array(block["items"][tr["item_id"]]["frames"]) if tr["item_id"] != tgt["item_id"] else frames[:1].repeat(60, 0)
        f, t = synth_response(frames, rng, style_m=0.02)
        r = client.post(f"/api/blocks/{block['block_id']}/trials/{tr['index']}/response",
                        json={"frames": f.tolist(), "times": t.tolist(), "visibility": np.ones(f.shape[:2]).tolist()})
        assert r.status_code == 200, r.text
        results.append(r.json())
    summary = client.post(f"/api/blocks/{block['block_id']}/finish").json()
    return block, results, summary


def test_full_motor_block_round_trip(client):
    p = make_profile(client)
    block, results, summary = run_motor_block(client, p["id"], 2)
    assert len(block["trials"]) == 22 and len(results) == 20
    assert all(r["valid"] for r in results)
    assert summary["accuracy"] >= 0.85 and summary["next_n"] == 3
    assert client.get(f"/api/profiles/{p['id']}").json()["settings"]["motor"]["n"] == 3
    report = client.get(f"/api/blocks/{block['block_id']}?report=true").json()
    assert len(report["trials_results"]) == 20 and "response" in report["trials_results"][0]


def test_bad_block_lowers_n(client):
    p = make_profile(client)
    _, results, summary = run_motor_block(client, p["id"], 2, good=False, seed=1)
    assert summary["accuracy"] < 0.6 and summary["next_n"] == 1


def test_manual_mode_keeps_n(client):
    p = make_profile(client, n_mode="manual")
    _, _, summary = run_motor_block(client, p["id"], 2)
    assert summary["next_n"] == 2


def test_response_validation(client):
    p = make_profile(client)
    block = client.post("/api/blocks", json={"profile_id": p["id"], "modality": "motor", "n": 1, "seed": 3}).json()
    r = client.post(f"/api/blocks/{block['block_id']}/trials/0/response", json={"frames": []})
    assert r.status_code == 400  # watch-only trial
    r = client.post(f"/api/blocks/{block['block_id']}/trials/1/response", json={"frames": [[1, 2]]})
    assert r.json()["valid"] is False


def test_too_narrow_filters_rejected(client):
    p = make_profile(client)
    r = client.post("/api/blocks", json={"profile_id": p["id"], "modality": "motor",
                                         "overrides": {"categories": ["nope"]}})
    assert r.status_code == 400 and "filters" in r.json()["detail"]


def test_facial_block_and_dashboard(client):
    p = make_profile(client)
    rng = np.random.default_rng(0)
    block = client.post("/api/blocks", json={"profile_id": p["id"], "modality": "facial", "n": 1, "seed": 5,
                                             "face_neutral": synth_face_neutral(rng).tolist()}).json()
    assert all(not i.startswith("face.jaw_left") for i in block["items"])    # needs a face calibration first
    from mfnb.face.blendshapes import mirror_vec, vec
    for tr in block["trials"]:
        if tr["watch_only"]:
            continue
        tgt = tr["targets"][0]
        v = vec(block["items"][tgt["item_id"]]["target"])
        if tgt["effective_mirror"]:
            v = mirror_vec(v)
        f, t = synth_face_response(v, rng)
        res = client.post(f"/api/blocks/{block['block_id']}/trials/{tr['index']}/response",
                          json={"frames": f.tolist(), "times": t.tolist()}).json()
        assert res["valid"]
    summary = client.post(f"/api/blocks/{block['block_id']}/finish").json()
    assert summary["accuracy"] >= 0.8
    dash = client.get(f"/api/dashboard/{p['id']}").json()
    assert dash["totals"]["blocks"] == 1 and dash["totals"]["streak"] == 1
    assert dash["modalities"]["facial"]["history"][0]["accuracy"] == summary["accuracy"]
    assert dash["modalities"]["facial"]["counts"]["learning"] >= 1


def test_body_and_face_calibration(client):
    p = make_profile(client)
    from mfnb.motion.library import get_library
    frames = get_library().get("pose.t_pose").frames[-20:]
    dims = client.put(f"/api/profiles/{p['id']}/calibration/body", json={"frames": frames.tolist()}).json()
    assert dims["upper_arm"] == pytest.approx(0.29, abs=0.01)
    from mfnb.face.blendshapes import IDX
    rng = np.random.default_rng(1)
    neutral = synth_face_neutral(rng)
    wink = neutral.copy()
    wink[:, IDX["eyeBlinkRight"]] = 0.7   # a mirrored camera feed: the left wink shows up on the right eye
    jaw = neutral.copy()
    jaw[:, IDX["jawRight"]] = 0.35        # same feed: the jaw moved to the user's left
    smile = neutral.copy()
    smile[:, IDX["mouthSmileLeft"]] = smile[:, IDX["mouthSmileRight"]] = 0.12   # barely moved: not measured
    cal = client.put(f"/api/profiles/{p['id']}/calibration/face",
                     json={"neutral": neutral.tolist(), "wink_left": wink.tolist(),
                           "prompts": {"jaw_left": jaw.tolist(), "smile": smile.tolist()}}).json()
    assert cal["lr_swap"] is True and cal["side_check"] == "mirrored"
    # one-sided prompt: the other side is assumed to move as far
    assert set(cal["measured"]) == {"jawLeft", "jawRight"}
    lib = {i["id"]: i for i in client.get(f"/api/library/facial?profile_id={p['id']}").json()}
    assert lib["face.jaw_left"]["available"] and not lib["face.lips_press"]["available"]


def test_library_endpoints_and_exclusions(client):
    p = make_profile(client, flexibility="low")
    items = client.get(f"/api/library/motor?profile_id={p['id']}").json()
    assert len(items) >= 500 and any(not i["available"] for i in items)
    client.put(f"/api/profiles/{p['id']}/exclusions/motor/box.jab", json={"excluded": True})
    items = {i["id"]: i for i in client.get(f"/api/library/motor?profile_id={p['id']}").json()}
    assert items["box.jab"]["excluded"]
    one = client.get("/api/library/motor/box.jab").json()
    assert len(one["frames"]) > 10 and one["fps"] == 30
    assert client.get("/api/library/motor/nope").status_code == 404
