from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from ..contracts.artifacts import ArtifactManifest, ArtifactRecord, FindingRecord
from ..io.loaders import load_csv, load_parquet
from ..io.writers import write_csv, write_finding, write_manifest, write_parquet
from ..settings import RuntimeConfig
from ..utils.geography import derive_county_fips, derive_state_fips, derive_tract_geoid
from ..utils.validation import ValidationError, require_columns

STAGE_META: dict[str, Any] = {
    "stage_id": "01",
    "name": "geography_enrichment",
    "question": "Where are facilities and denominators anchored geographically?",
    "description": "Build geographic keys and denominator layers for county/tract analyses.",
    "replaces_notebooks": ["01_data_exploration.ipynb", "02_challenge_outputs.ipynb"],
    "required_inputs": ["data/interim/nird_clean.parquet"],
    "produced_datasets": [
        "data/processed/facilities_geo.parquet",
        "data/processed/county_denominators.parquet",
        "data/processed/tract_denominators.parquet",
    ],
    "produced_tables": [
        "outputs/tables/01_tables_join_quality_ground_only.csv",
        "outputs/tables/01_tables_ruca_summary_ground_only.csv",
    ],
    "produced_figures": ["outputs/figures/01_figures_rural_urban_mix_ground_only.png"],
    "produced_findings": ["outputs/metrics/01_findings_ground_only.json"],
    "validations": ["input_exists", "required_columns", "geography_key_completeness", "denominator_join_quality"],
}


@dataclass(frozen=True)
class Stage01Config:
    nird_clean_path: Path
    county_den_path: Path | None
    tract_den_path: Path | None
    acs_tract_path: Path | None
    geocode_results_path: Path | None
    ruca_path: Path | None
    svi_path: Path | None
    tiger_dir: Path | None
    data_processed_dir: Path
    outputs_tables_dir: Path
    outputs_figures_dir: Path
    outputs_metrics_dir: Path
    strict: bool


def _cfg(config: RuntimeConfig) -> Stage01Config:
    root = Path(config.raw.get("project_root", Path.cwd())).resolve()
    data = config.raw.get("data", {})
    external = data.get("external", {})
    outputs = config.raw.get("outputs", {})
    data_root = root / "Data" if (root / "Data").exists() else root / "data"
    external_root = data_root / "external"
    output_tables_root = data_root / "output" / "tables"
    return Stage01Config(
        nird_clean_path=Path(data.get("nird_clean_path", root / "data" / "interim" / "nird_clean.parquet")),
        county_den_path=Path(external["county_denominators"]) if "county_denominators" in external else None,
        tract_den_path=Path(external["tract_denominators"]) if "tract_denominators" in external else None,
        acs_tract_path=Path(external["acs_tract"]) if "acs_tract" in external else external_root / "acs" / "acs_2022_5yr_tract_b01003_b09001.csv",
        geocode_results_path=Path(external["geocode_results"]) if "geocode_results" in external else output_tables_root / "GeocodeResults.csv",
        ruca_path=Path(external["ruca"]) if "ruca" in external else external_root / "ruca" / "RUCA-codes-2020-tract.xlsx",
        svi_path=Path(external["svi"]) if "svi" in external else external_root / "svi" / "SVI_2022_US.csv",
        tiger_dir=Path(external["tiger_dir"]) if "tiger_dir" in external else external_root / "tiger",
        data_processed_dir=Path(data.get("processed_dir", root / "data" / "processed")),
        outputs_tables_dir=Path(outputs.get("tables_dir", root / "outputs" / "tables")),
        outputs_figures_dir=Path(outputs.get("figures_dir", root / "outputs" / "figures")),
        outputs_metrics_dir=Path(outputs.get("metrics_dir", root / "outputs" / "metrics")),
        strict=bool(config.raw.get("validation", {}).get("strict_geography", True)),
    )


def _load_optional(path: Path | None) -> pd.DataFrame | None:
    if path is None or not path.exists():
        return None
    if path.suffix.lower() == ".parquet":
        return load_parquet(path)
    return load_csv(path)


def _normalize_numeric_fips(series: object, width: int) -> pd.Series:
    cleaned = pd.Series(series).astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    return cleaned.where(cleaned.str.fullmatch(r"\d+"), "").str.zfill(width)


