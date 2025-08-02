import json
import csv
import os
from pathlib import Path
from .logic import LandingLogic

def run(drone):
    """Main landing mission entry point"""
    mission_dir = Path(__file__).parent
    config_path = mission_dir / "config.json"
    csv_path = mission_dir / "data.csv"

    try:
        drone.connect()
        drone.piloting.land()
        drone.disconnect()
        
    except Exception as e:
        print(f"Landing mission failed: {e}")
        raise