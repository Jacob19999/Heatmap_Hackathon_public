param(
    [string] $ContainerName = "valhalla-hires",
    [int] $Port = 8003,
    [string] $ConfigFile = "valhalla.json",
    [double] $Cpus = 16,
    [string] $Memory = "24g",
    [string] $ShmSize = "2g",
    [int] $Threads = 12,
    [string] $DataDir = ""
)

$ErrorActionPreference = "Stop"
# Use -DataDir if provided (e.g. D:\ValhallaData to run Valhalla off C:); otherwise script directory
$DATA_DIR = if ($DataDir -and (Test-Path $DataDir)) { (Resolve-Path $DataDir).Path } else { $PSScriptRoot }
$IMAGE = "ghcr.io/valhalla/valhalla:latest"
$DATA_DIR_DOCKER = $DATA_DIR -replace '\\', '/'
$CONFIG_PATH = Join-Path $DATA_DIR $ConfigFile
$CONFIG_PATH_DOCKER = "/custom_files/$ConfigFile"

if (-not (Test-Path $CONFIG_PATH)) {
    Write-Host "ERROR: Config file not found: $CONFIG_PATH" -ForegroundColor Red
    Write-Host "Build Valhalla first so $ConfigFile exists in $DATA_DIR." -ForegroundColor Yellow
    exit 1
}

docker version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running or not installed. Start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

$existingContainerId = docker ps -aq -f "name=^${ContainerName}$"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to query Docker for existing containers."
}

if ($existingContainerId) {
    $isRunning = docker ps -q -f "name=^${ContainerName}$"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to inspect existing container '$ContainerName'."
    }

    if ($isRunning) {
        Write-Host "Container '$ContainerName' is already running." -ForegroundColor Green
        Write-Host "Health check URL: http://127.0.0.1:$Port/status" -ForegroundColor Green
        Write-Host "No changes were made. Existing CPU/memory limits remain in effect." -ForegroundColor Yellow
        Write-Host "To apply new CPU/thread defaults, recreate the container or run with a new container name." -ForegroundColor Yellow
        exit 0
    }

    Write-Host "Starting existing container '$ContainerName' ..." -ForegroundColor Yellow
    docker start $ContainerName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start existing container '$ContainerName'."
    }

    Write-Host "Valhalla is running in the background." -ForegroundColor Green
    Write-Host "Health check URL: http://127.0.0.1:$Port/status" -ForegroundColor Green
    Write-Host "Note: existing CPU/memory limits were preserved." -ForegroundColor Yellow
    Write-Host "To apply new CPU/thread defaults, recreate the container or run with a new container name." -ForegroundColor Yellow
    exit 0
}

Write-Host "Starting Valhalla on http://127.0.0.1:$Port ..." -ForegroundColor Yellow
Write-Host "Container: $ContainerName | CPUs: $Cpus | Memory: $Memory | Threads: $Threads" -ForegroundColor Gray

docker run -d `
    --name $ContainerName `
    --restart unless-stopped `
    --cpus "$Cpus" `
    --memory $Memory `
    --memory-swap $Memory `
    --shm-size $ShmSize `
    -p "${Port}:8002" `
    -v "${DATA_DIR_DOCKER}:/custom_files" `
    $IMAGE `
    valhalla_service $CONFIG_PATH_DOCKER $Threads

if ($LASTEXITCODE -ne 0) {
    throw "Failed to start Valhalla container."
}

Write-Host "Valhalla is running in the background." -ForegroundColor Green
Write-Host "Health check URL: http://127.0.0.1:$Port/status" -ForegroundColor Green
Write-Host "Stop with: docker stop $ContainerName" -ForegroundColor Gray
