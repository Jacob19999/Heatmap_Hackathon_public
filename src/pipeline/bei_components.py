"""
BEI components: step-decay, robust normalization, S/T/P/C computation.
E2SFCA for S, P, C; T from system time and tier penalty.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from . import config

if TYPE_CHECKING:
    pass

LOG = logging.getLogger(__name__)


def step_decay(t_min: pd.Series | np.ndarray, bands: tuple[int, ...] | None = None, weights: tuple[float, ...] | None = None) -> np.ndarray:
    """g(t): 1.0 if t<=30, 0.60 if 30<t<=60, 0.30 if 60<t<=90, 0 if t>90."""
    bands = bands or config.STEP_DECAY_BANDS_MIN
    weights = weights or config.STEP_DECAY_WEIGHTS
    t = np.asarray(t_min, dtype=float)
    out = np.zeros_like(t)
    out[:] = weights[-1]
    out[t <= bands[0]] = weights[0]
    out[(t > bands[0]) & (t <= bands[1])] = weights[1]
    out[(t > bands[1]) & (t <= bands[2])] = weights[2]
    return out


def robust_norm(x: pd.Series | np.ndarray, low_p: float | None = None, high_p: float | None = None, inf_cap: float | None = None) -> np.ndarray:
    """Min-max normalization with 5th/95th percentile winsorization. Returns array in [0, 1] (higher = better).

    Inf values are replaced with *inf_cap* (default: 480 min / 8 hours) before
    percentile computation so they don't poison the normalization.
    """
    low_p = low_p or config.NORM_LOW_PERCENTILE
    high_p = high_p or config.NORM_HIGH_PERCENTILE
    x = np.asarray(x, dtype=float)
    cap = inf_cap if inf_cap is not None else 480.0
    x = np.where(np.isinf(x), cap, x)
    lo = np.nanpercentile(x, low_p)
    hi = np.nanpercentile(x, high_p)
    x = np.clip(x, lo, hi)
    span = hi - lo
    if span <= 0:
        return np.ones_like(x) * 0.5
    return (x - lo) / span


def gap_score(accessibility: pd.Series | np.ndarray, **norm_kw) -> np.ndarray:
    """Gap = 1 - Norm(accessibility); higher = worse access."""
    return 1.0 - robust_norm(accessibility, **norm_kw)
