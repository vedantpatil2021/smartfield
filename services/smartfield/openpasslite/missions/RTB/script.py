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
    _banner("RTB — RETURN TO BASE")
    try:
        _log.info("Setting up return to home")
        drone.rth.setup_rth()

        _log.info("Returning to base")
        drone.rth.return_to_home()

        time.sleep(3)
        _banner("RTB COMPLETE")

    except Exception as e:
        _banner(f"RTB FAILED: {e}", error=True)
        raise
