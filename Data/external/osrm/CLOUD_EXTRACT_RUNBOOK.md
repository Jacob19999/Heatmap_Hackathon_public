# Cloud Runbook: One-Time OSRM Preprocess

Use this when local `osrm-extract` runs out of memory. The preprocess is done once
on a high-memory VM, then copied back to your local machine for normal serving.

## 1) Provision VM

- Linux VM with **64 GB RAM** (or more), 8 vCPU, 80+ GB disk.
- Install Docker.
- Upload `us-latest.osm.pbf` (or another extract) to VM.

## 2) Run OSRM preprocess on VM

```bash
mkdir -p ~/osrm
mv us-latest.osm.pbf ~/osrm/
cd ~/osrm

docker run -t -v "$PWD:/data" ghcr.io/project-osrm/osrm-backend \
  osrm-extract -p /opt/car.lua /data/us-latest.osm.pbf

docker run -t -v "$PWD:/data" ghcr.io/project-osrm/osrm-backend \
  osrm-partition /data/us-latest.osrm

docker run -t -v "$PWD:/data" ghcr.io/project-osrm/osrm-backend \
  osrm-customize /data/us-latest.osrm
```

Expected outputs include `us-latest.osrm` and related sidecar files (`.osrm.*`).

## 3) Copy artifacts back to local machine

From local PowerShell (replace host/user/key as needed):

```powershell
scp -i "C:\path\to\key.pem" user@your-vm-host:~/osrm/us-latest.osrm* `
  "c:\Users\tngzj\OneDrive\Desktop\Heatmap_Hackathon\Data\external\osrm\"
```

## 4) Run local OSRM server only

```powershell
cd c:\Users\tngzj\OneDrive\Desktop\Heatmap_Hackathon
docker run -t -i -p 5000:5000 `
  -v "c:/Users/tngzj/OneDrive/Desktop/Heatmap_Hackathon/Data/external/osrm:/data" `
  ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld "/data/us-latest.osrm"
```

Or detached:

```powershell
docker run -t -d -p 5000:5000 `
  -v "c:/Users/tngzj/OneDrive/Desktop/Heatmap_Hackathon/Data/external/osrm:/data" `
  --name osrm ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld "/data/us-latest.osrm"
```

## 5) Verify

- `python -m src.pipeline.verify_osrm`
- Open <http://127.0.0.1:5000/health>
