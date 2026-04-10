from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from ..contracts.artifacts import ArtifactManifest, ArtifactRecord, FindingRecord
from ..io.loaders import load_excel
from ..io.writers import write_csv, write_finding, write_manifest, write_parquet
from ..settings import RuntimeConfig
from ..utils.normalization import coerce_bool_series, coerce_int_series
from ..utils.validation import ValidationError, require_columns

NIRD_SHEET = "Data Table NIRD 20230130"

STAGE_META: dict[str, Any] = {
    "stage_id": "00",
    "name": "data_audit",
    "question": "Is NIRD standardized and trustworthy for downstream analytics?",
    "description": "Normalize encodings, coerce capacity fields, deduplicate facilities, and export quality diagnostics.",
    "replaces_notebooks": ["01_data_exploration.ipynb", "02_challenge_outputs.ipynb"],
    "required_inputs": ["NIRD workbook"],
    "produced_datasets": ["data/interim/nird_clean.parquet"],
    "produced_tables": [
        "outputs/tables/00_tables_data_quality_summary_ground_only.csv",
        "outputs/tables/00_tables_facility_class_counts_ground_only.csv",
    ],
    "produced_figures": [
        "outputs/figures/00_figures_data_quality_summary_ground_only.png",
        "outputs/figures/00_figures_facility_class_counts_ground_only.png",
    ],
    "produced_findings": ["outputs/metrics/00_findings_ground_only.json"],
    "validations": ["required_columns", "input_exists", "artifact_presence"],
}


@dataclass(frozen=True)
class Stage00Config:
    nird_path: Path
    nird_sheet: str
    data_interim_dir: Path
    outputs_tables_dir: Path
    outputs_figures_dir: Path
    outputs_metrics_dir: Path


def _stage00_config(config: RuntimeConfig) -> Stage00Config:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    data = config.raw.get("data", {})
    outputs = config.raw.get("outputs", {})
    nird_path = Path(data.get("nird_path", root / "Data" / "NIRD 20230130 Database_Hackathon_sample.xlsx"))
    return Stage00Config(
        nird_path=nird_path,
        nird_sheet=str(data.get("nird_sheet", NIRD_SHEET)),
        data_interim_dir=Path(data.get("interim_dir", root / "data" / "interim")),
        outputs_tables_dir=Path(outputs.get("tables_dir", root / "outputs" / "tables")),
        outputs_figures_dir=Path(outputs.get("figures_dir", root / "outputs" / "figures")),
        outputs_metrics_dir=Path(outputs.get("metrics_dir", root / "outputs" / "metrics")),
    )


def _normalize_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    flag_cols = [
        "BURN_ADULT",
        "BURN_PEDS",
        "TRAUMA_ADULT",
        "ADULT_TRAUMA_L1",
        "ADULT_TRAUMA_L2",
        "PEDS_TRAUMA_L1",
        "PEDS_TRAUMA_L2",
        "ABA_VERIFIED",
        "BC_STATE_DESIGNATED",
    ]
    for col in flag_cols:
        if col in out.columns:
            out[col] = coerce_bool_series(out[col])
    return out


