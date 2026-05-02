import sys
import logging
import os
from pathlib import Path

import toml
from SoftwarePilot import SoftwarePilot

from openpasslite.missions.LTT import script as ltt
from openpasslite.missions.RTB import script as rtb
from openpasslite.missions.TAKEOFF import script as takeoff
from openpasslite.missions.LAND import script as land
from wildwing import controller

_log = logging.getLogger(__name__)


def _load_mission_config() -> dict:
    config_path = Path(os.environ.get("CONFIG_PATH", str(Path(__file__).parent.parent.parent / "config.toml")))
    if not config_path.exists():
        _log.warning("config.toml not found at %s", config_path)
        return {}
    return toml.load(config_path).get("mission", {})


def _setup_mission_logging(output_directory: str) -> logging.FileHandler:
    log_path = os.path.join(output_directory, "mission.log")
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    return handler


def main(lat, long, output_directory, mode_type):
    cfg = _load_mission_config()
    lat       = lat       if lat       is not None else cfg.get("lat")
    long      = long      if long      is not None else cfg.get("long")
    mode_type = mode_type if mode_type is not None else cfg.get("mode_type", "live")

    handler = _setup_mission_logging(output_directory)
    try:
        _log.info("mission started — lat=%s long=%s mode=%s output=%s", lat, long, mode_type, output_directory)

        sp = SoftwarePilot()
        drone = sp.setup_drone("parrot_anafi", 1, "None")
        drone.connect()
        _log.info("drone connected")

        if mode_type == "test":
            takeoff.run(drone, lat=lat, long=long)
            controller.run(drone, output_directory, mode_type)
            land.run(drone)
        else:
            ltt.run(drone, lat=lat, long=long)
            controller.run(drone, output_directory, mode_type)
            rtb.run(drone)

        drone.disconnect()
        _log.info("drone disconnected — mission complete")
    except Exception as e:
        _log.error("mission failed: %s", e)
        raise
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <output_directory> <mode_type>")
        sys.exit(1)
    main(lat=None, long=None, output_directory=sys.argv[1], mode_type=sys.argv[2])
