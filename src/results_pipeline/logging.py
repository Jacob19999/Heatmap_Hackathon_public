from __future__ import annotations

import logging
import time
from typing import Any

_STAGE_START_TS: dict[str, float] = {}


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def stage_logger(stage_id: str) -> logging.Logger:
    return logging.getLogger(f"results_pipeline.stage.{stage_id}")


def log_stage_start(stage_id: str, extra: dict[str, Any] | None = None) -> None:
    _STAGE_START_TS[stage_id] = time.perf_counter()
    stage_logger(stage_id).info("stage_start %s", extra or {})


def log_stage_end(stage_id: str, extra: dict[str, Any] | None = None) -> None:
    payload = dict(extra or {})
    started = _STAGE_START_TS.pop(stage_id, None)
    if started is not None:
        payload["duration_ms"] = int((time.perf_counter() - started) * 1000)
    stage_logger(stage_id).info("stage_end %s", payload)


def log_validation(stage_id: str, ok: bool, detail: str = "") -> None:
    logger = stage_logger(stage_id)
    if ok:
        logger.info("validation_pass %s", detail)
    else:
        logger.error("validation_fail %s", detail)


def log_pipeline_failure(summary: dict[str, Any]) -> None:
    logging.getLogger("results_pipeline").error("pipeline_failed %s", summary)