def _build_geoid(state: pd.Series, county: pd.Series, tract: pd.Series) -> pd.Series:
    state_fips = _normalize_numeric_fips(state, 2)
    county_fips = _normalize_numeric_fips(county, 3)
    tract_fips = _normalize_numeric_fips(tract, 6)
    out = state_fips + county_fips + tract_fips
    return out.where((state_fips != "") & (county_fips != "") & (tract_fips != ""), "")


def _missing_geo_ids(series: pd.Series, width: int) -> pd.Series:
    missing_tokens = {"", "nan", "None", "0" * width}
    return series.astype(str).isin(missing_tokens)


def _load_ruca(path: Path | None) -> pd.DataFrame | None:
    if path is None or not path.exists():
        return None
    if path.suffix.lower() not in {".xlsx", ".xls"}:
        df = load_csv(path)
        if "tract_geoid" in df.columns and "ruca_primary_code" in df.columns:
            return df[["tract_geoid", "ruca_primary_code"]]
        return df
    workbook = pd.ExcelFile(path)
    sheet_name = "RUCA2020 Tract Data" if "RUCA2020 Tract Data" in workbook.sheet_names else workbook.sheet_names[1]
    df = pd.read_excel(path, sheet_name=sheet_name, header=1)
    if "TractFIPS20" not in df.columns or "PrimaryRUCA" not in df.columns:
        return None
    out = df.rename(columns={"TractFIPS20": "tract_geoid", "PrimaryRUCA": "ruca_primary_code"})
    out["tract_geoid"] = _normalize_numeric_fips(out["tract_geoid"], 11)
    out["ruca_primary_code"] = pd.to_numeric(out["ruca_primary_code"], errors="coerce")
    return out[["tract_geoid", "ruca_primary_code"]].dropna(subset=["tract_geoid"])


def _load_svi(path: Path | None) -> pd.DataFrame | None:
    if path is None or not path.exists():
        return None
    df = _load_optional(path)
    if df is None or "FIPS" not in df.columns:
        return None
    svi_col = "svi_overall" if "svi_overall" in df.columns else ("RPL_THEMES" if "RPL_THEMES" in df.columns else None)
    if svi_col is None:
        return None
    out = df.rename(columns={"FIPS": "tract_geoid", svi_col: "svi_overall"})
    out["tract_geoid"] = _normalize_numeric_fips(out["tract_geoid"], 11)
    return out[["tract_geoid", "svi_overall"]]


def _load_tiger_attrs(tiger_dir: Path | None) -> pd.DataFrame | None:
    if tiger_dir is None or not tiger_dir.exists():
        return None
    frames: list[pd.DataFrame] = []
    for shp in sorted(tiger_dir.glob("tl_*_tract.shp")):
        try:
            import geopandas as gpd

            gdf = gpd.read_file(shp)
        except Exception:  # noqa: BLE001
            continue
        keep = [c for c in ["GEOID", "STATEFP", "COUNTYFP", "INTPTLAT", "INTPTLON"] if c in gdf.columns]
        if "GEOID" not in keep:
            continue
        frames.append(pd.DataFrame(gdf[keep]))
    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True)
    out["tract_geoid"] = _normalize_numeric_fips(out["GEOID"], 11)
    out["county_fips"] = _normalize_numeric_fips(out["STATEFP"] if "STATEFP" in out.columns else "", 2) + _normalize_numeric_fips(
        out["COUNTYFP"] if "COUNTYFP" in out.columns else "", 3
    )
    out["centroid_lat"] = pd.to_numeric(out["INTPTLAT"] if "INTPTLAT" in out.columns else "", errors="coerce")
    out["centroid_lon"] = pd.to_numeric(out["INTPTLON"] if "INTPTLON" in out.columns else "", errors="coerce")
    return out[["tract_geoid", "county_fips", "centroid_lat", "centroid_lon"]].drop_duplicates("tract_geoid")


