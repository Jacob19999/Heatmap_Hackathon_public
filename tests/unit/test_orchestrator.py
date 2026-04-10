from __future__ import annotations

from src.results_pipeline.orchestrator import build_final_exports, plan_for_profile, validate_pipeline
from src.results_pipeline.settings import RuntimeConfig


def test_plan_for_profile_mvp() -> None:
    cfg = RuntimeConfig(raw={"profile": "mvp"}, source_paths=[])
    stages = plan_for_profile(cfg)
    assert stages == ["00", "01", "02", "03", "04", "05", "08", "09"]


def test_plan_for_profile_full() -> None:
    cfg = RuntimeConfig(raw={"profile": "full"}, source_paths=[])
    stages = plan_for_profile(cfg)
    assert "06" in stages and "07" in stages


def test_validate_pipeline_returns_ok_for_default_profiles() -> None:
    cfg = RuntimeConfig(raw={"profile": "mvp"}, source_paths=[])
    result = validate_pipeline(cfg)
    assert result["ok"] is True
    assert result["summary"]["status"] == "PASS"


def test_build_final_exports_reports_missing_upstream_artifacts(tmp_path) -> None:
    cfg = RuntimeConfig(
        raw={
            "profile": "mvp",
            "outputs": {
                "figures_dir": str(tmp_path / "outputs" / "figures"),
                "tables_dir": str(tmp_path / "outputs" / "tables"),
                "metrics_dir": str(tmp_path / "outputs" / "metrics"),
                "final_bundle_dir": str(tmp_path / "outputs" / "final_bundle"),
            },
        },
        source_paths=[],
    )
    result = build_final_exports(cfg)
    assert result["ok"] is False
    assert any("upstream artifacts are missing" in err.lower() for err in result["errors"])
