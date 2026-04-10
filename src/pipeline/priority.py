"""
Need overlay and priority layer: Priority = BEI * (1 + λ * NeedOverlay).
NeedOverlay = α * Norm(total_pop) + (1 − α) * Norm(child_pop).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .bei_components import robust_norm

__all__ = ["config", "compute_need_overlay", "compute_priority_score"]


def compute_need_overlay(
    df: pd.DataFrame,
    total_pop_col: str = "total_pop",
    child_pop_col: str = "child_pop",
    alpha: float | None = None,
) -> pd.Series:
    """Compute need overlay: α * Norm(total_pop) + (1 − α) * Norm(child_pop).

    Population is normalized (robust 5th–95th percentile) so that higher pop
    yields higher overlay. Missing or zero pop is treated as 0 after norm.
    """
    alpha = alpha if alpha is not None else config.NEED_OVERLAY_ALPHA
    total = df[total_pop_col].fillna(0).values.astype(float)
    child = df[child_pop_col].fillna(0).values.astype(float) if child_pop_col in df.columns else np.zeros(len(df))
    n_total = robust_norm(total)
    n_child = robust_norm(child)
    return pd.Series(alpha * n_total + (1.0 - alpha) * n_child, index=df.index)


def compute_priority_score(
    df: pd.DataFrame,
    bei_col: str = "bei",
    total_pop_col: str = "total_pop",
    child_pop_col: str = "child_pop",
    alpha: float | None = None,
    lambda_: float | None = None,
) -> pd.DataFrame:
    """Add need_overlay and priority_score to a BEI table.

    priority_score = bei * (1 + λ * need_overlay).
    Higher need (pop/child) increases priority for intervention ranking.
    Returns a copy of df with columns need_overlay and priority_score added.
    """
    lambda_ = lambda_ if lambda_ is not None else config.PRIORITY_LAMBDA
    out = df.copy()
    need = compute_need_overlay(out, total_pop_col=total_pop_col, child_pop_col=child_pop_col, alpha=alpha)
    out["need_overlay"] = need
    bei = out[bei_col].astype(float).fillna(0)
    out["priority_score"] = bei * (1.0 + lambda_ * need.values)
    return out
