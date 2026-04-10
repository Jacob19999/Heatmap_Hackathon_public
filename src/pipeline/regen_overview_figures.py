"""
Regenerate overview figures with proper choropleth maps and a highest-BEI table.
"""
from __future__ import annotations
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
import geopandas as gpd

from . import config

DPI = 200
TIGER = Path("Data/external/tiger")

GREEN_RED_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "bei_gr",
    ["#1a9850", "#66bd63", "#a6d96a", "#d9ef8b",
     "#fee08b", "#fdae61", "#f46d43", "#d73027", "#a50026"],
)

DARK_BG = "#0F1923"
CARD_BG = "#1A2634"
TEXT = "#E8ECF1"
MUTED = "#8899AA"
BORDER = "#2A3A4A"
ACCENT = "#E85D04"


def _load_mn_bei() -> pd.DataFrame:
    return pd.read_parquet("Data/output/tables/mn_bei_recomputed.parquet")


def _load_usa_bei() -> pd.DataFrame:
    return pd.read_parquet("Data/output/tables/usa_bei_recomputed.parquet")


def _load_fac() -> pd.DataFrame:
    return pd.read_parquet("Data/processed/facilities_geo.parquet")


def _load_county_names() -> dict:
    p = Path("outputs/dashboard/mn_county_names.json")
    if p.exists():
        return json.loads(p.read_text())
    return {}


# ── MN Choropleth ──────────────────────────────────────────────────────────
def gen_mn_bei_map(out_dir: Path):
    print("  Generating MN choropleth map...")
    gdf = gpd.read_file(TIGER / "tl_2025_27_tract.shp").to_crs("EPSG:4326")
    bei = _load_mn_bei()
    merged = gdf.merge(bei[["GEOID", "bei"]], on="GEOID", how="left")

    fac = _load_fac()
    mn_fac = fac[
        fac["latitude"].notna() &
        (fac["latitude"] > 43) & (fac["latitude"] < 50) &
        (fac["longitude"] > -98) & (fac["longitude"] < -88)
    ]

    fig, ax = plt.subplots(figsize=(11, 13), facecolor=DARK_BG)
    ax.set_facecolor(DARK_BG)

    merged.plot(
        ax=ax, column="bei", cmap=GREEN_RED_CMAP,
        vmin=0, vmax=100, edgecolor="#1A263488", linewidth=0.15,
        missing_kwds={"color": "#333"},
    )

    ax.scatter(
        mn_fac["longitude"], mn_fac["latitude"],
        s=50, c=ACCENT, edgecolors="white", linewidth=0.8,
        zorder=10, marker="o", label="Burn Centers",
    )

    sm = plt.cm.ScalarMappable(cmap=GREEN_RED_CMAP, norm=plt.Normalize(0, 100))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.45, pad=0.02, aspect=25)
    cbar.set_label("Burn Equity Index", fontsize=11, color=TEXT, labelpad=8)
    cbar.ax.tick_params(colors=TEXT, labelsize=9)
    cbar.outline.set_edgecolor(BORDER)

    p90 = bei["bei"].quantile(0.9)
    n_hot = (bei["bei"] >= p90).sum()
    pop_hot = bei.loc[bei["bei"] >= p90, "total_pop"].sum()

    ax.set_title(
        "Burn Equity Index — Minnesota Tracts",
        fontsize=18, fontweight="bold", color=TEXT, pad=16, loc="left",
    )
    ax.text(
        0.0, 1.01,
        f"{n_hot} high-burden tracts (top 10%) affecting {pop_hot:,.0f} residents",
        transform=ax.transAxes, fontsize=11, color=MUTED, va="bottom",
    )
    ax.legend(
        loc="lower right", fontsize=10,
        facecolor=CARD_BG, edgecolor=BORDER,
        labelcolor=TEXT, framealpha=0.9,
    )
    ax.set_xlim(-97.5, -89)
    ax.set_ylim(43, 49.5)
    ax.set_axis_off()
    fig.tight_layout()

    path = out_dir / "mn_06_bei_map.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"    -> {path}")


