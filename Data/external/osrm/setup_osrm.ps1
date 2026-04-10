# OSRM setup for Windows: extract, partition, customize, and run routing server.
# Prerequisites: Docker Desktop installed and running.
# Usage:
#   .\setup_osrm.ps1 -Extract us-latest.osm.pbf                  # full pipeline, all states (~11+ GB)
#   .\setup_osrm.ps1 -Extract us-midwest-latest.osm.pbf          # regional only, e.g. Minnesota (~2.2 GB)
#   .\setup_osrm.ps1 -Preset us-210101 -DownloadIfMissing        # lower-memory full-US snapshot
#   .\setup_osrm.ps1 -Extract us-latest.osm.pbf -Detach          # run server in background

param(
    [string] $Extract,

    # Optional quick selector for common extracts:
    #   us-latest, us-midwest-latest, us-210101, us-220101, us-230101
    [string] $Preset = "",

    [switch] $Detach,

    [switch] $DownloadIfMissing,

    # Limit threads for osrm-extract to reduce memory use.
    # Full US extract with all cores easily exceeds 16 GB RAM.
    # Default 2 keeps peak memory around 10-12 GB; use 1 if still OOM.
    [int] $Threads = 2
)

$ErrorActionPreference = "Stop"
$OSRM_DIR = $PSScriptRoot
$IMAGE = "ghcr.io/project-osrm/osrm-backend"
$GEOFABRIK_US_BASE = "https://download.geofabrik.de/north-america"

# Docker on Windows often needs a path with forward slashes for the bind mount
$OSRM_DIR_DOCKER = $OSRM_DIR -replace '\\', '/'

if (-not $Extract -and [string]::IsNullOrWhiteSpace($Preset)) {
    Write-Host "ERROR: Provide either -Extract or -Preset." -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Extract) -and -not [string]::IsNullOrWhiteSpace($Preset)) {
    $map = @{
        "us-latest" = "us-latest.osm.pbf"
        "us-midwest-latest" = "us-midwest-latest.osm.pbf"
        "us-210101" = "us-210101.osm.pbf"
        "us-220101" = "us-220101.osm.pbf"
        "us-230101" = "us-230101.osm.pbf"
    }
    if (-not $map.ContainsKey($Preset)) {
        Write-Host "ERROR: Unknown -Preset '$Preset'." -ForegroundColor Red
        Write-Host "Valid presets: $($map.Keys -join ', ')" -ForegroundColor Yellow
        exit 1
    }
    $Extract = $map[$Preset]
}

if (-not (Test-Path "$OSRM_DIR\$Extract")) {
    if ($DownloadIfMissing) {
        $url = "$GEOFABRIK_US_BASE/$Extract"
        Write-Host "Extract not found locally. Downloading: $url" -ForegroundColor Yellow
        Invoke-WebRequest -Uri $url -OutFile "$OSRM_DIR\$Extract"
    } else {
        Write-Host "ERROR: OSM extract not found: $OSRM_DIR\$Extract" -ForegroundColor Red
        Write-Host "Download one of:" -ForegroundColor Yellow
        Write-Host "  Full US, all states (~11+ GB):   $GEOFABRIK_US_BASE/us-latest.osm.pbf" -ForegroundColor Gray
        Write-Host "  Lower-memory US (~7.5 GB):       $GEOFABRIK_US_BASE/us-210101.osm.pbf" -ForegroundColor Gray
        Write-Host "  US Midwest only (~2.2 GB):       $GEOFABRIK_US_BASE/us-midwest-latest.osm.pbf" -ForegroundColor Gray
        Write-Host "Or use -DownloadIfMissing with -Preset/-Extract." -ForegroundColor Gray
        Write-Host "Save the file into: $OSRM_DIR" -ForegroundColor Gray
        exit 1
    }
}

docker version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running or not installed. Start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

$BaseName = [System.IO.Path]::GetFileNameWithoutExtension($Extract)
Write-Host "Using extract: $Extract -> base name: $BaseName" -ForegroundColor Cyan

# 1. Extract
$ExtractArgs = @("-p", "/opt/car.lua")
if ($Threads -gt 0) {
    $ExtractArgs += @("--threads", $Threads)
    Write-Host "`n[1/4] osrm-extract (car profile, $Threads threads) — this may take 10–30+ minutes..." -ForegroundColor Yellow
} else {
    Write-Host "`n[1/4] osrm-extract (car profile) — this may take 10–30+ minutes..." -ForegroundColor Yellow
}
docker run -t -v "${OSRM_DIR_DOCKER}:/data" $IMAGE osrm-extract @ExtractArgs "/data/$Extract"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 2. Partition
Write-Host "`n[2/4] osrm-partition..." -ForegroundColor Yellow
docker run -t -v "${OSRM_DIR_DOCKER}:/data" $IMAGE osrm-partition "/data/$BaseName.osrm"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 3. Customize
Write-Host "`n[3/4] osrm-customize..." -ForegroundColor Yellow
docker run -t -v "${OSRM_DIR_DOCKER}:/data" $IMAGE osrm-customize "/data/$BaseName.osrm"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 4. Start routing server
Write-Host "`n[4/4] Starting osrm-routed on http://127.0.0.1:5000 ..." -ForegroundColor Yellow
if ($Detach) {
    docker run -t -d -p 5000:5000 -v "${OSRM_DIR_DOCKER}:/data" --name osrm $IMAGE osrm-routed --algorithm mld "/data/$BaseName.osrm"
    Write-Host "OSRM is running in the background. Stop with: docker stop osrm" -ForegroundColor Green
} else {
    Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Gray
    docker run -t -i -p 5000:5000 -v "${OSRM_DIR_DOCKER}:/data" $IMAGE osrm-routed --algorithm mld "/data/$BaseName.osrm"
}