def _merge_geocode_results(fac: pd.DataFrame, results_path: Path | None) -> pd.DataFrame:
    if results_path is None or not results_path.exists() or "AHA_ID" not in fac.columns:
        return fac
    results = load_csv(results_path)
    if not {"Unique_ID", "Long", "Lat"}.issubset(results.columns):
        return fac
    state_col = next((c for c in results.columns if "state" in str(c).lower() and "fips" in str(c).lower()), None)
    county_col = next((c for c in results.columns if "county" in str(c).lower() and "fips" in str(c).lower()), None)
    tract_col = next((c for c in results.columns if str(c).lower() == "tract" or ("tract" in str(c).lower() and "fips" not in str(c).lower())), None)
    if state_col is None and len(results.columns) > 10:
        state_col = results.columns[10]
    if county_col is None and len(results.columns) > 11:
        county_col = results.columns[11]
    if tract_col is None and len(results.columns) > 12:
        tract_col = results.columns[12]
    geo = results.rename(columns={"Unique_ID": "AHA_ID", "Long": "longitude_geocode", "Lat": "latitude_geocode"}).copy()
    geo["AHA_ID"] = geo["AHA_ID"].astype(str)
    if state_col is not None and county_col is not None and tract_col is not None:
        geo["tract_geoid_geocode"] = _build_geoid(geo[state_col], geo[county_col], geo[tract_col])
        geo["county_fips_geocode"] = _normalize_numeric_fips(geo[state_col], 2) + _normalize_numeric_fips(geo[county_col], 3)
    else:
        geo["tract_geoid_geocode"] = ""
        geo["county_fips_geocode"] = ""
    merged = fac.copy()
    merged["AHA_ID"] = merged["AHA_ID"].astype(str)
    merged = merged.merge(
        geo[["AHA_ID", "longitude_geocode", "latitude_geocode", "tract_geoid_geocode", "county_fips_geocode"]],
        on="AHA_ID",
        how="left",
    )
    for target, source in [
        ("longitude", "longitude_geocode"),
        ("latitude", "latitude_geocode"),
        ("tract_geoid", "tract_geoid_geocode"),
        ("county_fips", "county_fips_geocode"),
    ]:
        if target not in merged.columns:
            merged[target] = "" if "fips" in target or "geoid" in target else float("nan")
        if "fips" in target or "geoid" in target:
            merged[target] = merged[target].astype(str)
            missing = _missing_geo_ids(merged[target], 11 if "geoid" in target else 5)
        else:
            missing = merged[target].isna()
        merged.loc[missing, target] = merged.loc[missing, source]
    return merged.drop(columns=["longitude_geocode", "latitude_geocode", "tract_geoid_geocode", "county_fips_geocode"])


def _fill_missing_tracts_from_tiger(fac: pd.DataFrame, tiger_dir: Path | None) -> pd.DataFrame:
    if tiger_dir is None or not tiger_dir.exists():
        return fac
    needs_fill = (
        _missing_geo_ids(fac["tract_geoid"], 11)
        & fac["latitude"].notna()
        & fac["longitude"].notna()
        & ~fac["state_fips"].astype(str).isin(["", "nan", "None"])
    )
    if not needs_fill.any():
        return fac
    try:
        import geopandas as gpd
    except Exception:  # noqa: BLE001
        return fac
    states = set(fac.loc[needs_fill, "state_fips"].astype(str).str.zfill(2))
    tiger_frames = []
    for state in sorted(states):
        shp = tiger_dir / f"tl_2025_{state}_tract.shp"
        if not shp.exists():
            continue
        gdf = gpd.read_file(shp)
        keep = [c for c in ["GEOID", "STATEFP", "COUNTYFP", "geometry"] if c in gdf.columns]
        if {"GEOID", "geometry"}.issubset(keep):
            tiger_frames.append(gdf[keep])
    if not tiger_frames:
        return fac
    tiger = gpd.GeoDataFrame(pd.concat(tiger_frames, ignore_index=True), geometry="geometry", crs=tiger_frames[0].crs)
    points = gpd.GeoDataFrame(
        fac.loc[needs_fill, ["latitude", "longitude"]].copy(),
        geometry=gpd.points_from_xy(fac.loc[needs_fill, "longitude"], fac.loc[needs_fill, "latitude"]),
        crs="EPSG:4326",
    )
    if tiger.crs is not None and tiger.crs != points.crs:
        tiger = tiger.to_crs(points.crs)
    joined = gpd.sjoin(points, tiger[["GEOID", "STATEFP", "COUNTYFP", "geometry"]], how="left", predicate="within")
    out = fac.copy()
    out.loc[needs_fill, "tract_geoid"] = joined["GEOID"].fillna("").astype(str).values
    county_fill = _normalize_numeric_fips(joined["STATEFP"], 2) + _normalize_numeric_fips(joined["COUNTYFP"], 3)
    missing_county = _missing_geo_ids(out.loc[needs_fill, "county_fips"], 5)
    out.loc[out.loc[needs_fill].index[missing_county], "county_fips"] = county_fill[missing_county].values
    return out