# ── USA Choropleth ─────────────────────────────────────────────────────────
def gen_usa_bei_map(out_dir: Path):
    print("  Generating USA choropleth map...")
    bei = _load_usa_bei()
    bei["county_fips"] = bei["county_fips"].astype(str).str.zfill(5)
    bei["state_fips_2"] = bei["county_fips"].str[:2]

    lower48_fips = {
        "01","04","05","06","08","09","10","11","12","13",
        "16","17","18","19","20","21","22","23","24","25",
        "26","27","28","29","30","31","32","33","34","35",
        "36","37","38","39","40","41","42","44","45","46",
        "47","48","49","50","51","53","54","55","56",
    }
    bei = bei[bei["state_fips_2"].isin(lower48_fips)].copy()

    all_tracts = []
    for sf in lower48_fips:
        shp = TIGER / f"tl_2025_{sf}_tract.shp"
        if shp.exists():
            g = gpd.read_file(shp).to_crs("EPSG:4326")
            g = g.dissolve(by="COUNTYFP", aggfunc="first").reset_index()
            g["county_fips"] = g["STATEFP"] + g["COUNTYFP"]
            g = g[["county_fips", "geometry"]]
            all_tracts.append(g)

    counties = pd.concat(all_tracts, ignore_index=True)
    counties = counties.dissolve(by="county_fips").reset_index()
    merged = counties.merge(bei[["county_fips", "bei"]], on="county_fips", how="left")
    merged = gpd.GeoDataFrame(merged, geometry="geometry")

    fac = _load_fac()
    fac_48 = fac[
        fac["latitude"].notna() &
        (fac["latitude"] > 24) & (fac["latitude"] < 50) &
        (fac["longitude"] > -130) & (fac["longitude"] < -65)
    ]

    fig, ax = plt.subplots(figsize=(16, 10), facecolor=DARK_BG)
    ax.set_facecolor(DARK_BG)

    merged.plot(
        ax=ax, column="bei", cmap=GREEN_RED_CMAP,
        vmin=0, vmax=100, edgecolor="#1A263444", linewidth=0.08,
        missing_kwds={"color": "#222"},
    )
    ax.scatter(
        fac_48["longitude"], fac_48["latitude"],
        s=18, c=ACCENT, edgecolors="white", linewidth=0.4,
        zorder=10, marker="o", alpha=0.9, label="Burn Centers",
    )

    sm = plt.cm.ScalarMappable(cmap=GREEN_RED_CMAP, norm=plt.Normalize(0, 100))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.4, pad=0.02, aspect=25)
    cbar.set_label("Burn Equity Index", fontsize=11, color=TEXT, labelpad=8)
    cbar.ax.tick_params(colors=TEXT, labelsize=9)
    cbar.outline.set_edgecolor(BORDER)

    n_high = (bei["bei"] >= bei["bei"].quantile(0.9)).sum()
    pop_high = bei.loc[bei["bei"] >= bei["bei"].quantile(0.9), "total_pop"].sum()
    ax.set_title(
        "National Burn Equity Index — County Level",
        fontsize=18, fontweight="bold", color=TEXT, pad=16, loc="left",
    )
    ax.text(
        0.0, 1.01,
        f"{n_high} high-burden counties (top 10%) affecting {pop_high:,.0f} residents",
        transform=ax.transAxes, fontsize=11, color=MUTED, va="bottom",
    )
    ax.legend(
        loc="lower right", fontsize=10,
        facecolor=CARD_BG, edgecolor=BORDER,
        labelcolor=TEXT, framealpha=0.9,
    )
    ax.set_xlim(-126, -66)
    ax.set_ylim(24, 50)
    ax.set_axis_off()
    fig.tight_layout()

    path = out_dir / "usa_01_county_bei_map.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"    -> {path}")


# ── Highest-BEI Table ──────────────────────────────────────────────────────
def gen_highest_bei_table(out_dir: Path):
    print("  Generating highest-BEI table...")
    bei = _load_mn_bei()
    county_names = _load_county_names()

    if "COUNTYFP" not in bei.columns or "NAMELSAD" not in bei.columns:
        gdf = gpd.read_file(TIGER / "tl_2025_27_tract.shp")[["GEOID", "COUNTYFP", "NAMELSAD"]]
        gdf["GEOID"] = gdf["GEOID"].astype(str)
        bei["GEOID"] = bei["GEOID"].astype(str)
        bei = bei.merge(gdf, on="GEOID", how="left")

    cfp = "COUNTYFP" if "COUNTYFP" in bei.columns else "COUNTYFP_y"
    nls = "NAMELSAD" if "NAMELSAD" in bei.columns else "NAMELSAD_y"
    bei["county_name"] = bei[cfp].map(county_names).fillna("Unknown")
    bei["tract_name"] = bei[nls].fillna("Tract")

    top = bei.nlargest(25, "bei").reset_index(drop=True)
    top.index = top.index + 1

    fig, ax = plt.subplots(figsize=(14, 10), facecolor=DARK_BG)
    ax.set_facecolor(DARK_BG)
    ax.set_axis_off()

    ax.set_title(
        "Highest-Burden Census Tracts in Minnesota",
        fontsize=18, fontweight="bold", color=TEXT, pad=20, loc="left",
    )
    ax.text(
        0.0, 1.01, "Top 25 tracts ranked by Burn Equity Index",
        transform=ax.transAxes, fontsize=11, color=MUTED, va="bottom",
    )

    cols = ["Rank", "Tract", "County", "BEI", "Travel\n(min)", "Pop", "Type",
            "S", "T", "P", "C"]
    rows = []
    for i, (_, r) in enumerate(top.iterrows()):
        rows.append([
            str(i + 1),
            str(r.get("tract_name", ""))[:22],
            str(r.get("county_name", ""))[:18],
            f"{r['bei']:.1f}",
            f"{r['t_sys']:.0f}" if pd.notna(r.get("t_sys")) else "—",
            f"{int(r['total_pop']):,}" if pd.notna(r.get("total_pop")) else "—",
            "Rural" if r.get("is_rural") else "Urban",
            f"{r['s_score']:.2f}",
            f"{r['t_score']:.2f}",
            f"{r['p_score']:.2f}",
            f"{r['c_score']:.2f}",
        ])

    table = ax.table(
        cellText=rows, colLabels=cols,
        loc="center", cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.45)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(BORDER)
        if row == 0:
            cell.set_facecolor(ACCENT)
            cell.set_text_props(color="white", fontweight="bold", fontsize=9)
            cell.set_height(0.06)
        else:
            cell.set_facecolor(CARD_BG if row % 2 == 0 else "#1E2E3E")
            cell.set_text_props(color=TEXT)
            if col == 3:
                bei_val = float(cell.get_text().get_text())
                if bei_val >= 80:
                    cell.set_text_props(color="#f46d43", fontweight="bold")
                elif bei_val >= 60:
                    cell.set_text_props(color="#fdae61", fontweight="bold")

    fig.tight_layout()
    path = out_dir / "mn_08_hotspot_table.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"    -> {path}")


# ── Entry point ────────────────────────────────────────────────────────────
def regenerate_all():
    out_dir = config.FIGURES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    gen_mn_bei_map(out_dir)
    gen_usa_bei_map(out_dir)
    gen_highest_bei_table(out_dir)
    print("Done — all overview figures regenerated.")


if __name__ == "__main__":
    regenerate_all()
