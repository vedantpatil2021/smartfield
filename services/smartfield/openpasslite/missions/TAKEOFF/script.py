import logging
import time

_log = logging.getLogger(__name__)

_BAR = "=" * 52


def _banner(title: str, error: bool = False):
    emit = _log.error if error else _log.info
    emit(_BAR)
    emit("  %s", title)
    emit(_BAR)


def run(drone, lat=None, long=None):
    _banner("TAKEOFF")
    try:
        drone.piloting.takeoff()
        time.sleep(8)
        _banner("TAKEOFF COMPLETE")
    except Exception as e:
        _banner(f"TAKEOFF FAILED: {e}", error=True)
        raise
