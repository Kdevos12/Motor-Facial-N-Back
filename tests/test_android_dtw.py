import numpy as np
import pytest
from dtaidistance.subsequence.dtw import subsequence_alignment

from mfnb.motion._dtw import subsequence_alignment as python_subsequence_alignment


def test_python_subsequence_alignment_matches_reference_with_idle_frames():
    rng = np.random.default_rng(31)
    query = rng.normal(size=(8, 5))
    series = np.vstack((rng.normal(size=(4, 5)), query[:3], query[2:5], query[5:], rng.normal(size=(3, 5))))

    expected = subsequence_alignment(query, series, penalty=0.05, use_c=False).best_match().path
    actual = python_subsequence_alignment(query, series, penalty=0.05, use_c=True).best_match().path

    assert actual == expected


def test_python_subsequence_alignment_rejects_series_without_a_two_frame_match():
    query = np.array([[0.0], [1.0], [2.0]])
    series = np.array([[0.0]])

    with pytest.raises(ValueError):
        python_subsequence_alignment(query, series, penalty=0.05)
