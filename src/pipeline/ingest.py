"""
NIRD ingestion, validation, and facility classification.
Loads full NIRD xlsx (path from config), validates fields, computes supply/peds weights and classification.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from . import config

LOG = logging.getLogger(__name__)
NIRD_SHEET = "Data Table NIRD 20230130"


def _coerce_bool(s: pd.Series) -> pd.Series:
    """Coerce to bool: 1/1.0/True/'Yes' -> True, else False."""
    dtype_name = getattr(s.dtype, "name", str(s.dtype))
    if s.dtype == object or dtype_name in ("string", "str", "object"):
        return s.fillna("").astype(str).str.strip().str.lower().isin(("yes", "1", "true"))
    return (pd.to_numeric(s, errors="coerce").fillna(0).astype(int) == 1).astype(bool)


def _coerce_int(s: pd.Series) -> pd.Series:
    """Coerce to int; nulls -> 0 for beds."""
    return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)


def load_nird(path: Path | None = None) -> pd.DataFrame:
    """Load NIRD from xlsx; use data sheet. Path defaults to config.NIRD_FULL_PATH."""
    path = path or config.NIRD_FULL_PATH
    if not path.exists():
        raise FileNotFoundError(f"NIRD file not found: {path}")
    df = pd.read_excel(path, sheet_name=NIRD_SHEET)
    return df


def validate_nird(df: pd.DataFrame) -> dict:
    """Validate types, nulls, duplicates on AHA_ID. Return report dict with full validation summary."""
    report = {
        "rows": len(df),
        "duplicates_aha_id": 0,
        "null_aha_id": 0,
        "errors": [],
        "null_counts": {},
        "duplicate_aha_ids": [],
        "validation_passed": True,
    }
    required = ["AHA_ID", "HOSPITAL_NAME", "STATE", "ZIP_CODE"]
    for col in required:
        if col not in df.columns:
            report["errors"].append(f"Missing column: {col}")
            report["validation_passed"] = False
    optional_key = ["ADDRESS", "CITY"]
    for col in required + optional_key:
        if col in df.columns:
            report["null_counts"][col] = int(df[col].isna().sum())
    if "AHA_ID" in df.columns:
        report["null_aha_id"] = int(df["AHA_ID"].isna().sum())
        report["duplicates_aha_id"] = int(df["AHA_ID"].duplicated().sum())
        if report["null_aha_id"] > 0 or report["duplicates_aha_id"] > 0:
            report["validation_passed"] = False
        dup_ids = df.loc[df["AHA_ID"].duplicated(keep=False), "AHA_ID"].dropna().unique().tolist()
        report["duplicate_aha_ids"] = [str(x) for x in dup_ids[:50]]
        if len(dup_ids) > 50:
            report["duplicate_aha_ids"].append(f"... and {len(dup_ids) - 50} more")
    return report


def compute_classification(df: pd.DataFrame) -> pd.DataFrame:
    """Add is_definitive, is_stabilization, supply_weight, peds_weight per plan.md."""
    out = df.copy()
    # Coerce flags to bool
    burn_adult = _coerce_bool(out["BURN_ADULT"]) if "BURN_ADULT" in out.columns else pd.Series(False, index=out.index)
    burn_peds = _coerce_bool(out["BURN_PEDS"]) if "BURN_PEDS" in out.columns else pd.Series(False, index=out.index)
    trauma_adult = _coerce_bool(out["TRAUMA_ADULT"]) if "TRAUMA_ADULT" in out.columns else pd.Series(False, index=out.index)
    adult_l1 = _coerce_bool(out["ADULT_TRAUMA_L1"]) if "ADULT_TRAUMA_L1" in out.columns else pd.Series(False, index=out.index)
    adult_l2 = _coerce_bool(out["ADULT_TRAUMA_L2"]) if "ADULT_TRAUMA_L2" in out.columns else pd.Series(False, index=out.index)
    peds_l1 = _coerce_bool(out["PEDS_TRAUMA_L1"]) if "PEDS_TRAUMA_L1" in out.columns else pd.Series(False, index=out.index)
    peds_l2 = _coerce_bool(out["PEDS_TRAUMA_L2"]) if "PEDS_TRAUMA_L2" in out.columns else pd.Series(False, index=out.index)
    aba = _coerce_bool(out["ABA_VERIFIED"]) if "ABA_VERIFIED" in out.columns else pd.Series(False, index=out.index)
    bc_state = _coerce_bool(out["BC_STATE_DESIGNATED"]) if "BC_STATE_DESIGNATED" in out.columns else pd.Series(False, index=out.index)

    is_definitive = burn_adult | burn_peds
    is_stabilization = (trauma_adult | adult_l1 | adult_l2) & ~is_definitive

    # Supply weight q_j^(S): order matters (higher first)
    supply_weight = pd.Series(0.0, index=out.index)
    supply_weight[aba] = 1.00
    supply_weight[bc_state & ~aba] = 0.85
    supply_weight[is_definitive & ~aba & ~bc_state] = 0.50
    supply_weight[is_stabilization & (supply_weight == 0)] = 0.20

    # Pediatric weight q_j^(P): higher first
    peds_weight = pd.Series(0.0, index=out.index)
    peds_weight[burn_peds & aba] = 1.00
    peds_weight[burn_peds & bc_state & ~aba] = 0.85
    peds_weight[(peds_l1 | peds_l2) & is_definitive & (peds_weight == 0)] = 0.60
    peds_weight[(peds_l1 | peds_l2) & (peds_weight == 0)] = 0.25

    out["is_definitive"] = is_definitive
    out["is_stabilization"] = is_stabilization
    out["supply_weight"] = supply_weight
    out["peds_weight"] = peds_weight
    if "BURN_BEDS" in out.columns:
        out["burn_beds"] = _coerce_int(out["BURN_BEDS"])
    return out


def ingest_nird(path: Path | None = None, produce_report: bool = True) -> tuple[pd.DataFrame, dict]:
    """Load NIRD, validate, compute classification and weights. Returns (facilities_df, validation_report)."""
    from tqdm.auto import tqdm

    path = path or config.NIRD_FULL_PATH
    with tqdm(total=4, desc="Ingest", unit="step", leave=True) as pbar:
        pbar.set_postfix_str(f"current: load NIRD from {path.name}")
        df = load_nird(path)
        pbar.update(1)
        pbar.set_postfix_str("current: validate")
        report = validate_nird(df)
        pbar.update(1)
        pbar.set_postfix_str(f"current: classify ({len(df)} rows)")
        df = compute_classification(df)
        pbar.update(1)
        report["facility_counts"] = {
            "definitive": int(df["is_definitive"].sum()),
            "stabilization": int(df["is_stabilization"].sum()),
            "total": len(df),
        }
        pbar.set_postfix_str(f"done: {report['facility_counts']['total']} facilities")
        pbar.update(1)
    if produce_report:
        LOG.info("NIRD ingest: %s", report)
    if not report.get("validation_passed", True):
        LOG.warning(
            "NIRD validation issues: %d null AHA_ID, %d duplicate AHA_ID, errors=%s",
            report.get("null_aha_id", 0),
            report.get("duplicates_aha_id", 0),
            report.get("errors", []),
        )
    return df, report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Use sample for testing when full file not present
    path = config.NIRD_SAMPLE_PATH if not config.NIRD_FULL_PATH.exists() else config.NIRD_FULL_PATH
    facilities, report = ingest_nird(path)
    print("Report:", report)
    print("Columns:", facilities.columns.tolist())
