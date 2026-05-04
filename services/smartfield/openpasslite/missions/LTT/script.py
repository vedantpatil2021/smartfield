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
    _banner("LTT — NAVIGATE TO SITE")
    try:
        lat_float = float(lat)
        long_float = float(long)
    except (ValueError, TypeError):
        raise Exception(f"Invalid coordinates: lat={lat}, long={long}")

    try:
        _log.info("Checking GPS status")
        coordinates = drone.get_drone_coordinates()
        if not coordinates or coordinates[0] == 0.0 or coordinates[1] == 0.0:
            raise Exception("GPS coordinates not available — drone may not have GPS lock")

        _log.info("Current GPS: lat=%.6f lon=%.6f alt=%.2fm", coordinates[0], coordinates[1], coordinates[2])

        _log.info("Initiating takeoff")
        drone.piloting.takeoff()
        _log.info("Takeoff completed")

        _log.info("Detting gimbal orientation")
        drone.camera.controls.set_orientation(0, -70, 0, wait=True)
        time.sleep(3)

        _log.info("navigating to target: lat=%.6f lon=%.6f alt=13m", lat_float, long_float)
        try:
            drone.piloting.move_to(
                lat=lat_float,
                lon=long_float,
                alt=13,
                orientation_mode="TO_TARGET",
                heading=0,
                wait=True,
            )
            _log.info("navigation completed")
        except AssertionError as e:
            _log.warning("navigation with wait=True failed (%s), retrying without wait", e)
            drone.piloting.move_to(
                lat=lat_float,
                lon=long_float,
                alt=13,
                orientation_mode="TO_TARGET",
                heading=0,
                wait=False,
            )
            _log.info("Navigation command sent (not waiting for completion)")

        final_coords = drone.get_drone_coordinates()
        _log.info("Final position: lat=%.6f lon=%.6f alt=%.2fm", final_coords[0], final_coords[1], final_coords[2])
        _banner("LTT COMPLETE")

    except Exception as e:
        _banner(f"LTT FAILED: {e}", error=True)
        raise
