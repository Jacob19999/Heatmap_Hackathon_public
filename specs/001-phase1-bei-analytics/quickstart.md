# Quickstart: Phase 1 — BEI Analytics Pipeline

**Feature**: 001-phase1-bei-analytics
**Date**: 2026-03-14

## Prerequisites

- Python 3.11+
- Docker (for self-hosted OSRM)
- ~20 GB disk space (OSM extract + TIGER shapefiles + OSRM data)
- Internet access for data downloads

## 1. Create Python Environment

```bash
cd Heatmap_Hackathon
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 2. Install Dependencies

Create `requirements.txt` at the project root:

```text
pandas>=2.1
geopandas>=0.14
numpy>=1.26
scipy>=1.11
scikit-learn>=1.3
hdbscan>=0.8.33
esda>=2.5
libpysal>=4.9
matplotlib>=3.8
seaborn>=0.13
plotly>=5.18
folium>=0.15
openpyxl>=3.1
shapely>=2.0
requests>=2.31
pyarrow>=14.0
tqdm>=4.66
cenpy>=1.0
```

## 3. Download External Data

### ACS 5-Year (2022)

Download tract-level population tables via Census API or `data.census.gov`:
- Table B01003 (Total Population)
- Table B09001 (Population Under 18)

Save to `Data/external/acs/`.

### TIGER/Line Shapefiles (2022)

```bash
# Download tract shapefiles (one per state, or national file)
# From: https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2022&layergroup=Census+Tracts
```

Save to `Data/external/tiger/`.

### RUCA Codes

Download from: https://www.ers.usda.gov/data-products/rural-urban-commuting-area-codes/

Save to `Data/external/ruca/`.

### CDC SVI (Optional)

Download from: https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html

Save to `Data/external/svi/`.

### FAA Airport/Heliport Data

Download from: https://www.faa.gov/data

Save to `Data/external/faa/`.

## 4. Set Up OSRM (Docker)

```bash
# Download US OSM extract (~10 GB)
wget https://download.geofabrik.de/north-america/us-latest.osm.pbf -P Data/external/osrm/

# Extract, partition, and customize
docker run -t -v "$(pwd)/Data/external/osrm:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/us-latest.osm.pbf
docker run -t -v "$(pwd)/Data/external/osrm:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/us-latest.osrm
docker run -t -v "$(pwd)/Data/external/osrm:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/us-latest.osrm

# Start the routing server
docker run -t -d -p 5000:5000 -v "$(pwd)/Data/external/osrm:/data" ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/us-latest.osrm

# Verify it's running
curl "http://localhost:5000/table/v1/driving/-73.9857,40.7484;-87.6298,41.8781"
```

## 5. Run the Pipeline

Once all data is downloaded and OSRM is running:

```bash
# Stage 1: Data foundation
python -m src.pipeline.ingest
python -m src.pipeline.geocode
python -m src.pipeline.augment

# Stage 2: Challenge outputs (basic, pre-routing)
# Run notebook: src/notebooks/02_challenge_outputs.ipynb

# Stage 3: Routing and access
python -m src.pipeline.routing
python -m src.pipeline.access

# Stage 4: BEI computation
python -m src.pipeline.bei_components
python -m src.pipeline.bei_composite
python -m src.pipeline.aggregation

# Stage 5: Air scenario (no Valhalla: closest airport + straight-line distance only)
python -m src.pipeline.air_scenario          # optional: --mn-only for faster test
# Re-run access + BEI under air scenario

# Stage 6: Hotspots and ML
python -m src.pipeline.hotspot
python -m src.pipeline.priority
python -m src.pipeline.sensitivity

# Stage 7: Export and visualize
python -m src.pipeline.export
python -m src.pipeline.visualize
```

Or use notebooks for interactive exploration at each stage.

### Dual-path presentation build

For the current product design, publish two frontend paths from the same analytics pipeline:

- `mn_high_detail` — Minnesota tract-level detail
- `usa_low_detail_county` — national county-level detail

**Validated run sequence** (run from repo root):

```bash
# 1. Minnesota high-detail path (tract access + BEI, mn_high_detail_manifest.json)
python -m src.pipeline.mn_mvp_pipeline

# 2. USA low-detail county path: build county–hospital matrix, then access + BEI
#    (Valhalla must be running; optional: set VALHALLA_CONTAINER_NAME to restart after chunks)
python -m src.pipeline.usa_low_detail_county_valhalla
python -m src.pipeline.usa_low_detail_county

# 3. Export: profile GeoJSON + product_views_manifest.json
python -m src.pipeline.export

