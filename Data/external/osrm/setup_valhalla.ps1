# Valhalla setup for Windows via Docker.
# Builds tiles from an OSM PBF and starts a local routing service.
#
# Usage:
#   .\setup_valhalla.ps1 -Extract us-210101.osm.pbf
#   .\setup_valhalla.ps1 -Extract us-latest.osm.pbf -Detach

param(
    [Parameter(Mandatory = $true)]
    [string] $Extract,

    [switch] $Detach
)

$ErrorActionPreference = "Stop"
$DATA_DIR = $PSScriptRoot
$IMAGE = "ghcr.io/valhalla/valhalla:latest"
$DATA_DIR_DOCKER = $DATA_DIR -replace '\\', '/'

if (-not (Test-Path "$DATA_DIR\$Extract")) {
    Write-Host "ERROR: OSM extract not found: $DATA_DIR\$Extract" -ForegroundColor Red
    Write-Host "Download from Geofabrik and save into: $DATA_DIR" -ForegroundColor Yellow
    exit 1
}

docker version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running or not installed. Start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

Write-Host "Building Valhalla tiles from $Extract (this can take a while)..." -ForegroundColor Yellow
$ConfigPath = "/custom_files/valhalla.json"
docker run --rm -t -v "${DATA_DIR_DOCKER}:/custom_files" $IMAGE /bin/bash -lc "valhalla_build_config --mjolnir-tile-dir /custom_files/valhalla_tiles --mjolnir-tile-extract /custom_files/valhalla_tiles.tar -o $ConfigPath"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker run --rm -t -v "${DATA_DIR_DOCKER}:/custom_files" $IMAGE /bin/bash -lc "valhalla_build_tiles -c $ConfigPath /custom_files/$Extract"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Starting Valhalla service on http://127.0.0.1:8002 ..." -ForegroundColor Yellow
if ($Detach) {
    docker run -d -p 8002:8002 -v "${DATA_DIR_DOCKER}:/custom_files" --name valhalla $IMAGE valhalla_service $ConfigPath 1
    Write-Host "Valhalla is running in the background. Stop with: docker stop valhalla" -ForegroundColor Green
} else {
    Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Gray
    docker run -it -p 8002:8002 -v "${DATA_DIR_DOCKER}:/custom_files" $IMAGE valhalla_service $ConfigPath 1
}
