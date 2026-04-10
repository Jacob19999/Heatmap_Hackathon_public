# Challenge Area 3 — Burn Equity Method Notes

Generated: 2026-03-17T00:26:19.270827+00:00

## Data Sources
- **NIRD**: 635 facilities from NIRD 20230130 Database (full hackathon dataset)
- **ACS**: 5-year 2022 tract-level population (B01003, B09001)
- **TIGER**: 2025 tract shapefiles for geometry and centroids
- **RUCA**: 2020 rural-urban commuting area codes
- **SVI**: CDC/ATSDR 2022 Social Vulnerability Index
- **Routing**: Valhalla-computed ground travel times (MN high-detail)

## Pipeline
- **MN High Detail**: 1,505 tracts, Valhalla-routed travel times to 25 MN/regional hospitals
- **USA Low Detail**: 3,144 counties, Valhalla-routed travel times
- **BEI**: 4-pillar composite (Supply 25%, Travel 30%, Pediatric 20%, Capacity 25%)
  - Supply: step-decay-weighted count of accessible burn centers
  - Travel: robust-normalized system travel time (min of direct or transfer pathway)
  - Pediatric: haversine-proxy travel to 3rd-nearest center (pediatric specialization proxy)
  - Capacity: step-decay-weighted burn bed availability

## Methodological Constraints
- All capacity metrics are **structural** (not real-time bed availability)
- Air transport outputs are **scenario-based sensitivity**, not operational truth
- Pediatric metrics are separated from adult metrics
- Need overlays (SVI, burden) are attached as overlays, not mixed into BEI
