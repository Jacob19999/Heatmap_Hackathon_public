from __future__ import annotations

import logging

from src.results_pipeline.logging import log_stage_end, log_stage_start


def test_stage_logging_includes_duration(caplog) -> None:
    caplog.set_level(logging.INFO)
    log_stage_start("00", {"profile": "mvp"})
    log_stage_end("00", {"status": "ok"})
    assert any("duration_ms" in record.getMessage() for record in caplog.records)
