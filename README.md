# SmartField


## System Requirements

- **OS**: Ubuntu 22.04 LTS
- **RAM**: Minimum 4GB
- **Hardware**: Anafi Parrot drone
- **Software**: Docker and Docker Compose

## Services

### openpasslite (:2177) - Anafi drone control with LTT/RTB missions
- `GET /` - Health check
- `POST /start_mission` - Start drone mission
- `POST /stop_mission` - Stop drone mission  
- `GET /mission_status` - Get mission status
- `GET /logs` - View service logs

### smartfield (:2188) - Field monitoring and analysis
- `GET /` - Health check
- `GET /initiate_process` - Start field analysis
- `GET /logs` - View logs (HTML)
- `GET /pipeline_status` - Get processing status
- `GET /health` - Service health
- `POST /start_mission` - Start field mission
- `POST /stop_mission` - Stop field mission

### wildwings (:2199) - Route visualization and navigation
- `GET /` - Health check
- `POST /start_mission` - Start navigation mission
- `POST /stop_mission` - Stop navigation mission
- `GET /mission_status` - Get mission status
- `GET /logs` - View service logs

## Monitoring Stack

- **Grafana** (:3000) - Dashboard (admin/admin)
- **Loki** (:3100) - Log aggregation
- **Promtail** - Log collection

## Quick Start

```bash
# Build and run all services
docker-compose up --build

# Or with Podman
podman-compose up --build
```

## Configuration

Edit `config.toml` for service-specific settings. Logs are stored in `./logs/` and missions in `./mission/`.