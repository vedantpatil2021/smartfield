import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import toml
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import subscriber

SERVICE = "mqtt_subscriber"

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT   = int(os.environ.get("MQTT_PORT", 1883))
CLIENT_ID   = os.environ.get("MQTT_CLIENT_ID", "smartfield_subscriber")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_log        = logging.getLogger(SERVICE)
_start_time = datetime.now(timezone.utc)


def ok(data: dict) -> dict:
    return {"success": True, "data": data}


def err(message: str) -> dict:
    return {"success": False, "error": message}


def _load_topic_mappings() -> dict:
    # Root-level config.toml — override with CONFIG_PATH env var (e.g. in Docker)
    config_path = Path(os.environ.get("CONFIG_PATH", str(Path(__file__).parent.parent.parent / "config.toml")))
    if not config_path.exists():
        _log.warning("config.toml not found at %s — no topics will be subscribed", config_path)
        return {}
    return toml.load(config_path).get("mqtt_topics", {})


_mqtt_client = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _mqtt_client
    _log.info("mqtt_subscriber service starting")

    topic_mappings = _load_topic_mappings()
    _mqtt_client   = subscriber.build_client(topic_mappings, CLIENT_ID)

    try:
        _mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        _mqtt_client.loop_start()
        _log.info("MQTT loop started — broker=%s:%d topics=%d", MQTT_BROKER, MQTT_PORT, len(topic_mappings))
    except Exception as e:
        _log.error("could not connect to MQTT broker: %s", e)

    yield

    _log.info("mqtt_subscriber service shutting down")
    if _mqtt_client:
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()


app = FastAPI(title="MQTT Subscriber", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return ok({"status": "ok"})


@app.get("/ready")
async def ready():
    return ok({"ready": subscriber.broker_connected, "broker_connected": subscriber.broker_connected})


@app.get("/metrics")
async def metrics():
    uptime = (datetime.now(timezone.utc) - _start_time).total_seconds()
    return ok({
        "uptime_seconds": uptime,
        "mqtt_messages":  subscriber.message_count,
        "last_event_at":  subscriber.last_event_ts,
        "broker_connected": subscriber.broker_connected,
    })


@app.get("/api/v1/info")
async def info():
    return ok({
        "service":      SERVICE,
        "broker_host":  MQTT_BROKER,
        "broker_port":  MQTT_PORT,
        "client_id":    CLIENT_ID,
        "smartfield_url": subscriber.SMARTFIELD_URL,
    })


if __name__ == "__main__":
    port = int(os.environ.get("APP_PORT", 9987))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
