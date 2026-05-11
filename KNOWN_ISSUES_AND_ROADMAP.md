# Known Issues and Roadmap

This document covers known limitations of the current Smartfield deployment, architectural decisions that have long-term implications, and directions for future work. It is intended for engineers planning to extend, scale, or redeploy the system.

---

## Known Issues

### Dashboard Performance and Startup Blankout

The field operations dashboard is built on PyQt6 and OpenCV, neither of which is lightweight. As the host environment scales (more services, higher system load, larger conda environment), the startup black-out period will increase. This is a Qt/X11 paint initialisation delay and is not a crash.

> [!WARNING]
> Do not migrate the dashboard to a web-based UI. Browser-based RTSP streaming is a significant engineering problem. MediaMTX, the most common relay solution, introduces a re-transcoding loop that is difficult to stabilise and adds substantial latency. The PyQt6 + OpenCV stack, despite its resource footprint, is the most reliable path for low-latency RTSP rendering on an edge device. Switching stacks will cost considerably more time than it saves.

---

### RTSP Stream Latency

The live video stream introduces variable latency depending on network conditions between the SkyController and the host machine. This is inherent to RTSP over UDP transport and cannot be fully eliminated without switching to a different streaming protocol.

---

### Host Network Dependency

All services currently run with `network_mode: host`. Migrating to a named Docker network or a Kubernetes pod network will require reconfiguring service discovery and may break drone connectivity.

> [!CAUTION]
> The Parrot ANAFI expects to be reachable directly on the host machine's WiFi interface at `192.168.53.1`. Any network abstraction layer placed between the host and the drone (bridge networks, NAT, overlay networks) risks disrupting the Olympe connection, which has strict latency requirements and no built-in reconnection logic.

---

### Mission Log Design

The mission logging system is functional but lacks structured querying, log rotation, and storage bounds. Without periodic cleanup via `make clean-logs`, mission directories will accumulate and consume significant disk space over time, particularly when video files are written.

---

### Drone Connection Architecture (Monolithic Requirement)

The decision to keep `openpasslite` and `wildwings` inside a single container process was a deliberate architectural choice, not a shortcut. Splitting them into separate microservices would produce race conditions on the drone's internal connection thread.

> [!IMPORTANT]
> Olympe and SoftwarePilot maintain drone state on a single-threaded internal network loop. If `openpasslite` and `wildwings` are separated into independent microservices, the first service to acquire the drone connection will be unable to release it unless `disconnect()` is called explicitly and confirmed before the second service calls `connect()`. This handoff is unreliable in practice. A failed disconnect leaves the drone holding an orphaned session that requires a physical reboot to clear. Always keep all drone-related code inside a single container process.

---

## Roadmap and Future Possibilities

### Kubernetes Migration

The project architecture is compatible with Kubernetes deployment. The stateless FastAPI services (`smartfield` and `mqtt_subscriber`) can be packaged as standard pods with minimal changes.

> [!NOTE]
> An air-gapped Kubernetes cluster is strongly recommended for field deployments. This ensures the VPC remains bound to the host network of the edge device at all times. Standard cloud-connected Kubernetes configurations will not meet the latency requirements for real-time drone control traffic and introduce an external dependency that is unavailable in remote field environments.

---

### Pipeline Extensibility

The project supports a pluggable pipeline model. Additional processing services can be integrated by exposing a consistent Python API interface. New mission types can be added by implementing the `run(drone, **kwargs)` interface under `openpasslite/missions/` without modifying the orchestration logic in `main.py`.

> [!IMPORTANT]
> Regardless of how the pipeline is extended, all drone-related operations must remain inside a single container process. Distributing drone operations across microservices will produce connection lifecycle failures that are difficult to diagnose and may require a drone reboot to recover from.

---

### Multi-Drone Fleet Scalability

The system is horizontally scalable at the service layer. Multiple `smartfield` instances can be deployed on separate ports with distinct SkyController IP addresses to support multi-drone fleet operations. No code changes are required as both the port and the drone IP are environment-variable-configurable.

---

### Structured Log Pipeline

Future work could introduce a structured logging backend (e.g., writing mission events to a local SQLite database or a time-series store) to enable querying across missions, automatic retention policies, and richer dashboard analytics without relying on raw log file parsing.
