import json
import csv
from pathlib import Path

def run(drone):
    mission_dir = Path(__file__).parent
    config_path = mission_dir / "config.json"
    csv_path = mission_dir / "data.csv"
        
    try:
        drone.connect()
        drone.piloting.takeoff()

    except Exception as e:
        print(f"Takeoff mission failed: {e}")
        raise