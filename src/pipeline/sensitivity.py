"""Parameter grid helpers for sensitivity analysis.

This module keeps the *declarative* description of which parameter
combinations are worth exploring for:

- transfer penalty (τ)
- capacity utilization (u)
- need overlay weight (α)
- priority lambda (λ)
- transport scenario (ground-only vs ground-plus-air)

The actual heavy-weight computation of BEI under each setting remains in
the main pipeline modules; callers can import :func:`iter_sensitivity_grid`
to drive notebooks or scripted sweeps without duplicating the ranges.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Iterator, Literal

from . import config

Scenario = Literal["ground_only", "ground_plus_air"]


@dataclass(frozen=True)
class SensitivityPoint:
    """Single point in the sensitivity design grid."""

    scenario: Scenario
    transfer_penalty_min: float
    capacity_utilization: float
    need_alpha: float
    priority_lambda: float


def _default_scenarios() -> tuple[Scenario, ...]:
    """Return the conditional ground-only and ground-plus-air scenarios.

    The MN MVP uses ground-only for primary results, but notebooks may
    still explore a paired ground-plus-air sensitivity run.
    """
    return ("ground_only", "ground_plus_air")


def iter_sensitivity_grid(
    scenarios: Iterable[Scenario] | None = None,
) -> Iterator[SensitivityPoint]:
    """Yield the cross-product of configured sensitivity ranges.

    The ranges are sourced from :mod:`config` so they stay in one place:

    - ``config.SENSITIVITY_TRANSFER_PENALTY``
    - ``config.SENSITIVITY_CAPACITY_UTILIZATION``
    - ``config.SENSITIVITY_NEED_ALPHA``
    - ``config.SENSITIVITY_PRIORITY_LAMBDA``

    Parameters
    ----------
    scenarios:
        Optional iterable of scenarios to include. When omitted, both
        ``\"ground_only\"`` and ``\"ground_plus_air\"`` are used so callers
        can run a paired conditional ground-plus-air comparison.
    """
    tau_values = tuple(config.SENSITIVITY_TRANSFER_PENALTY)
    util_values = tuple(config.SENSITIVITY_CAPACITY_UTILIZATION)
    alpha_values = tuple(config.SENSITIVITY_NEED_ALPHA)
    lambda_values = tuple(config.SENSITIVITY_PRIORITY_LAMBDA)
    scenario_values = tuple(scenarios) if scenarios is not None else _default_scenarios()

    for scenario, tau, util, alpha, lam in product(
        scenario_values,
        tau_values,
        util_values,
        alpha_values,
        lambda_values,
    ):
        yield SensitivityPoint(
            scenario=scenario,
            transfer_penalty_min=float(tau),
            capacity_utilization=float(util),
            need_alpha=float(alpha),
            priority_lambda=float(lam),
        )


__all__ = [
    "config",
    "Scenario",
    "SensitivityPoint",
    "iter_sensitivity_grid",
]
