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
    _banner("LANDING")
    try:
        drone.piloting.land()
        time.sleep(5)
        _banner("LANDING COMPLETE")
    except Exception as e:
        _banner(f"LANDING FAILED: {e}", error=True)
        raise
