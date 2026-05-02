import logging
import time

_log = logging.getLogger(__name__)


def run(drone, lat=None, long=None):
    try:
        _log.info("setting up return to home")
        drone.rth.setup_rth()

        _log.info("returning to base")
        drone.rth.return_to_home()

        _log.info("RTB mission completed")
        time.sleep(3)

    except Exception as e:
        _log.error("RTB mission failed: %s", e)
        raise
