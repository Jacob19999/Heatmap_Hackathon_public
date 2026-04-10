# Data Sources for the Burn Equity Index

This file documents the data stack for the Burn Equity Index (BEI) and clarifies which inputs are challenge-provided versus public/free augmentation layers.

## Core source statement

**The model uses challenge-provided NIRD + public/free augmentation layers.**

That wording is the most accurate description of the project data stack.

---

## 1) Base dataset

| Source | Status | Role in BEI | Notes |
|---|---|---|---|
| `NIRD` | **Challenge-provided** | Base hospital infrastructure layer | Use as the primary source for burn center flags, trauma designations, geographic hospital records, and `BURN_BEDS`. Do not describe this file as a standard public open-data download unless you later confirm a public release source. |

---

## 2) Public/free augmentation layers

These sources are publicly accessible or free to use and can be combined with NIRD for population denominators, rurality, transport modeling, and contextual overlays.

| Source | Public/free? | Official access | Geography / format | Use in BEI | Notes |
|---|---|---|---|---|---|
| `American Community Survey (ACS) 5-year` | Yes | https://www.census.gov/programs-surveys/acs/data/data-via-api.html | API tables for tract, county, and related Census geographies | Total population, child population, poverty, no-vehicle, optional social context | Best source for population denominators and tract/county attributes. |
| `TIGER/Line shapefiles` | Yes | https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html | Shapefiles / geospatial boundaries | County and tract geometry, mapping, centroids, spatial joins | Use for tract/county polygons and map outputs. |
| `Census Geocoder` | Yes | https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html | Web/API geocoding and batch address matching | Convert hospital records to coordinates and Census geography | Useful if address cleaning or boundary assignment is needed. |
| `USDA ERS RUCA codes` | Yes | https://www.ers.usda.gov/data-products/rural-urban-commuting-area-codes/ | Downloadable tract / ZIP tables | Rural vs urban classification | Best tract-level rurality layer for stratified access analysis. |
| `CDC/ATSDR Social Vulnerability Index (SVI)` | Yes | https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html | CSV / geodatabase | Optional contextual overlay | Useful as a secondary interpretation layer, not required as a core BEI pillar. |
| `OpenStreetMap road network` | Yes | https://www.openstreetmap.org and https://download.geofabrik.de/ | Open road-network geodata | Base road layer for routing and drive-time estimation | Public/open source road network. |
| `OSRM` | Yes, with caveats | https://project-osrm.org/docs/v5.24.0/api/ | Open-source routing engine and API | Road-network drive time, transfer-path estimation | Good for road access. Public demo server is not ideal for large national batch jobs; self-hosting is better for production-scale analysis. |
| `FAA airport / heliport infrastructure data` | Yes | https://www.faa.gov/data | Public airport and heliport infrastructure records | Air-access sensitivity scenario | Appropriate for identifying where air transport may be physically plausible. This supports a structural air-access scenario, not real-time helicopter availability. |

---

## 3) How each source maps to the methodology

### A. Specialized supply and burn capability
Use `NIRD` for:
- hospital location records
- adult / pediatric burn capability flags
- trauma designations
- burn-center verification / designation fields
- `BURN_BEDS`

### B. Population denominators
Use `ACS` for:
- total population
- child population
- optional poverty / no-vehicle fields

### C. Geography and mapping
Use:
- `TIGER/Line` for tract and county boundaries
- `Census Geocoder` for hospital-to-geography assignment when needed

### D. Rurality
Use `RUCA` for:
- rural vs urban classification
- stratified analysis of timely access burden

### E. Road access
Use:
- `OpenStreetMap` as the base road network
- `OSRM` for road travel time between origins, stabilization hospitals, and definitive burn centers

### F. Air access sensitivity scenario
Use:
- `FAA airport / heliport infrastructure data`
- hospital coordinates from `NIRD`
- optional geospatial support from `OpenStreetMap` / `TIGER`

This air layer should be used conservatively. It supports a **public-data structural air-access scenario** by approximating whether air movement may be feasible between an origin area, a launch/landing point, and a destination facility.

It should **not** be described as:
- real-time medevac dispatch availability
- live helicopter base coverage
- guaranteed clinical air transfer time

So the recommended framing is:
- **ground-only baseline**, and
- **conditional ground+air sensitivity scenario**

---

## 4) Recommended transport-data wording

Use wording like this in methodology sections:

> The model uses challenge-provided NIRD + public/free augmentation layers. Road access is estimated from OpenStreetMap/OSRM, while air access is modeled only as a public-data sensitivity scenario using FAA airport/heliport infrastructure and related geospatial linkages.

Avoid wording like this:

> The methodology relies only on publicly available data.

That stronger claim is inaccurate unless `NIRD` is independently confirmed as public.

Also avoid wording like this:

> Air transport times represent actual helicopter transport availability.

That claim is too strong unless you obtain operational dispatch data.

---

## 5) Final recommended source stack for the project

### Required core stack
1. `NIRD` *(challenge-provided)*
2. `ACS 5-year`
3. `TIGER/Line shapefiles`
4. `RUCA`
5. `OpenStreetMap + OSRM`

### Recommended optional context layers
6. `Census Geocoder`
7. `CDC/ATSDR SVI`
8. `FAA airport / heliport infrastructure data` *(for air-access sensitivity only)*

---

## 6) Practical summary

The BEI is best described as a model that combines:
- **challenge-provided NIRD** for burn-care supply and hospital capability, and
- **public/free augmentation layers** for population, rurality, mapping, road routing, and optional air-access sensitivity analysis.

That is the cleanest and most defensible description for the methodology, research narrative, and judging presentation.