def _coerce_capacity(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "TOTAL_BEDS" in out.columns:
        out["TOTAL_BEDS"] = coerce_int_series(out["TOTAL_BEDS"])
    if "BURN_BEDS" in out.columns:
        out["BURN_BEDS"] = coerce_int_series(out["BURN_BEDS"])
    if "ZIP_CODE" in out.columns:
        out["ZIP_CODE"] = out["ZIP_CODE"].astype(str).str.extract(r"(\d{5})", expand=False).fillna("")
    return out


def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "AHA_ID" in out.columns:
        out = out.drop_duplicates(subset=["AHA_ID"], keep="first")
    else:
        keys = [c for c in ["HOSPITAL_NAME", "STATE", "ZIP_CODE"] if c in out.columns]
        if keys:
            out = out.drop_duplicates(subset=keys, keep="first")
    return out.reset_index(drop=True)


def _facility_class(df: pd.DataFrame) -> pd.Series:
    burn_adult = df["BURN_ADULT"] if "BURN_ADULT" in df.columns else False
    burn_peds = df["BURN_PEDS"] if "BURN_PEDS" in df.columns else False
    trauma = (
        (df["TRAUMA_ADULT"] if "TRAUMA_ADULT" in df.columns else False)
        | (df["ADULT_TRAUMA_L1"] if "ADULT_TRAUMA_L1" in df.columns else False)
        | (df["ADULT_TRAUMA_L2"] if "ADULT_TRAUMA_L2" in df.columns else False)
        | (df["PEDS_TRAUMA_L1"] if "PEDS_TRAUMA_L1" in df.columns else False)
        | (df["PEDS_TRAUMA_L2"] if "PEDS_TRAUMA_L2" in df.columns else False)
    )
    aba = df["ABA_VERIFIED"] if "ABA_VERIFIED" in df.columns else False

    facility_class = pd.Series("other", index=df.index, dtype="string")
    definitive = burn_adult | burn_peds | aba
    facility_class.loc[definitive & aba] = "aba_verified_burn"
    facility_class.loc[definitive & ~aba] = "non_verified_burn_capable"
    facility_class.loc[trauma & ~definitive] = "trauma_only"
    facility_class.loc[definitive & trauma] = "combined_burn_trauma"
    facility_class.loc[burn_peds] = "pediatric_capable_burn"
    return facility_class


def _quality_table(before_rows: int, after_rows: int, df: pd.DataFrame) -> pd.DataFrame:
    data = {
        "metric": [
            "input_rows",
            "deduplicated_rows",
            "removed_duplicates",
            "null_aha_id",
            "null_hospital_name",
        ],
        "value": [
            before_rows,
            after_rows,
            before_rows - after_rows,
            int(df["AHA_ID"].isna().sum()) if "AHA_ID" in df.columns else 0,
            int(df["HOSPITAL_NAME"].isna().sum()) if "HOSPITAL_NAME" in df.columns else 0,
        ],
    }
    return pd.DataFrame(data)


def _plot_quality(quality_df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(quality_df["metric"], quality_df["value"], color="#4063D8")
    ax.set_title("Stage 00 Data Audit Summary")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _plot_facility_class(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counts = df["facility_class"].value_counts().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4))
    counts.plot(kind="bar", ax=ax, color="#34A853")
    ax.set_title("Stage 00 Facility Class Counts")
    ax.set_xlabel("facility_class")
    ax.set_ylabel("count")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def run(config: RuntimeConfig) -> dict[str, Any]:
    c = _stage00_config(config)
    if not c.nird_path.exists():
        raise ValidationError(f"NIRD file not found for Stage 00: {c.nird_path}")

    raw = load_excel(c.nird_path, sheet_name=c.nird_sheet)
    require_columns(raw.columns.tolist(), ["AHA_ID", "HOSPITAL_NAME", "STATE"])

    before_rows = len(raw)
    cleaned = _normalize_flags(raw)
    cleaned = _coerce_capacity(cleaned)
    cleaned = _deduplicate(cleaned)
    cleaned["facility_class"] = _facility_class(cleaned)
    after_rows = len(cleaned)

    quality = _quality_table(before_rows, after_rows, cleaned)
    class_counts = (
        cleaned["facility_class"].value_counts().rename_axis("facility_class").reset_index(name="count")
    )

    dataset_path = c.data_interim_dir / "nird_clean.parquet"
    table_quality_path = c.outputs_tables_dir / "00_tables_data_quality_summary_ground_only.csv"
    table_classes_path = c.outputs_tables_dir / "00_tables_facility_class_counts_ground_only.csv"
    fig_quality_path = c.outputs_figures_dir / "00_figures_data_quality_summary_ground_only.png"
    fig_classes_path = c.outputs_figures_dir / "00_figures_facility_class_counts_ground_only.png"
    finding_path = c.outputs_metrics_dir / "00_findings_ground_only.json"
    manifest_path = c.outputs_metrics_dir / "00_manifest_ground_only.json"

    write_parquet(cleaned, dataset_path)
    write_csv(quality, table_quality_path)
    write_csv(class_counts, table_classes_path)
    _plot_quality(quality, fig_quality_path)
    _plot_facility_class(cleaned, fig_classes_path)

    finding = FindingRecord(
        stage_id="00",
        question="Is NIRD standardized and trustworthy for downstream analytics?",
        finding="Stage 00 standardized key flags and capacity fields, removed duplicates, and produced a clean facility base table.",
        why_it_matters="Downstream equity metrics are only defensible if source data quality issues are identified and normalized first.",
        action_implication="Use the Stage 00 quality outputs as the trust gate before geography enrichment and access modeling.",
        scenario_id="ground_only",
    )
    write_finding(finding, finding_path)

    manifest = ArtifactManifest(
        run_id="stage00",
        profile=config.profile,
        artifacts=[
            ArtifactRecord("00_dataset_nird_clean", "00", "dataset", str(dataset_path), "parquet"),
            ArtifactRecord("00_table_quality", "00", "table", str(table_quality_path), "csv"),
            ArtifactRecord("00_table_classes", "00", "table", str(table_classes_path), "csv"),
            ArtifactRecord("00_fig_quality", "00", "figure", str(fig_quality_path), "png"),
            ArtifactRecord("00_fig_classes", "00", "figure", str(fig_classes_path), "png"),
            ArtifactRecord("00_finding", "00", "finding", str(finding_path), "json"),
        ],
    )
    write_manifest(manifest, manifest_path)

    return {
        "ok": True,
        "stage_id": "00",
        "rows_in": before_rows,
        "rows_out": after_rows,
        "dataset": str(dataset_path),
        "tables": [str(table_quality_path), str(table_classes_path)],
        "figures": [str(fig_quality_path), str(fig_classes_path)],
        "finding": str(finding_path),
        "manifest": str(manifest_path),
    }
