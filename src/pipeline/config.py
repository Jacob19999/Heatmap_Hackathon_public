"""
Pipeline configuration: paths, BEI weights, scenario parameters.
All paths are relative to the repository root (project root).
"""
import os
from pathlib import Path

# --- Repository root (assume run from repo root or adjust via env) ---
REPO_ROOT = Path(__file__).resolve().parents[2]

# --- Data paths ---
DATA_DIR = REPO_ROOT / "Data"
NIRD_FULL_PATH = DATA_DIR / "NIRD 20230130 Database_Hackathon.xlsx"
NIRD_SAMPLE_PATH = DATA_DIR / "NIRD 20230130 Database_Hackathon_sample.xlsx"
DATA_MAPPING_PATH = DATA_DIR / "Data_Mapping_Document.pdf"

EXTERNAL_DIR = DATA_DIR / "external"
ACS_DIR = EXTERNAL_DIR / "acs"
TIGER_DIR = EXTERNAL_DIR / "tiger"
RUCA_DIR = EXTERNAL_DIR / "ruca"
# Expected manual RUCA file (ERS 2020 tract-level)
RUCA_MANUAL_FILENAME = "RUCA-codes-2020-tract.xlsx"
SVI_DIR = EXTERNAL_DIR / "svi"
# CDC/ATSDR SVI tract CSV (e.g. SVI_2022_US.csv); use first matching CSV in SVI_DIR if not found
SVI_CSV_FILENAME = "SVI_2022_US.csv"
OSRM_DIR = EXTERNAL_DIR / "osrm"
FAA_DIR = EXTERNAL_DIR / "faa"

OUTPUT_DIR = DATA_DIR / "output"
TABLES_DIR = OUTPUT_DIR / "tables"
# Cached travel-time matrix (origin_id, destination_id, duration_min)
TRAVEL_TIME_MATRIX_PATH = TABLES_DIR / "travel_time_matrix.parquet"
GEOJSON_DIR = OUTPUT_DIR / "geojson"
FIGURES_DIR = OUTPUT_DIR / "figures"
# Scope-aware presentation manifests (one per dataset profile)
MANIFESTS_DIR = OUTPUT_DIR / "manifests"

# Default dataset profile used for Phase 1 presentation runs
DEFAULT_PROFILE_ID = "mn_high_detail"

# --- BEI weights (Constitution §4.2): S, T, P, C ---
BEI_WEIGHTS = (0.25, 0.30, 0.20, 0.25)  # S, T, P, C

# --- T component sub-weights (system time vs tier penalty) ---
T_SYS_WEIGHT = 0.75
T_DELTA_WEIGHT = 0.25

# --- Step-decay bands (minutes) and weights ---
STEP_DECAY_BANDS_MIN = (30, 60, 90)  # t <= 30, 30 < t <= 60, 60 < t <= 90, t > 90
STEP_DECAY_WEIGHTS = (1.0, 0.60, 0.30, 0.0)  # g(t) at each band

# --- Transfer and stabilization ---
TRANSFER_PENALTY_MIN = 45
STABILIZATION_THRESHOLD_MIN = 30

# --- Normalization ---
NORM_LOW_PERCENTILE = 5
NORM_HIGH_PERCENTILE = 95

# --- Capacity utilization (structural beds) ---
CAPACITY_UTILIZATION = 1.0

# --- Need overlay and priority (Methodology §8) ---
NEED_OVERLAY_ALPHA = 0.5
PRIORITY_LAMBDA = 0.5

# --- Air scenario (conditional, no Valhalla: closest airport + straight-line) ---
AIR_DISPATCH_MIN = 10
AIR_HANDOFF_MIN = 15
AIR_CRUISE_SPEED_MPH = 150
GROUND_TO_LAUNCH_MAX_MIN = 30
# Estimated ground speed (km/h) for tract→airport and airport→facility legs (straight-line / speed).
AIR_GROUND_SPEED_KMH = 50.0

# --- Sensitivity sweep ranges (for FR-018) ---
SENSITIVITY_TRANSFER_PENALTY = (30, 45, 60)
SENSITIVITY_CAPACITY_UTILIZATION = (1.0, 0.75)
SENSITIVITY_NEED_ALPHA = (0.3, 0.5, 0.7)
SENSITIVITY_PRIORITY_LAMBDA = (0.25, 0.5, 1.0)

# --- OSRM ---
OSRM_BASE_URL = "http://127.0.0.1:5000"
OSRM_TABLE_SERVICE = "/table/v1/driving"
# Parallel requests for table API (1 = sequential; 4–8 typical for faster runs)
OSRM_MAX_WORKERS = 6

# --- Routing backend ---
# "valhalla" (default) or "osrm"
ROUTING_ENGINE = "valhalla"

# Valhalla matrix endpoint (sources_to_targets)
# Use the higher-resource Valhalla container on port 8003.
VALHALLA_BASE_URL = "http://127.0.0.1:8003"
VALHALLA_MATRIX_SERVICE = "/sources_to_targets"
VALHALLA_REQUEST_TIMEOUT = 120  # seconds per matrix request (increase if Read timed out often)
# Optional: Docker container name to restart after each county chunk (reduces OOM).
# Set in code, or via env VALHALLA_CONTAINER_NAME (e.g. "valhalla-hires"); None/empty = no restart.
VALHALLA_CONTAINER_NAME: str | None = os.environ.get("VALHALLA_CONTAINER_NAME") or None
if VALHALLA_CONTAINER_NAME is not None:
    VALHALLA_CONTAINER_NAME = VALHALLA_CONTAINER_NAME.strip() or None

# --- Haversine prefilter for routing ---
# Skip OSRM for facility-tract pairs farther than this air-line distance.
# 300 km Haversine ≈ 400+ km road ≈ 3.5+ h driving — well beyond the 90-min
# step-decay cutoff (g(t)=0) and never the "nearest" by driving time.
ROUTING_MAX_HAVERSINE_KM = 300
# Safety net: always keep at least this many candidate facilities per tract
# (even for very remote tracts where nothing is within the radius).
ROUTING_MIN_K = 30

# --- Census / Geocoding ---
CENSUS_GEOCODER_BATCH_URL = "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch"
