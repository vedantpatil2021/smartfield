import json
import csv
from pathlib import Path

def run(drone, lat=None, long=None):
    mission_dir = Path(__file__).parent
    config_path = mission_dir / "config.json"
    csv_path = mission_dir / "data.csv"
        
    try:
        drone.connect()
        drone.camera.media.setup_recording("standard","res_dci_4k","fps_24","ratio_15")
        drone.camera.media.start_recording()
        drone.piloting.takeoff()
        heading = drone.get_drone_heading()
        drone.piloting.move_to(lat,long,20,heading,True)
        drone.camera.media.stop_recording()
        drone.camera.media.download_last_media()

    except Exception as e:
        print(f"Takeoff mission failed: {e}")
        raise