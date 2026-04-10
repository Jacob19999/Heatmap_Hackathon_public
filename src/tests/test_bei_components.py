"""BEI component tests: step-decay boundaries, normalization bounds, gap inversion."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.bei_components import step_decay, robust_norm, gap_score


def test_step_decay_boundaries():
    """Step-decay at 30, 60, 90 min boundaries."""
    t = np.array([0, 30, 31, 60, 61, 90, 91])
    g = step_decay(t)
    assert g[0] == 1.0
    assert g[1] == 1.0
    assert g[2] == 0.6
    assert g[3] == 0.6
    assert g[4] == 0.3
    assert g[5] == 0.3
    assert g[6] == 0.0


def test_robust_norm_bounds():
    """Normalization output in [0, 1]; ordering preserved."""
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    n = robust_norm(x, low_p=0, high_p=100)
    assert n.min() >= 0 and n.max() <= 1
    assert np.all(np.diff(n) >= 0)


def test_gap_inversion():
    """Gap = 1 - Norm; higher accessibility -> lower gap."""
    x = np.array([10.0, 20.0, 30.0])
    g = gap_score(x)
    n = robust_norm(x)
    assert np.allclose(g, 1 - n)
