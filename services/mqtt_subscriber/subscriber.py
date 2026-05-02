import json
import logging
import os
import threading

import paho.mqtt.client as mqtt
import requests

_log = logging.getLogger(__name__)

SMARTFIELD_URL = os.environ.get("SMARTFIELD_URL", "http://localhost:9988")
MQTT_QOS       = int(os.environ.get("MQTT_QOS", 1))

# State read by main.py (updated from the MQTT background thread)
_lock            = threading.Lock()
broker_connected = False
message_count    = 0
last_event_ts    = None


def _set_state(**kwargs):
    global broker_connected, message_count, last_event_ts
    with _lock:
        for k, v in kwargs.items():
            globals()[k] = v


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        _set_state(broker_connected=True)
        topic_mappings = userdata or {}
        for topic in topic_mappings:
            client.subscribe(topic, qos=MQTT_QOS)
            _log.info("subscribed to topic: %s", topic)
        _log.info("connected to MQTT broker")
    else:
        _set_state(broker_connected=False)
        _log.error("broker connection failed (rc=%d)", rc)


def on_disconnect(client, userdata, rc, properties=None):
    _set_state(broker_connected=False)
    if rc != 0:
        _log.warning("unexpected MQTT disconnect (rc=%d) — will auto-reconnect", rc)


def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        topic_mappings = userdata or {}
        mapping = topic_mappings.get(topic)
        if not mapping:
            _log.warning("message on unrecognised topic: %s — ignoring", topic)
            return

        payload = json.loads(msg.payload.decode("utf-8"))
        _log.info("MQTT event received — topic=%s keys=%s", topic, list(payload.keys()))

        from datetime import datetime, timezone
        with _lock:
            globals()["message_count"] += 1
            globals()["last_event_ts"] = datetime.now(timezone.utc).isoformat()

        lat   = mapping["lat"]
        lon   = mapping["lon"]
        camid = mapping["camid"]

        resp = requests.post(
            f"{SMARTFIELD_URL}/initiate_pipeline",
            params={"lat": lat, "lon": lon, "camid": camid},
            timeout=30,
        )

        if resp.status_code == 200:
            _log.info("pipeline triggered — camid=%s lat=%s lon=%s", camid, lat, lon)
        else:
            _log.error("smartfield rejected trigger: HTTP %d", resp.status_code)

    except json.JSONDecodeError as e:
        _log.error("invalid JSON on topic %s: %s", topic, e)
    except requests.RequestException as e:
        _log.error("HTTP error triggering pipeline: %s", e)
    except Exception as e:
        _log.error("error processing message on %s: %s", topic, e)


def build_client(topic_mappings: dict, client_id: str) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    client.user_data_set(topic_mappings)
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message
    return client