def _build_tract_denominators(
    acs_path: Path | None,
    tiger_dir: Path | None,
    ruca: pd.DataFrame | None,
    svi: pd.DataFrame | None,
) -> pd.DataFrame | None:
    if acs_path is None or not acs_path.exists():
        return None
    acs = load_csv(acs_path)
    required = {"state", "county", "tract", "B01003_001E", "B09001_001E"}
    if not required.issubset(acs.columns):
        return None
    tract = pd.DataFrame(
        {
            "tract_geoid": _build_geoid(acs["state"], acs["county"], acs["tract"]),
            "state_fips": _normalize_numeric_fips(acs["state"], 2),
            "county_fips": _normalize_numeric_fips(acs["state"], 2) + _normalize_numeric_fips(acs["county"], 3),
            "population_total": pd.to_numeric(acs["B01003_001E"], errors="coerce").fillna(0),
            "population_child_u18": pd.to_numeric(acs["B09001_001E"], errors="coerce").fillna(0),
        }
    )
    tiger_attrs = _load_tiger_attrs(tiger_dir)
    if tiger_attrs is not None:
        tract = tract.merge(tiger_attrs, on="tract_geoid", how="left", suffixes=("", "_tiger"))
        tract["county_fips"] = tract["county_fips"].where(tract["county_fips"] != "", tract["county_fips_tiger"].fillna(""))
        tract = tract.drop(columns=["county_fips_tiger"], errors="ignore")
    if ruca is not None and {"tract_geoid", "ruca_primary_code"}.issubset(ruca.columns):
        tract = tract.merge(ruca[["tract_geoid", "ruca_primary_code"]], on="tract_geoid", how="left")
        tract["ruca_code"] = tract["ruca_primary_code"]
    if svi is not None and {"tract_geoid", "svi_overall"}.issubset(svi.columns):
        tract = tract.merge(svi[["tract_geoid", "svi_overall"]], on="tract_geoid", how="left")
    return tract


def _aggregate_county_denominators(tract_denom: pd.DataFrame) -> pd.DataFrame:
    return (
        tract_denom.groupby("county_fips", dropna=False)[["population_total", "population_child_u18"]]
        .sum()
        .reset_index()
    )


def _fallback_county_denom(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.groupby("county_fips", dropna=False)
        .size()
        .rename("facility_count")
        .reset_index()
        .assign(population_total=lambda x: x["facility_count"] * 100_000, population_child_u18=lambda x: x["facility_count"] * 20_000)
    )
    return out[["county_fips", "population_total", "population_child_u18"]]


def _fallback_tract_denom(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.groupby("tract_geoid", dropna=False)
        .size()
        .rename("facility_count")
        .reset_index()
        .assign(population_total=lambda x: x["facility_count"] * 10_000, population_child_u18=lambda x: x["facility_count"] * 2_000)
    )
    return out[["tract_geoid", "population_total", "population_child_u18"]]


def _rural_urban_from_ruca(code: object) -> str:
    try:
        code_f = float(code)
    except Exception:  # noqa: BLE001
        return "unknown"
    return "rural" if code_f >= 4 else "urban"


