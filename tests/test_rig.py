import numpy as np
import pytest

from mfnb.motion.rig import DEFAULT_BODY, parse_dir, pose_joints, sample_keys
from mfnb.motion.skeleton import J, mirror_seq


def dist(p, a, b):
    return np.linalg.norm(p[..., J[a], :] - p[..., J[b], :], axis=-1)


def test_parse_dir_tokens():
    root, v = parse_dir("@down+0.5fwd")
    assert root
    np.testing.assert_allclose(v, np.array([0, -1, 0.5]) / np.linalg.norm([0, -1, 0.5]))
    assert parse_dir("out")[1].tolist() == [1, 0, 0]
    with pytest.raises(ValueError):
        parse_dir("sideways")


def test_bone_lengths_preserved():
    keys = [(0.0, {}), (0.5, {"r_upper_arm": "@fwd", "r_forearm": "@fwd", "pitch": 20, "twist": -30,
                              "l_thigh": "fwd", "l_shin": "fwd+0.2down", "yaw": 40})]
    seq = sample_keys(keys)
    b = DEFAULT_BODY
    np.testing.assert_allclose(dist(seq, "r_shoulder", "r_elbow"), b.upper_arm, atol=1e-9)
    np.testing.assert_allclose(dist(seq, "r_elbow", "r_wrist"), b.forearm, atol=1e-9)
    np.testing.assert_allclose(dist(seq, "l_hip", "l_knee"), b.thigh, atol=1e-9)
    np.testing.assert_allclose(dist(seq, "l_knee", "l_ankle"), b.shin, atol=1e-9)


def test_grounding_keeps_lowest_foot_on_floor():
    seq = sample_keys([(0.0, {}), (1.0, {"l_thigh": "down+0.8fwd", "l_shin": "down",
                                          "r_thigh": "down+0.5back", "r_shin": "down"})])
    feet = seq[:, [J["l_ankle"], J["r_ankle"]], 1] - DEFAULT_BODY.ankle_height
    toes = seq[:, [J["l_foot"], J["r_foot"]], 1] - 0.02
    low = np.minimum(feet.min(1), toes.min(1))
    np.testing.assert_allclose(low, 0, atol=1e-9)


def test_rest_pose_is_upright_and_symmetric():
    p = pose_joints({})
    assert p[J["nose"], 1] > 1.5
    np.testing.assert_allclose(mirror_seq(p), p, atol=1e-9)


def test_mirror_involution_and_side_swap():
    right_jab = sample_keys([(0, {}), (0.4, {"r_upper_arm": "@fwd", "r_forearm": "@fwd"})])
    left_jab = sample_keys([(0, {}), (0.4, {"l_upper_arm": "@fwd", "l_forearm": "@fwd"})])
    np.testing.assert_allclose(mirror_seq(mirror_seq(right_jab)), right_jab)
    np.testing.assert_allclose(mirror_seq(right_jab), left_jab, atol=1e-9)
    # the jab points toward the camera (+z)
    assert right_jab[-1, J["r_wrist"], 2] > right_jab[-1, J["r_shoulder"], 2] + 0.5


def test_positive_yaw_turns_toward_subject_left():
    p = pose_joints({"yaw": 90})
    # facing +x: the left shoulder moved behind (negative z)
    assert p[J["l_shoulder"], 2] < -0.1
    mid_sh_x = (p[J["l_shoulder"], 0] + p[J["r_shoulder"], 0]) / 2
    assert p[J["nose"], 0] > mid_sh_x + 0.05


def test_leg_ik_reaches_target_and_grounds_both_feet():
    p = pose_joints({"l_leg_ik": [0.05, -0.80, 0.25], "r_leg_ik": [0.10, -0.80, -0.25]})
    b = DEFAULT_BODY
    ank = p[J["l_ankle"]] - p[J["l_hip"]]
    np.testing.assert_allclose(ank, [0.05, -0.80, 0.25], atol=1e-6)
    # equal drop on both legs -> both ankles at ankle height
    np.testing.assert_allclose(p[[J["l_ankle"], J["r_ankle"]], 1], b.ankle_height, atol=1e-6)
    # knees bend forward
    assert p[J["l_knee"], 2] > (p[J["l_hip"], 2] + p[J["l_ankle"], 2]) / 2


def test_arm_ik_then_direction_override():
    from mfnb.motion.rig import merge_pose
    pose = merge_pose({}, {"r_arm_ik": [-0.1, 0.15, 0.25]})
    pose = merge_pose(pose, {"r_forearm": "@fwd"})
    assert "r_arm_ik" not in pose and "r_upper_arm" in pose
    p = pose_joints(pose)
    assert p[J["r_wrist"], 2] > p[J["r_elbow"], 2] + 0.2


def test_sampling_covers_every_frame_for_odd_durations():
    for dur in (0.66, 0.71, 1.03, 2.345):
        seq = sample_keys([(0, {}), (dur, {"r_upper_arm": "@fwd"})])
        assert not np.isnan(seq).any()
        # the last frame is the final key, not an all-zero frame
        assert seq[-1, J["r_wrist"], 2] > 0.3