# 4. Visualize: MN tract and USA county BEI maps
python -m src.pipeline.visualize
```

**One-command option** (runs MN pipeline + USA county pipeline + product views manifest; then run export and visualize separately):

```bash
python -m src.pipeline.run_dual_path_pipeline
python -m src.pipeline.export
python -m src.pipeline.visualize
```

Recommended behavior for the dual-path build:

- Keep production ingestion pointed at `Data/NIRD 20230130 Database_Hackathon_full_ai_ignore.xlsx`
- Prefer the Minnesota-specific filled matrix when present for the tract-detail path
- Export Minnesota high-detail payloads with a scope prefix such as `mn_high_detail_`
- Route the USA low-detail path from county centroids directly to hospitals rather than from all U.S. tracts
- Export USA low-detail payloads with a scope prefix such as `usa_low_detail_county_`
- Write one manifest per dataset profile plus a product-level views manifest for the frontend tabs

## 6. Verify Outputs

After the pipeline completes, check:

```
Data/output/
├── tables/
│   ├── tract_ground_v1.parquet
│   ├── tract_air_v1.parquet
│   ├── tract_delta_v1.parquet
│   ├── county_ground_v1.parquet
│   ├── state_ground_v1.parquet
│   ├── hotspot_v1.parquet
│   └── facilities_v1.parquet
├── geojson/
│   ├── tract_bei_ground.geojson
│   ├── tract_bei_air.geojson
│   ├── tract_delta.geojson
│   ├── tract_hotspot.geojson
│   ├── facilities.geojson
│   └── county_bei_ground.geojson
└── figures/
    ├── national_bei_choropleth.png
    ├── rural_urban_comparison.png
    ├── scenario_delta_map.png
    ├── hotspot_map.png
    └── archetype_profiles.png
```

For the dual-path product build, also expect scope-specific payloads and manifests, for example:

```text
Data/output/
├── manifests/
│   ├── mn_high_detail_manifest.json
│   ├── usa_low_detail_county_manifest.json
│   └── product_views_manifest.json
├── tables/
│   ├── mn_high_detail_tract_bei.parquet
│   ├── mn_high_detail_tract_access.parquet
│   ├── usa_low_detail_county_county_bei.parquet
│   └── usa_low_detail_county_county_access.parquet
├── geojson/
│   ├── mn_high_detail_tract_bei_ground.geojson
│   └── usa_low_detail_county_county_bei.geojson
└── figures/
    ├── mn_high_detail_tract_bei_map.png
    └── usa_low_detail_county_county_bei_map.png
```

### Direct-output publication (both profiles)

Challenge-specific direct outputs (burn center distribution, rural/urban travel burden, pediatric access, burn-bed capacity) are published as follows:

- **mn_high_detail**: Tract-level BEI and access tables (`mn_high_detail_tract_bei.parquet`, `mn_high_detail_tract_access.parquet`) and tract BEI GeoJSON (`mn_high_detail_tract_bei_ground.geojson`). County/state rollups can be produced from the tract table via `aggregation.aggregate_to_county` / `aggregate_to_state`. Companion metrics (e.g. burn centers per 100k, pediatric access) are in `bei_composite` and used by the pipeline.
- **usa_low_detail_county**: County-level BEI and access tables (`usa_low_detail_county_county_bei.parquet`, `usa_low_detail_county_county_access.parquet`) and county BEI GeoJSON (`usa_low_detail_county_county_bei.geojson`). These are the primary direct-output tables for the low-detail frontend tab. Profile manifest and product_views_manifest reference these assets.

Run `python -m src.pipeline.export` after the dual-path build to refresh GeoJSON and manifests.

## 7. Sanity Checks

Run the sanity test suite:

```bash
pytest src/tests/test_sanity.py -v
```

**Dual-path validation**: After running the dual-path build (mn_mvp_pipeline, usa_low_detail_county, export, visualize), verify manifests and contracts:

```bash
cd src
pytest tests/test_export_contracts.py tests/test_sanity.py -v
```

This checks that presentation and product_views manifests exist and satisfy the schema (required keys, view count, geography levels).

This verifies:
- BEI composite = weighted sum of components
- System time ≤ direct time for all tracts
- Components bounded [0, 1]
- Zero-burn-center states rank in top BEI quartile
- All output files exist and pass schema validation

## Key Configuration

All parameters are in `src/pipeline/config.py`. Scope-specific paths and labels should be centralized in a dataset-profile layer so both the Minnesota high-detail path and the USA low-detail county path can be published without changing frontend logic. To run sensitivity analysis, modify the sweep ranges there and re-run `python -m src.pipeline.sensitivity`.

## Data Governance Reminder

- **DO NOT** share `Data/NIRD 20230130 Database_Hackathon_full_ai_ignore.xlsx` with AI tools
- The sample file `Data/NIRD 20230130 Database_Hackathon_sample.xlsx` may be shared with AI for development assistance
- All code points to the full file; the sample is for AI schema reference only
