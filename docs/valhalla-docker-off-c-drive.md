# Moving Valhalla and Docker Off the C: Drive

If C: is at 100% during the county Valhalla pipeline, move Docker and/or Valhalla data to another drive (e.g. D: or E:) to reduce disk contention.

---

## 1. Move Docker’s data (images, containers, volumes)

Docker Desktop stores everything under `C:\Users\<You>\AppData\Local\Docker` by default. Moving it to another drive reduces C: I/O.

### Steps

1. **Quit Docker Desktop** (right‑click tray icon → Quit).
2. **Create the target folder on the other drive**, e.g. `D:\wsl` (so the WSL data will live in `D:\wsl\DockerDesktopWSL`).
3. **Move the existing Docker WSL data** (optional but recommended so you don’t re-download images):
   - Copy the entire folder:
     - From: `%LOCALAPPDATA%\Docker\wsl` (contains `DockerDesktopWSL` and related data)
     - To: `D:\wsl`
   - So you end up with `D:\wsl\DockerDesktopWSL` (and inside it the `disk` image, i.e. `D:\wsl\DockerDesktopWSL\disk`).
   - Or use **Docker Desktop → Settings → Resources → Advanced → Disk image location** and set it to the folder that contains `disk`; Docker may offer to migrate. If it doesn’t migrate automatically, copy the `wsl` folder as above.
4. **Point Docker to the new location**
   - Open **Docker Desktop → Settings (gear) → Resources → Advanced**.
   - Set **Disk image location** to the folder that contains the virtual disk, e.g. `D:\wsl\DockerDesktopWSL` (so the `disk` file lives at `D:\wsl\DockerDesktopWSL\disk`).
   - Apply & Restart. Docker will use the new path from now on.
5. **Start Docker Desktop** again and confirm containers/images are visible. If you didn’t copy the data, you’ll need to re-pull images and recreate containers.

---

## 2. Move Valhalla data (tiles + config) off C:

Valhalla reads tiles and config from the folder you mount into the container (by default `Data\external\osrm`). If that folder is on C:, moving it to D: or E: moves Valhalla’s disk I/O off C:.

### Steps

1. **Stop and remove the existing Valhalla container** (so you can recreate it with the new path):
   ```powershell
   docker stop valhalla-hires
   docker rm valhalla-hires
   ```

2. **Copy the Valhalla data folder** to the other drive:
   - Source: `Heatmap_Hackathon\Data\external\osrm`  
     (contains `valhalla.json`, `valhalla_tiles/` or `valhalla_tiles.tar`, and the scripts)
   - Destination: e.g. `D:\ValhallaData`
   - Copy everything (tiles, config, scripts) so that `D:\ValhallaData\valhalla.json` and the tile files exist.

3. **Start Valhalla from the new location** using the `-DataDir` parameter:
   ```powershell
   cd D:\ValhallaData
   .\run_valhalla_service.ps1 -DataDir "D:\ValhallaData"
   ```
   Or from the repo (script path doesn’t have to match DataDir):
   ```powershell
   cd Heatmap_Hackathon\Data\external\osrm
   .\run_valhalla_service.ps1 -DataDir "D:\ValhallaData"
   ```

4. **Confirm** the service is up: open `http://127.0.0.1:8003/status` in a browser (or use port 8002 if you didn’t pass `-Port 8003`).

### Optional: keep only one copy

If you want to free space on C: and use only the copy on D::

- After confirming Valhalla works from `D:\ValhallaData`, you can delete the original `Data\external\osrm` tile data (e.g. `valhalla_tiles` or `valhalla_tiles.tar`) on C: to save space. Keep the scripts in the repo if you like; just run them with `-DataDir "D:\ValhallaData"` when starting the container.

---

## Summary

| Goal                         | Action |
|-----------------------------|--------|
| Less C: use by Docker        | Move Docker Desktop “Disk image location” to e.g. `D:\DockerData`. |
| Less C: use by Valhalla I/O  | Copy `Data\external\osrm` to e.g. `D:\ValhallaData`, then run `run_valhalla_service.ps1 -DataDir "D:\ValhallaData"` (after removing the old container). |

Doing both moves Docker and Valhalla’s heavy I/O off C:, which should reduce disk saturation during the county matrix runs.
