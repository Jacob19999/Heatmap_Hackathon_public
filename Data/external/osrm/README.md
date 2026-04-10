# OSRM Data and Server (T011)

Run a local OSRM routing server so the pipeline can compute driving distances/times across **all states** (national-scale routing) or for a single region (e.g. notebook sanity check).

## Prerequisites

- **Docker Desktop for Windows**
  Install from https://www.docker.com/products/docker-desktop/ and ensure it's running (Docker engine started).

- **WSL2 memory & swap** (critical for full US extract)
  `osrm-extract` on the full US is extremely memory-hungry (~10-12 GB with 2 threads, much more with all cores). Each thread builds its own in-memory copy of parsed ways/nodes, so more threads = linearly more RAM.

  Edit or create `%UserProfile%\.wslconfig`:
  ```ini
  [wsl2]
  memory=16GB
  processors=4
  swap=32GB
  ```
  Then restart WSL (`wsl --shutdown` in PowerShell) and reopen Docker Desktop.
  The large swap (32 GB) lets the OS spill to disk instead of OOM-killing the process. It only costs disk space.

  If extract still fails with 2 threads + 32 GB swap, use `-Threads 1` (slower but lowest memory).

## Full pipeline (all states) -- recommended for production

Use the **full US** extract so routing works for every state (tract centroids and facilities nationwide). Requires ~11 GB download and more disk space and processing time.

1. **Download the US OSM extract** (~11 GB) into this folder:
   - https://download.geofabrik.de/north-america/us-latest.osm.pbf
   - Save as: `Data/external/osrm/us-latest.osm.pbf`

2. **Run the Windows setup script** (from repo root):
   ```powershell
   cd c:\Users\tngzj\OneDrive\Desktop\Heatmap_Hackathon
   .\Data\external\osrm\setup_osrm.ps1 -Extract us-latest.osm.pbf
   ```
   The script defaults to **2 threads** to keep peak RAM around 10-12 GB.
   Extract + partition + customize can take **30-90+ minutes** for the full US. Then the script starts the routing server on port 5000.

   **If extract exits during "Parse ways and nodes"** (out-of-memory):
   - Increase swap to 32 GB in `.wslconfig` (see Prerequisites above)
   - Use 1 thread for minimum memory:
   ```powershell
   .\Data\external\osrm\setup_osrm.ps1 -Extract us-latest.osm.pbf -Threads 1
   ```

3. **Verify**: From repo root run `python -m src.pipeline.verify_osrm` or open http://127.0.0.1:5000/health

4. **Run the full pipeline** (ingest -> geocode -> augment -> routing -> access, etc.) with OSRM serving all states.

To run the server in the background instead:
```powershell
.\Data\external\osrm\setup_osrm.ps1 -Extract us-latest.osm.pbf -Detach
```
Stop later: `docker stop osrm`

---

## Lower-memory full-US option (recommended on 32 GB machines)

If latest full-US extract OOMs during `osrm-extract`, use an older full-US snapshot.
This keeps full national coverage with much lower memory pressure.

```powershell
cd c:\Users\tngzj\OneDrive\Desktop\Heatmap_Hackathon
.\Data\external\osrm\setup_osrm.ps1 -Preset us-210101 -DownloadIfMissing -Threads 1
```

Notes:
- `us-210101.osm.pbf` is ~7.5 GB (vs ~11.7 GB latest), so extract memory is much lower.
- `-DownloadIfMissing` downloads directly from Geofabrik into `Data/external/osrm`.
- You can try `-Threads 2` first; use `-Threads 1` if still memory constrained.

---

## Quick / regional only (e.g. Minnesota sanity check)

If you only need to test the notebook (e.g. Mankato -> Minneapolis) or a single region, use the **US Midwest** extract (~2.2 GB) for a smaller download and faster processing. **Not suitable for the full national pipeline** -- use full US above for all states.

1. **Download US Midwest OSM extract** (~2.2 GB):
   - https://download.geofabrik.de/north-america/us-midwest-latest.osm.pbf
   - Save as: `Data/external/osrm/us-midwest-latest.osm.pbf`

2. **Run the setup script**:
   ```powershell
   .\Data\external\osrm\setup_osrm.ps1 -Extract us-midwest-latest.osm.pbf
   ```

3. **Verify** as above. Notebook "Driving (OSRM)" check will work for Minnesota; routing outside the Midwest will fail.

---

## Manual Docker commands (Windows PowerShell)

Run from repo root. For **full pipeline (all states)** use `us-latest.osm.pbf`; for regional testing use `us-midwest-latest.osm.pbf`. `OSRM_DIR` must be the **absolute** path to `Data/external/osrm`.

**Full US (all states):**
```powershell
$OSRM_DIR = "c:\Users\tngzj\OneDrive\Desktop\Heatmap_Hackathon\Data\external\osrm"
$EXTRACT = "us-latest.osm.pbf"
$BASENAME = "us-latest"
```

**Regional (e.g. US Midwest):**
```powershell
$OSRM_DIR = "c:\Users\tngzj\OneDrive\Desktop\Heatmap_Hackathon\Data\external\osrm"
$EXTRACT = "us-midwest-latest.osm.pbf"
$BASENAME = "us-midwest-latest"
```

Then run:

```powershell
# 1. Extract (car profile) -- full US can take 30-90+ minutes
docker run -t -v "${OSRM_DIR}:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua --threads 2 "/data/$EXTRACT"

# 2. Partition
docker run -t -v "${OSRM_DIR}:/data" ghcr.io/project-osrm/osrm-backend osrm-partition "/data/$BASENAME.osrm"

# 3. Customize
docker run -t -v "${OSRM_DIR}:/data" ghcr.io/project-osrm/osrm-backend osrm-customize "/data/$BASENAME.osrm"

# 4. Start routing server (foreground; Ctrl+C to stop)
docker run -t -i -p 5000:5000 -v "${OSRM_DIR}:/data" ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld "/data/$BASENAME.osrm"
```

To run the server in the background (detached):

```powershell
docker run -t -d -p 5000:5000 -v "${OSRM_DIR}:/data" --name osrm ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld "/data/$BASENAME.osrm"
```

Stop later: `docker stop osrm`

## Alternative engines / deployment options

### Option B: Valhalla fallback

If OSRM extract is still too heavy, you can switch to Valhalla matrix API.

1. Build and run Valhalla:
```powershell
.\Data\external\osrm\setup_valhalla.ps1 -Extract us-210101.osm.pbf
```

2. In `src/pipeline/config.py`:
```python
ROUTING_ENGINE = "valhalla"
VALHALLA_BASE_URL = "http://127.0.0.1:8002"
```

3. Run pipeline routing step as usual (`compute_travel_time_matrix` now supports OSRM or Valhalla).

### Option C: Cloud VM for one-time OSRM preprocess

If you need latest full-US data and local extract keeps OOMing:
- Run `osrm-extract`, `osrm-partition`, `osrm-customize` on a high-memory cloud VM (e.g. 64 GB RAM).
- Copy generated `.osrm*` files back into `Data/external/osrm`.
- Start `osrm-routed` locally (low memory) from those files.

Detailed runbook: `Data/external/osrm/CLOUD_EXTRACT_RUNBOOK.md`

## Verify

- Run: `python -m src.pipeline.verify_osrm`
- Or open in browser: http://127.0.0.1:5000/health

Once OSRM is running on port 5000 with the **full US** extract, the notebook's "Driving (OSRM)" sanity check and the **full pipeline** (routing across all states) will work.
