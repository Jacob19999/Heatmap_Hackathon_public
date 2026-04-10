"""Stage 09: Robustness and story exports — final bundle assembly and one-line findings."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ..contracts.artifacts import ArtifactManifest, ArtifactRecord, FindingRecord
from ..io.writers import write_csv, write_finding, write_manifest
from ..settings import RuntimeConfig
from ..utils.validation import ValidationError

STAGE_META: dict[str, Any] = {
    "stage_id": "09",
    "name": "story_exports",
    "question": "What are the final story-ready artifacts and one-line findings?",
    "description": "Assemble figure/table manifests, final findings summary, method notes, and deck/map/metrics-ready exports.",
    "replaces_notebooks": ["02_challenge_outputs.ipynb"],
    "required_inputs": ["outputs/figures/", "outputs/tables/", "outputs/metrics/"],
    "produced_datasets": [],
    "produced_tables": ["outputs/final_bundle/final_findings_summary.csv", "outputs/final_bundle/table_manifest.csv"],
    "produced_figures": ["outputs/final_bundle/figure_manifest.csv"],
    "produced_findings": ["outputs/metrics/09_findings_ground_only.json"],
    "validations": ["findings_coverage"],
}


@dataclass(frozen=True)
class Stage09Config:
    outputs_figures_dir: Path
    outputs_tables_dir: Path
    outputs_metrics_dir: Path
    final_bundle_dir: Path


def _cfg(config: RuntimeConfig) -> Stage09Config:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    outputs = config.raw.get("outputs", {})
    return Stage09Config(
        outputs_figures_dir=Path(outputs.get("figures_dir", root / "outputs" / "figures")),
        outputs_tables_dir=Path(outputs.get("tables_dir", root / "outputs" / "tables")),
        outputs_metrics_dir=Path(outputs.get("metrics_dir", root / "outputs" / "metrics")),
        final_bundle_dir=Path(outputs.get("final_bundle_dir", root / "outputs" / "final_bundle")),
    )


def _gather_findings(metrics_dir: Path) -> list[dict[str, Any]]:
    findings = []
    if not metrics_dir.exists():
        return findings
    for p in sorted(metrics_dir.glob("*_findings_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["_path"] = str(p)
            findings.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return findings


def _gather_figures(figures_dir: Path) -> list[Path]:
    if not figures_dir.exists():
        return []
    return sorted(figures_dir.glob("*.png")) + sorted(figures_dir.glob("*.pdf"))


def _gather_tables(tables_dir: Path) -> list[Path]:
    if not tables_dir.exists():
        return []
    return sorted(tables_dir.glob("*.csv"))


def _infer_stage_id_from_name(name: str) -> str:
    token = name[:2]
    return token if token.isdigit() else ""


def _validate_findings_coverage(
    findings_df: pd.DataFrame,
    figure_rows: list[dict[str, str]],
    table_rows: list[dict[str, str]],
) -> None:
    if findings_df.empty:
        raise ValidationError("Stage 09 cannot build final bundle: no stage findings were found.")
    if "stage_id" not in findings_df.columns:
        raise ValidationError("Stage 09 findings summary is missing `stage_id`.")
    covered_stage_ids = {str(s) for s in findings_df["stage_id"].dropna().astype(str).tolist()}
    missing_figure_stage_ids = sorted(
        {
            row["stage_id"]
            for row in figure_rows
            if row.get("stage_id") and row["stage_id"] not in covered_stage_ids
        }
    )
    missing_table_stage_ids = sorted(
        {
            row["stage_id"]
            for row in table_rows
            if row.get("stage_id") and row["stage_id"] not in covered_stage_ids
        }
    )
    if missing_figure_stage_ids or missing_table_stage_ids:
        raise ValidationError(
            "Missing findings coverage for final artifacts. "
            f"figure stages without findings: {missing_figure_stage_ids}; "
            f"table stages without findings: {missing_table_stage_ids}"
        )


def _write_method_notes(path: Path, config: RuntimeConfig) -> None:
    scenario = config.scenario
    path.write_text(
        "# Method notes\n\n"
        "## Scope and interpretation\n"
        "- Pipeline stages: 00 audit -> 01 geography -> 02 supply/capacity -> 03 ground access -> 04 pediatric gap -> 05 transfer-aware -> 08 BEI hotspots -> 09 story exports.\n"
        "- NIRD-derived metrics describe structural access and infrastructure context; they are not patient-level outcomes.\n"
        "- Structural capacity outputs are not real-time bed availability claims.\n"
        "- Need overlays are attached for context and are not mixed into core BEI scoring.\n\n"
        "## Scenario labeling\n"
        f"- Active run scenario: `{scenario}`.\n"
        "- Air-related outputs are scenario/sensitivity layers and must remain explicitly labeled.\n\n"
        "## Documented deviations from notebook path\n"
        "- Configuration is contract-driven (`configs/default.yaml`, profile, and scenario overlays).\n"
        "- Stage execution is deterministic by DAG and validated contracts rather than notebook execution order.\n"
        "- Final bundle is manifest-driven for reproducible artifact traceability.\n",
        encoding="utf-8",
    )


def _validate_final_bundle(c: Stage09Config) -> None:
    required_files = [
        c.final_bundle_dir / "final_findings_summary.csv",
        c.final_bundle_dir / "figure_manifest.csv",
        c.final_bundle_dir / "table_manifest.csv",
        c.final_bundle_dir / "method_notes.md",
    ]
    required_dirs = [
        c.final_bundle_dir / "deck_ready",
        c.final_bundle_dir / "map_ready",
        c.final_bundle_dir / "metrics_ready",
    ]
    missing_files = [str(path) for path in required_files if not path.exists()]
    missing_dirs = [str(path) for path in required_dirs if not path.exists()]
    if missing_files or missing_dirs:
        raise ValidationError(
            "Final bundle completeness check failed. "
            f"missing files: {missing_files}; missing directories: {missing_dirs}"
        )


def run(config: RuntimeConfig) -> dict[str, Any]:
    c = _cfg(config)
    c.final_bundle_dir.mkdir(parents=True, exist_ok=True)

    findings_list = _gather_findings(c.outputs_metrics_dir)
    figures = _gather_figures(c.outputs_figures_dir)
    tables = _gather_tables(c.outputs_tables_dir)

    one_liners = []
    for f in findings_list:
        stage_id = f.get("stage_id", "?")
        question = f.get("question", "")
        finding = f.get("finding", "")
        one_liners.append({"stage_id": stage_id, "question": question, "one_line_finding": finding})
    findings_df = pd.DataFrame(one_liners)
    final_findings_path = c.final_bundle_dir / "final_findings_summary.csv"
    write_csv(findings_df, final_findings_path)

    figure_manifest_rows = [
        {"path": str(p), "name": p.name, "stage_id": _infer_stage_id_from_name(p.name)}
        for p in figures
    ]
    figure_manifest_path = c.final_bundle_dir / "figure_manifest.csv"
    write_csv(pd.DataFrame(figure_manifest_rows), figure_manifest_path)

    table_manifest_rows = [
        {"path": str(p), "name": p.name, "stage_id": _infer_stage_id_from_name(p.name)}
        for p in tables
    ]
    table_manifest_path = c.final_bundle_dir / "table_manifest.csv"
    write_csv(pd.DataFrame(table_manifest_rows), table_manifest_path)

    _validate_findings_coverage(findings_df, figure_manifest_rows, table_manifest_rows)

    method_notes_path = c.final_bundle_dir / "method_notes.md"
    _write_method_notes(method_notes_path, config)

    deck_ready = c.final_bundle_dir / "deck_ready"
    map_ready = c.final_bundle_dir / "map_ready"
    metrics_ready = c.final_bundle_dir / "metrics_ready"
    deck_ready.mkdir(exist_ok=True)
    map_ready.mkdir(exist_ok=True)
    metrics_ready.mkdir(exist_ok=True)
    for p in figures:
        shutil.copy2(p, deck_ready / p.name)
        shutil.copy2(p, map_ready / p.name)
    for p in tables:
        shutil.copy2(p, metrics_ready / p.name)
    shutil.copy2(final_findings_path, metrics_ready / "final_findings_summary.csv")

    _validate_final_bundle(c)

    finding_path = c.outputs_metrics_dir / "09_findings_ground_only.json"
    finding = FindingRecord(
        stage_id="09",
        question="What are the final story-ready artifacts and one-line findings?",
        finding="Final bundle assembled: figure and table manifests, one-line findings summary, method notes, deck_ready/map_ready/metrics_ready exports.",
        why_it_matters="Judge-ready deliverables require traceable artifacts and plain-language findings.",
        action_implication="Use final_bundle for submission and validation.",
        scenario_id="ground_only",
    )
    write_finding(finding, finding_path)

    artifacts: list[ArtifactRecord] = [
        ArtifactRecord("09_final_findings", "09", "table", str(final_findings_path), "csv"),
        ArtifactRecord("09_figure_manifest", "09", "table", str(figure_manifest_path), "csv"),
        ArtifactRecord("09_table_manifest", "09", "table", str(table_manifest_path), "csv"),
        ArtifactRecord("09_method_notes", "09", "dataset", str(method_notes_path), "md"),
        ArtifactRecord("09_finding", "09", "finding", str(finding_path), "json"),
    ]
    manifest = ArtifactManifest(run_id="stage09", profile=config.profile, artifacts=artifacts)
    manifest_path = c.outputs_metrics_dir / "09_manifest_ground_only.json"
    write_manifest(manifest, manifest_path)

    return {
        "ok": True,
        "stage_id": "09",
        "final_bundle": str(c.final_bundle_dir),
        "final_findings_summary": str(final_findings_path),
        "figure_manifest": str(figure_manifest_path),
        "table_manifest": str(table_manifest_path),
        "method_notes": str(method_notes_path),
        "finding": str(finding_path),
        "manifest": str(manifest_path),
    }