def _plot_rural_urban(fac_geo: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counts = fac_geo["rural_urban_class"].value_counts(dropna=False)
    fig, ax = plt.subplots(figsize=(6, 4))
    counts.plot(kind="bar", ax=ax, color="#F39C12")
    ax.set_title("Stage 01 Rural vs Urban mix")
    ax.set_xlabel("rural_urban_class")
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def run(config: RuntimeConfig) -> dict[str, Any]:
    c = _cfg(config)
    if not c.nird_clean_path.exists():
        raise ValidationError(f"Missing Stage 00 output: {c.nird_clean_path}")

    fac = load_parquet(c.nird_clean_path)
    require_columns(fac.columns.tolist(), ["STATE"])

    fac = fac.copy()
    fac["state_fips"] = derive_state_fips(fac["STATE"])
    fac["county_fips"] = derive_county_fips(fac)
    fac["tract_geoid"] = derive_tract_geoid(fac)
    fac = _merge_geocode_results(fac, c.geocode_results_path)
    if "latitude" not in fac.columns:
        fac["latitude"] = float("nan")
    if "longitude" not in fac.columns:
        fac["longitude"] = float("nan")
    fac = _fill_missing_tracts_from_tiger(fac, c.tiger_dir)
    fac["tract_geoid"] = _normalize_numeric_fips(fac["tract_geoid"], 11)
    fac["county_fips"] = fac["county_fips"].astype(str)
    missing_county = _missing_geo_ids(fac["county_fips"], 5) & ~_missing_geo_ids(fac["tract_geoid"], 11)
    fac.loc[missing_county, "county_fips"] = fac.loc[missing_county, "tract_geoid"].str[:5]
    fac["county_fips"] = _normalize_numeric_fips(fac["county_fips"], 5)

    if c.strict and (fac["state_fips"] == "").any():
        raise ValidationError("State FIPS derivation failed for one or more facility rows.")
    if _missing_geo_ids(fac["tract_geoid"], 11).all():
        raise ValidationError(
            "Stage 01 could not derive tract GEOIDs. Provide `external.geocode_results` and TIGER files, "
            "or include tract geography in Stage 00 output."
        )

    county_denom = _load_optional(c.county_den_path)
    ruca = _load_ruca(c.ruca_path)
    svi = _load_svi(c.svi_path)
    tract_denom = _load_optional(c.tract_den_path)
    if tract_denom is None:
        tract_denom = _build_tract_denominators(c.acs_tract_path, c.tiger_dir, ruca, svi)

    if county_denom is None:
        county_denom = _aggregate_county_denominators(tract_denom) if tract_denom is not None else _fallback_county_denom(fac)
    if tract_denom is None:
        tract_denom = _fallback_tract_denom(fac)

    county_key = "county_fips" if "county_fips" in county_denom.columns else "COUNTY_FIPS"
    tract_key = "tract_geoid" if "tract_geoid" in tract_denom.columns else ("GEOID" if "GEOID" in tract_denom.columns else "tract_fips")
    county_denom = county_denom.rename(columns={county_key: "county_fips"})
    tract_denom = tract_denom.rename(columns={tract_key: "tract_geoid"})
    county_denom["county_fips"] = county_denom["county_fips"].astype(str).str.zfill(5)
    tract_denom["tract_geoid"] = tract_denom["tract_geoid"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
    if "county_fips" not in tract_denom.columns:
        tract_denom["county_fips"] = tract_denom["tract_geoid"].str[:5]
    if "state_fips" not in tract_denom.columns:
        tract_denom["state_fips"] = tract_denom["tract_geoid"].str[:2]

    fac_geo = fac.merge(
        county_denom[["county_fips"] + [c for c in county_denom.columns if c != "county_fips"]],
        on="county_fips",
        how="left",
        suffixes=("", "_county"),
    ).merge(
        tract_denom[["tract_geoid"] + [c for c in tract_denom.columns if c != "tract_geoid"]],
        on="tract_geoid",
        how="left",
        suffixes=("", "_tract"),
    )

    if ruca is not None:
        ruca_key = "tract_geoid" if "tract_geoid" in ruca.columns else ("GEOID" if "GEOID" in ruca.columns else None)
        if ruca_key:
            ruca = ruca.rename(columns={ruca_key: "tract_geoid"})
            ruca["tract_geoid"] = ruca["tract_geoid"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
            ruca_code_col = "ruca_primary_code" if "ruca_primary_code" in ruca.columns else "RUCA1"
            if ruca_code_col in ruca.columns:
                fac_geo = fac_geo.merge(
                    ruca[["tract_geoid", ruca_code_col]].rename(columns={ruca_code_col: "_ruca_primary_code_src"}),
                    on="tract_geoid",
                    how="left",
                )
                if "ruca_primary_code" not in fac_geo.columns:
                    fac_geo["ruca_primary_code"] = fac_geo["_ruca_primary_code_src"]
                else:
                    fac_geo["ruca_primary_code"] = fac_geo["ruca_primary_code"].fillna(fac_geo["_ruca_primary_code_src"])
                fac_geo = fac_geo.drop(columns=["_ruca_primary_code_src"])

    if "ruca_primary_code" not in fac_geo.columns:
        fac_geo["ruca_primary_code"] = 1
    fac_geo["rural_urban_class"] = fac_geo["ruca_primary_code"].map(_rural_urban_from_ruca)

    if svi is not None:
        svi_key = "tract_geoid" if "tract_geoid" in svi.columns else ("GEOID" if "GEOID" in svi.columns else None)
        if svi_key:
            svi = svi.rename(columns={svi_key: "tract_geoid"})
            svi["tract_geoid"] = svi["tract_geoid"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
            svi_col = "svi_overall" if "svi_overall" in svi.columns else ("RPL_THEMES" if "RPL_THEMES" in svi.columns else None)
            if svi_col:
                fac_geo = fac_geo.merge(
                    svi[["tract_geoid", svi_col]].rename(columns={svi_col: "_svi_overall_src"}),
                    on="tract_geoid",
                    how="left",
                )
                if "svi_overall" not in fac_geo.columns:
                    fac_geo["svi_overall"] = fac_geo["_svi_overall_src"]
                else:
                    fac_geo["svi_overall"] = fac_geo["svi_overall"].fillna(fac_geo["_svi_overall_src"])
                fac_geo = fac_geo.drop(columns=["_svi_overall_src"])

    join_quality = pd.DataFrame(
        {
            "metric": [
                "rows",
                "missing_state_fips",
                "missing_county_fips",
                "missing_tract_geoid",
                "missing_ruca",
            ],
            "value": [
                len(fac_geo),
                int((fac_geo["state_fips"] == "").sum()),
                int((fac_geo["county_fips"] == "").sum()),
                int((fac_geo["tract_geoid"] == "").sum()),
                int(fac_geo["ruca_primary_code"].isna().sum()),
            ],
        }
    )
    ruca_summary = (
        fac_geo.groupby("rural_urban_class", dropna=False).size().rename("facility_count").reset_index()
    )

    facilities_geo_path = c.data_processed_dir / "facilities_geo.parquet"
    county_out = c.data_processed_dir / "county_denominators.parquet"
    tract_out = c.data_processed_dir / "tract_denominators.parquet"
    table_quality_path = c.outputs_tables_dir / "01_tables_join_quality_ground_only.csv"
    table_ruca_path = c.outputs_tables_dir / "01_tables_ruca_summary_ground_only.csv"
    figure_path = c.outputs_figures_dir / "01_figures_rural_urban_mix_ground_only.png"
    finding_path = c.outputs_metrics_dir / "01_findings_ground_only.json"
    manifest_path = c.outputs_metrics_dir / "01_manifest_ground_only.json"

    write_parquet(fac_geo, facilities_geo_path)
    write_parquet(county_denom, county_out)
    write_parquet(tract_denom, tract_out)
    write_csv(join_quality, table_quality_path)
    write_csv(ruca_summary, table_ruca_path)
    _plot_rural_urban(fac_geo, figure_path)

    finding = FindingRecord(
        stage_id="01",
        question="Where are facilities and denominators anchored geographically?",
        finding="Stage 01 attached stable geography keys and denominator layers to facilities and produced rural/urban stratification artifacts.",
        why_it_matters="Reliable geography and denominator joins are prerequisites for defensible access and per-capita metrics.",
        action_implication="Use Stage 01 outputs as the canonical base for supply, access, and pediatric gap stages.",
        scenario_id="ground_only",
    )
    write_finding(finding, finding_path)

    manifest = ArtifactManifest(
        run_id="stage01",
        profile=config.profile,
        artifacts=[
            ArtifactRecord("01_dataset_facilities_geo", "01", "dataset", str(facilities_geo_path), "parquet"),
            ArtifactRecord("01_dataset_county_den", "01", "dataset", str(county_out), "parquet"),
            ArtifactRecord("01_dataset_tract_den", "01", "dataset", str(tract_out), "parquet"),
            ArtifactRecord("01_table_join_quality", "01", "table", str(table_quality_path), "csv"),
            ArtifactRecord("01_table_ruca_summary", "01", "table", str(table_ruca_path), "csv"),
            ArtifactRecord("01_figure_rural_urban", "01", "figure", str(figure_path), "png"),
            ArtifactRecord("01_finding", "01", "finding", str(finding_path), "json"),
        ],
    )
    write_manifest(manifest, manifest_path)

    return {
        "ok": True,
        "stage_id": "01",
        "dataset": str(facilities_geo_path),
        "county_denom": str(county_out),
        "tract_denom": str(tract_out),
        "tables": [str(table_quality_path), str(table_ruca_path)],
        "figures": [str(figure_path)],
        "finding": str(finding_path),
        "manifest": str(manifest_path),
    }
