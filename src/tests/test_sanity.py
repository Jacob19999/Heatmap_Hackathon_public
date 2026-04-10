"""Sanity tests: BEI formula, component bounds, and MN profile wiring."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config
from pipeline.presentation_scope import get_profile
from pipeline.bei_components import step_decay, robust_norm


def test_bei_weights_sum_to_one():
    """BEI weights (S,T,P,C) sum to 1."""
    w = config.BEI_WEIGHTS
    assert abs(sum(w) - 1.0) < 1e-6


def test_components_bounded():
    """Step-decay and robust_norm produce values in expected ranges."""
    t = np.array([10, 50, 100])
    g = step_decay(t)
    assert (g >= 0).all() and (g <= 1).all()
    x = np.array([0.1, 0.5, 0.9])
    n = robust_norm(x)
    assert (n >= 0).all() and (n <= 1).all()


def test_bei_formula_algebraic():
    """BEI = 100 * (0.25*S + 0.30*T + 0.20*P + 0.25*C) for sample scores."""
    s, t, p, c = 0.2, 0.3, 0.1, 0.4
    w = config.BEI_WEIGHTS
    bei = 100 * (w[0] * s + w[1] * t + w[2] * p + w[3] * c)
    assert 0 <= bei <= 100
    assert abs(bei - (100 * (0.25 * 0.2 + 0.30 * 0.3 + 0.20 * 0.1 + 0.25 * 0.4))) < 1e-6


def test_default_dataset_profile_is_mn_high_detail():
    """Default dataset profile is mn_high_detail and has expected prefix."""
    profile = get_profile()
    assert profile.profile_id == "mn_high_detail"
    assert profile.output_prefix == "mn_high_detail"
