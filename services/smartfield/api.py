import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from main import main as run_mission

SERVICE = "smartfield"
MISSION_LOGS_DIR = os.environ.get("MISSION_LOGS_DIR", "/home/icicle/smartfield/logs/mission")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_log = logging.getLogger(SERVICE)
_start_time = datetime.now(timezone.utc)


def ok(data: dict) -> dict:
    return {"success": True, "data": data}


def err(message: str) -> dict:
    return {"success": False, "error": message}


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _log.info("smartfield service starting")
    yield
    _log.info("smartfield service shutting down")


app = FastAPI(title="Smartfield", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MissionRequest(BaseModel):
    lat: Optional[float] = None        # falls back to config.toml [mission] lat
    long: Optional[float] = None       # falls back to config.toml [mission] long
    mode_type: Optional[str] = None    # falls back to config.toml [mission] mode_type


@app.get("/health")
async def health():
    return ok({"status": "ok"})


@app.get("/ready")
async def ready():
    return ok({"ready": True})


@app.get("/metrics")
async def metrics():
    uptime = (datetime.now(timezone.utc) - _start_time).total_seconds()
    return ok({"uptime_seconds": uptime})


@app.get("/api/v1/info")
async def info():
    return ok({"service": SERVICE, "version": "1.0.0"})


@app.get("/initiate_pipeline")
def initiate_pipeline(lat: float, lon: float, camid: str):
    """Called by mqtt_subscriber when a camera-trap event fires."""
    req = MissionRequest(lat=lat, long=lon)
    return mission_run(req)


@app.post("/api/v1/mission/run")
def mission_run(req: MissionRequest):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mission_id = f"mission_{timestamp}"
    output_directory = os.path.join(MISSION_LOGS_DIR, mission_id)
    os.makedirs(output_directory, exist_ok=True)

    _log.info("mission %s starting — lat=%s long=%s mode=%s", mission_id, req.lat, req.long, req.mode_type)

    try:
        run_mission(
            lat=req.lat,
            long=req.long,
            output_directory=output_directory,
            mode_type=req.mode_type,
        )
        _log.info("mission %s completed successfully", mission_id)
        return ok({"mission_id": mission_id, "output_directory": output_directory})
    except Exception as e:
        _log.error("mission %s failed: %s", mission_id, e)
        return err(str(e))


if __name__ == "__main__":
    port = int(os.environ.get("APP_PORT", 9000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
