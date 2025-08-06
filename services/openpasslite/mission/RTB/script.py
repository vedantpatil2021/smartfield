import json
import csv
import os
from pathlib import Path
from .logic import LandingLogic

def run(drone, lat=None, long=None):
    """Main landing mission entry point"""
    mission_dir = Path(__file__).parent
    config_path = mission_dir / "config.json"
    csv_path = mission_dir / "data.csv"

    try:
        drone.connect()
        drone.camera.media.setup_recording("standard","res_dci_4k","fps_24","ratio_15")
        drone.camera.media.start_recording()
        heading = drone.get_drone_heading()
        drone.piloting.move_to(lat,long,20,heading,True)
        drone.piloting.land()
        drone.camera.media.stop_recording()
        drone.camera.media.download_last_media()
        drone.disconnect()
        
    except Exception as e:
        print(f"Landing mission failed: {e}")
        raise