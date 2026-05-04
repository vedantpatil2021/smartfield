# Smartfield — Autonomous Drone Documentation System for Animal Ecology

A field-deployable edge computing platform that closes the gap between ground-level animal detection and aerial behavioural observation. When a camera-trap detects an animal, Smartfield autonomously dispatches a Parrot ANAFI drone to the site, runs real-time YOLO-based tracking, and stores a synchronized multimodal dataset — without a human in the loop.

[![Software](https://img.shields.io/badge/category-Software-blue.svg)](https://github.com/)
[![Animal Ecology](https://img.shields.io/badge/category-Animal%20Ecology-green.svg)](https://github.com/)
[![Docker](https://img.shields.io/badge/runtime-Docker-2496ED.svg)](https://www.docker.com/)

### License
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## References

### Key Resources
- **SoftwarePilot SDK**: [Parrot ANAFI Drone Control Framework](https://github.com/KevynAngueira/SoftwarePilot)
- **Parrot Olympe SDK**: [Low-level Drone Automation Library](https://developer.parrot.com/docs/olympe/)
- **MQTT Protocol**: [IoT Messaging Standard](https://mqtt.org/)
- **Ultralytics YOLOv5**: [Real-Time Object Detection](https://github.com/ultralytics/ultralytics)
- **NVIDIA Container Toolkit**: [GPU Access in Docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/overview.html)

### Key Terms
- **Camera-trap**: A motion-triggered edge sensor running YOLOv5 inference locally to detect animals and publish MQTT events
- **Detection-to-Documentation Pipeline**: The automated chain from ground-level detection through MQTT, to drone dispatch, aerial tracking, and dataset storage
- **OpenPassLite**: The mission execution layer inside Smartfield — a library of drone flight scripts (LTT, RTB, TAKEOFF, LAND) driven by GPS coordinates
- **WildWings**: The computer vision and drone-tracking layer — streams live video, runs YOLO frame-by-frame, and issues `move_by` corrections to follow animals
- **mode_type**: A runtime flag — `"test"` runs the full YOLO pipeline without moving the drone; `"live"` enables autonomous flight
- **Edge Computing**: All inference and coordination happens on a single local laptop; no cloud dependency

## Acknowledgements

*National Science Foundation (NSF) funded AI institute for Intelligent Cyberinfrastructure with Computational Learning in the Environment (ICICLE) (OAC 2112606)*

---

# Tutorials

## Getting Started with Smartfield Deployment

### Overview

This tutorial walks through deploying Smartfield from a clean machine to a running autonomous pipeline. Two services are started together via Docker Compose: `smartfield` (the drone orchestration service on port `9988`) and `mqtt_subscriber` (the camera-trap event listener on port `9987`). The Makefile handles GPU auto-detection, image building, and field export automatically.

### Prerequisites

#### Hardware Requirements
- **Edge Laptop or Workstation**: x86_64, 8GB RAM recommended
- **Parrot ANAFI Drone**: Connected via SkyController (192.168.53.1) or direct WiFi (192.168.42.1)
- **WiFi Interface**: Dedicated interface or shared — drone must be reachable on host network
- **NVIDIA GPU** (optional): Any CUDA 12.1-compatible card for accelerated YOLO inference

#### Software Requirements
- Docker Engine 24.0+
- Docker Compose v2.20+
- `make`
- `curl` (for health checks)
- Linux-based OS (tested on Ubuntu 22.04)
- NVIDIA Container Toolkit (GPU builds only) — installed via `make prereqs`

---

### Step 1: Clone and Configure

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd smartfield
   ```

2. Open `config.toml` and set the camera-trap GPS coordinates and operating mode:
   ```toml
   [mission]
   lat       = 40.008278   # Replace with your camera-trap's exact latitude
   long      = -83.017514  # Replace with your camera-trap's exact longitude
   mode_type = "live"      # "test" = YOLO runs but drone won't move | "live" = full autonomous flight
   ```

   > **IMPORTANT**: The `lat` and `long` values are the coordinates the drone will fly to. Incorrect values will cause the drone to navigate to the wrong location. Verify them before field deployment.

---

### Step 2: Install Prerequisites (GPU machines only)

If your machine has an NVIDIA GPU, install the NVIDIA Container Toolkit before building:
```bash
make prereqs
```

This runs `prerequisites.sh`, which:
- Adds the NVIDIA Container Toolkit apt repository
- Installs `nvidia-container-toolkit` at a pinned version (`1.19.0-1`)
- Configures Docker to use the NVIDIA runtime
- Restarts the Docker daemon

On CPU-only machines, `make prereqs` detects the absence of `nvidia-smi` and exits without making any changes.

> **Note**: `make prereqs` only needs to be run once per machine. Skip it on subsequent deployments.

---

### Step 3: Build and Start

Build the images and start both services (CPU by default):
```bash
make up
```

This single command:
- Builds using `Dockerfile.cpu` (no GPU required)
- Bakes YOLO weights into the image — no internet needed at runtime
- Starts both `smartfield` and `mqtt_subscriber`

To use the GPU image (requires NVIDIA Container Toolkit — see `make prereqs`):
```bash
make up-gpu
```

To run in the background (detached mode):
```bash
make up-detach       # CPU
make up-gpu-detach   # GPU
```

---

### Step 4: Verify Deployment

Check that both services are healthy:
```bash
make health
```

Expected output:
```
── smartfield ──
{
    "success": true,
    "data": {
        "status": "ok"
    }
}
── mqtt_subscriber ──
{
    "success": true,
    "data": {
        "status": "ok"
    }
}
```

Check running containers:
```bash
make status
```

---

### Step 5: Run a Test Mission

Before flying live, validate the pipeline in test mode (YOLO runs, drone stays grounded):

1. Switch to test mode:
   ```bash
   make mode-test
   ```

2. Trigger a manual test mission:
   ```bash
   make mission-test
   ```

3. Watch the logs:
   ```bash
   make logs-sf
   ```

   You should see the drone connect, the YOLO tracker start, telemetry logged to CSV, and the drone disconnect cleanly — without any physical movement.

---

### End Result

Upon successful deployment you will have:
- Autonomous camera-trap event listener running on MQTT
- YOLO-powered animal tracking active on every mission
- Drone-ready pipeline waiting for detection events
- Mission logs and telemetry CSVs written to `logs/mission/`
- A system that operates without internet or cloud infrastructure

To also launch the field operations dashboard:
```bash
make ui
```

The dashboard opens a native desktop window with live RTSP video, service health indicators, mission trigger controls, and a real-time log terminal.

---

# How-To Guides

## How to Switch Between Live and Test Mode

### Problem Description
Switching the system between safe ground-testing (YOLO runs, drone stays grounded) and full autonomous flight for field operations.

### Steps

**Switch to test mode** (drone will not move):
```bash
make mode-test
```

**Switch to live mode** (full autonomous flight):
```bash
make mode-live
```

**Check current mode**:
```bash
make mode-show
```

### How It Works
`mode_type` is read from `config.toml` at the start of every mission. In `test` mode the drone connects, takes off, runs the YOLO tracker for the full session duration, and lands — but the `move_by` calls that physically steer the drone are suppressed. All telemetry, frame captures, and detection CSVs are still written identically to live mode.

You can also override mode per-request via the API without touching `config.toml`:
```bash
curl -s -X POST http://localhost:9988/api/v1/mission/run \
  -H "Content-Type: application/json" \
  -d '{"mode_type": "test"}'
```

---

## How to Manually Trigger a Drone Mission

### Problem Description
Testing the full pipeline without waiting for a camera-trap MQTT event.

### Steps

1. Ensure both services are running:
   ```bash
   make status
   ```

2. Trigger a live mission (uses coordinates from `config.toml`):
   ```bash
   make mission-live
   ```

   Or trigger with explicit coordinates via the API:
   ```bash
   curl -s -X POST http://localhost:9988/api/v1/mission/run \
     -H "Content-Type: application/json" \
     -d '{"lat": 40.008278, "long": -83.017514, "mode_type": "live"}'
   ```

3. To abort a running mission:
   ```bash
   make mission-stop
   ```
   This restarts the `smartfield` container, which terminates the active mission immediately.

4. Monitor mission progress:
   ```bash
   make logs-sf
   ```

4. Inspect the output after the mission completes:
   ```bash
   ls logs/mission/
   # mission_20250501_143022/
   #   mission.log         — full structured log
   #   telemetry_log.csv   — per-frame GPS + move_by vectors
   #   <video files>       — downloaded from drone on mission end
   ```

### Troubleshooting
- **Drone not connecting**: Confirm the ANAFI is powered on and the SkyController shows a solid WiFi link. The drone is expected at `192.168.53.1`.
- **GPS not available**: The drone requires GPS lock before LTT navigation. Check `mission.log` for `GPS coordinates not available`.
- **Mission immediately fails**: Check `mission.log` — most failures are GPS or battery level issues.

---

## How to View Real-Time Logs

### Problem Description
Monitoring the pipeline in real time and debugging issues during field operations.

### Steps

**All services together**:
```bash
make logs
```

**Smartfield only** (drone orchestration, mission lifecycle, YOLO output):
```bash
make logs-sf
```

**MQTT Subscriber only** (broker connection, incoming camera-trap events):
```bash
make logs-mq
```

### Log Locations

Mission-specific logs are written to disk for each run:
```
logs/mission/
└── mission_20250501_143022/
    ├── mission.log          # Full structured log with timestamps
    └── telemetry_log.csv    # Frame counter, GPS position, move_by vectors
```

Clean all mission logs when storage is low:
```bash
make clean-logs
```

---

## How to Launch the Field Operations Dashboard

### Problem Description
Monitoring live RTSP video from the drone, checking service health, triggering missions, and reading log output from a single desktop interface — without switching between terminal windows.

### Prerequisites
- Conda (Anaconda or Miniconda) installed on the host machine
- An active X11 session (standard on Ubuntu desktop)
- Both `smartfield` and `mqtt_subscriber` services running (`make up-detach`)
- Drone connected via SkyController (reachable at `192.168.53.1`)

### Steps

1. Grant X11 display access to local processes:
   ```bash
   xhost +local:
   ```

2. Launch the dashboard:
   ```bash
   make ui
   ```

   On first run, `make ui` calls `services/ui/run.sh`, which:
   - Creates a `smartfield` conda environment with Python 3.10 (if it doesn't already exist)
   - Installs system dependencies (`libegl1`, Qt XCB runtime libraries, `fonts-noto-color-emoji`)
   - Installs Python dependencies (`PyQt6`, `opencv-python-headless`, `requests`, `psutil`, `toml`)
   - Launches `dashboard.py` from the smartfield root directory

   Subsequent runs skip environment creation and start immediately.

3. The dashboard window opens with:
   - **Live Video**: RTSP stream from the drone captured via OpenCV + FFmpeg (UDP transport) and rendered into the left panel. Enter the stream URL and click **Connect**.
   - **Service Health**: Pulsing green/red indicators for `smartfield` and `mqtt_subscriber`
   - **Detection-to-Documentation Pipeline**: Visual stage tracker (Camera Trap → MQTT → Navigate → Track → RTB)
   - **Mission Config**: Editable lat/lon and mode_type fields with Save Config and Trigger Mission buttons
   - **Log Terminal**: Real-time log tail from `smartfield` with ALL / INFO / WARNING / ERROR filter tabs
   - **Metrics**: CPU, RAM, and GPU usage bars updated every second

### Notes
- The dashboard connects to `smartfield` at `http://localhost:9988` and `mqtt_subscriber` at `http://localhost:9987`. Both services must be running for health polling to show green.
- The RTSP URL defaults to `rtsp://192.168.53.1/live` (Parrot ANAFI via SkyController). Override with the `RTSP_URL` environment variable if your setup differs.
- The video stack uses **OpenCV with FFmpeg over UDP**. TCP transport is not supported by the drone's RTSP server — do not change the transport mode.
- Emoji rendering requires `fonts-noto-color-emoji` to be installed in the container (included in the Dockerfile).
- To run the dashboard as a Docker container instead of natively, use `docker compose up ui` — but ensure `xhost +local:docker` is run first and `DISPLAY` is set in your shell.

---

## How to Export Images for Offline Field Deployment

### Problem Description
Shipping pre-built Docker images to field sites without internet access using USB drives or hard copies.

### Steps

**On a machine with internet (e.g., your lab workstation)**:

Build and export the GPU image:
```bash
make export-gpu
# Produces: smartfield-gpu.tar.gz
```

Build and export the CPU image (for laptops without NVIDIA GPU):
```bash
make export-cpu
# Produces: smartfield-cpu.tar.gz
```

**At the field site (no internet required)**:

Copy the appropriate `.tar.gz` to the target machine, then load it manually:
```bash
docker load < smartfield-cpu.tar.gz   # CPU-only machine
docker load < smartfield-gpu.tar.gz   # GPU machine
```

Start the system normally after loading:
```bash
make up-detach       # CPU
make up-gpu-detach   # GPU
```

---

## How to Configure MQTT Camera-Trap Topics

### Problem Description
Mapping multiple camera-trap MQTT topics to their physical GPS coordinates so the drone flies to the right location when each trap fires.

### Steps

1. Open `config.toml` and add a `[mqtt_topics]` section:
   ```toml
   [mqtt_topics."cameratrap/events/pi-001"]
   lat   = 40.008278
   lon   = -83.017514
   camid = "pi-001"

   [mqtt_topics."cameratrap/events/pi-002"]
   lat   = 40.009100
   lon   = -83.018002
   camid = "pi-002"
   ```

2. Restart the subscriber to pick up the new topics:
   ```bash
   docker compose restart mqtt_subscriber
   ```

3. Verify subscriptions in the logs:
   ```bash
   make logs-mq
   # subscribed to topic: cameratrap/events/pi-001
   # subscribed to topic: cameratrap/events/pi-002
   ```

When a camera-trap publishes any JSON payload to one of these topics, the subscriber reads the `lat`/`lon` from `config.toml` (not from the payload) and fires the pipeline with those coordinates.

---

## How to Add a New Mission Type (OpenPassLite)

### Problem Description
Adding a custom flight script (e.g., a grid survey or orbit pattern) to the mission library without modifying the orchestration logic.

### Steps

1. Create a new mission directory under `services/smartfield/openpasslite/missions/`:
   ```bash
   mkdir services/smartfield/openpasslite/missions/GRID
   touch services/smartfield/openpasslite/missions/GRID/__init__.py
   touch services/smartfield/openpasslite/missions/GRID/script.py
   ```

2. Implement the `run(drone, **kwargs)` interface in `script.py`:
   ```python
   def run(drone, lat=None, long=None):
       drone.piloting.takeoff()
       # your grid logic here
       drone.piloting.land()
   ```

3. Import and call it in `services/smartfield/main.py`:
   ```python
   from openpasslite.missions.GRID import script as grid

   # inside main():
   grid.run(drone, lat=lat, long=long)
   ```

All missions receive the same `drone` object — the connection is established once in `main.py` and passed through to each script.

---

# Explanation

## System Architecture

### The Problem

Wildlife ecology research is constrained by the operational realities of field data collection. Ground-based sensing platforms — however sophisticated — capture a single observational plane. Aerial platforms, while capable of broader spatial coverage, are conventionally operated manually, introducing both logistical overhead and observer-dependent variance into datasets. The methodological gap between detection and documentation is not merely an inconvenience; it represents a systematic limitation on the temporal resolution, spatial continuity, and behavioural richness of ecological records.

Camera-traps, the canonical instrument of passive wildlife monitoring, face further constraints: images are stored locally, processed post-hoc, and stripped of the behavioural context that unfolds in the seconds and minutes following the initial detection event. The animal is captured at the moment of crossing the sensor plane — but the ecologically meaningful behaviour that follows is invisible to the record.

Smartfield is built around a single architectural proposition: detection and documentation should be causally linked in real time, not correlated in post-processing.

### The Actors

| Component | Role | Technology |
|---|---|---|
| **Camera-Trap** | Motion-triggered ground sensor; classifies detections at the edge | YOLOv5 on Raspberry Pi |
| **MQTT Broker** | Event bus; carries detection events to the subscriber | Mosquitto / any broker |
| **mqtt_subscriber** | Listens for camera-trap events; translates them into mission triggers | FastAPI + paho-mqtt |
| **smartfield** | Mission orchestrator; connects the drone, sequences missions, coordinates YOLO tracking | FastAPI + SoftwarePilot |
| **OpenPassLite** | GPS-based flight mission library (LTT, RTB, TAKEOFF, LAND) | SoftwarePilot / Olympe |
| **WildWings** | Computer vision tracking layer; runs YOLO on the live video stream | Ultralytics + OpenCV |
| **Field Dashboard** | Native desktop GUI for live video monitoring, mission control, and log inspection | PyQt6 + OpenCV (FFmpeg/UDP) |
| **Parrot ANAFI** | Autonomous aerial observation platform | Hardware |

### The Detection-to-Documentation Pipeline

```
Camera-Trap detects animal (confidence > threshold)
                  │
                  ▼
MQTT publish → cameratrap/events/<camid>
                  │
                  ▼
mqtt_subscriber receives event
  → reads lat/lon from config.toml for this topic
  → POST /initiate_pipeline?lat=..&lon=..&camid=..
                  │
                  ▼
smartfield receives trigger
  → creates mission_<timestamp>/ output directory
  → calls main()
                  │
                  ├─── mode_type = "test" ──────────────────────────┐
                  │                                                  │
                  ▼                                                  ▼
         drone.connect()                                    drone.connect()
         TAKEOFF.run()                                      LTT.run(lat, lon)
         WildWings.run() ← YOLO active, move_by suppressed  WildWings.run() ← YOLO + move_by
         LAND.run()                                          RTB.run()
         drone.disconnect()                                 drone.disconnect()
                  │                                                  │
                  └──────────────────────────────────────────────────┘
                                         │
                                         ▼
                              logs/mission/<id>/
                              ├── mission.log
                              └── telemetry_log.csv
```

**Result**: A synchronized multimodal record — ground-level detection metadata paired with aerial video and GPS-tagged telemetry — produced autonomously without human intervention.

---

### Service Architecture

Smartfield deliberately avoids microservice complexity for an edge deployment scenario. Both services run in Docker containers on the same host machine with `network_mode: host`, sharing the host's network stack directly. This gives both containers:

- Direct access to the drone's WiFi network (`192.168.53.1` via SkyController)
- Access to the MQTT broker running on the same host
- Zero network-address-translation overhead on drone control traffic

```
┌─────────────────────────────────────────────────────────────────┐
│                         Host Machine                            │
│                                                                 │
│  ┌─────────────────────┐      ┌──────────────────────────────┐  │
│  │   mqtt_subscriber   │      │         smartfield           │  │
│  │     port 9987       │─────▶│          port 9988           │  │
│  │                     │      │                              │  │
│  │  paho-mqtt client   │      │  OpenPassLite  │  WildWings  │  │
│  │  FastAPI /health    │      │  (missions)    │  (YOLO+cam) │  │
│  └─────────────────────┘      └──────────────────────────────┘  │
│           │                                  │                  │
│           ▼                                  ▼                  │
│      MQTT Broker                       Parrot ANAFI             │
│     (localhost:1883)               (192.168.53.1 via WiFi)      │
└─────────────────────────────────────────────────────────────────┘
```

---

### The Drone Connection Constraint

The central architectural constraint of this system is that an `olympe.Drone` object — the low-level session handle that SoftwarePilot wraps — **cannot cross a process boundary**. It lives in memory within the Python process that created it. This is why both OpenPassLite (flight missions) and WildWings (camera and tracking) run inside the same `smartfield` container process, sharing the same drone handle through `main.py`.

```python
# main.py — one connection, shared across the entire mission sequence
drone = sp.setup_drone("parrot_anafi", 1, "None")
drone.connect()

ltt.run(drone, lat=lat, long=long)         # OpenPassLite: fly to site
controller.run(drone, output_dir, mode)    # WildWings: YOLO + track
rtb.run(drone)                             # OpenPassLite: return home

drone.disconnect()
```

This design keeps the drone connection deterministic and avoids inter-process coordination entirely.

---

### GPU / CPU Build Strategy

The image build system is bifurcated to support both GPU-equipped workstations and CPU-only field laptops without requiring any manual configuration:

| Dockerfile | Base Image | PyTorch Source | Approx. Size |
|---|---|---|---|
| `Dockerfile.gpu` | `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04` | Default CUDA wheel | ~2 GB |
| `Dockerfile.cpu` | `ubuntu:22.04` | [PyTorch CPU wheel index](https://download.pytorch.org/whl/cpu) | ~800 MB |

The Makefile defaults to CPU. GPU is an explicit opt-in — no auto-detection:

```bash
make up          # always uses Dockerfile.cpu → smartfield:cpu
make up-gpu      # always uses Dockerfile.gpu → smartfield:gpu
```

Both Dockerfiles use `ubuntu:22.04` as their base lineage (the GPU build adds the CUDA runtime on top). This choice is intentional: Olympe ships pre-compiled C libraries built against Ubuntu 22.04 glibc. Using a Debian-based Python image (`python:3.10-slim`) causes binary incompatibility with Olympe's bundled dependencies.

---

### WildWings Tracking Loop

WildWings runs inside the same process as the drone connection. Once `LTT` delivers the drone to the detection site, `controller.run()` starts the YOLO tracking session:

1. `drone.camera.media.setup_recording()` — begins video capture to drone storage
2. `drone.camera.media.setup_stream(yuv_frame_processing=tracker.track)` — registers the frame callback
3. Every 40 frames, the callback:
   - Converts the YUV frame to BGR using OpenCV
   - Runs `navigation.get_next_action()` — YOLO inference → animal count → `(x, y, z)` movement vectors
   - Logs GPS position + movement vectors to `telemetry_log.csv`
   - In `live` mode: issues `drone.piloting.move_by(x, y, z, 0)` to track the animal
   - In `test` mode: logs everything but suppresses `move_by`
4. After `DURATION` seconds, the stream stops, the recording is downloaded, and `RTB` flies the drone home.

---

### Mission Logging

Each mission writes its artefacts to an isolated timestamped directory under `logs/mission/`:

```
logs/mission/
└── mission_20250501_143022/
    ├── mission.log          # Structured log: connect → fly → track → disconnect
    └── telemetry_log.csv    # timestamp, lat, lon, alt, move_x, move_y, move_z, frame
```

The directory is mounted from the host via Docker volume, so logs persist across container restarts and are accessible without entering the container.

---

### Design Principles

1. **Single drone handle, single process**: The `olympe.Drone` object governs all drone interaction. Creating it once in `main.py` and passing it by reference through the mission sequence avoids the fundamental impossibility of sharing live hardware sessions across processes.

2. **Config-first**: `config.toml` is the single source of truth for deployment parameters. Environment variables override it for container-level concerns (ports, paths). API request bodies override both for per-call overrides. This three-tier precedence means the system can be tuned at any granularity without rebuilding the image.

3. **Test mode parity**: `mode_type = "test"` is not a stub — it runs the complete pipeline identically to live mode, including drone connection, GPS navigation, YOLO inference, and telemetry logging. The only suppressed operation is `move_by`. This ensures that field-tested system behaviour matches lab-tested behaviour exactly.

4. **Offline-first**: YOLO weights (`yolov5su`) are baked into the image at build time. The container starts without internet. Field deployment uses `make export-gpu` / `make export-cpu` to produce a single `.tar.gz` per variant, transferred via USB.

---

### Future Extensibility

- **Multiple camera-traps**: Add additional `[mqtt_topics."cameratrap/events/<id>"]` blocks to `config.toml` — no code changes required
- **Custom flight scripts**: Implement the `run(drone, **kwargs)` interface and add a new directory under `openpasslite/missions/`
- **Alternative detection models**: Swap the YOLO model string in `controller.py` — the tracking loop is model-agnostic
- **Multi-drone fleets**: Each drone instance requires its own `smartfield` container with a distinct port and SkyController IP — the stateless FastAPI layer supports this with environment variable overrides

---

## System Requirements

### Minimum Specifications
- **Processor**: Dual-core x86_64 or ARM64
- **RAM**: 4GB
- **Storage**: 32GB (OS) + 16GB (image) + mission log space
- **Network**: WiFi interface reachable to Parrot SkyController (192.168.53.1)
- **OS**: Ubuntu 22.04 LTS (tested), any Linux with Docker Engine 24.0+

### Recommended Specifications
- **Processor**: Quad-core x86_64
- **RAM**: 8GB
- **Storage**: 128GB SSD (mission video accumulates quickly)
- **GPU**: NVIDIA GPU with CUDA 12.1 support for real-time YOLO inference
- **Network**: Dedicated WiFi interface for drone control; separate interface for MQTT broker traffic

### Power Requirements
- **Idle (services running, no drone)**: ~10–15W
- **Active Mission (drone connected, YOLO running)**: ~20–35W (GPU variant higher)
- **Recommended Field Battery**: 200Wh+ power station for 6+ hours of standby + 10–15 missions

---

**Note**: Smartfield is designed for ecological research operations. Ensure compliance with local regulations governing UAS operations and wildlife observation in your deployment jurisdiction before conducting live missions.
