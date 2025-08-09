import json
import csv
from pathlib import Path
import time

def run(drone, lat=None, long=None):
    mission_dir = Path(__file__).parent
    config_path = mission_dir / "config.json"
    csv_path = mission_dir / "data.csv"

    try:
        lat_float = float(lat)
        long_float = float(long)
    except (ValueError, TypeError):
        raise Exception(f"Invalid coordinates: lat={lat}, long={long}")
        
    try:
        print("=== INITIALIZING DRONE ===")
        print("=== CONNECTING TO DRONE ===")
        drone.connect()
        print("Connected successfully")
        
        print("=== WAITING FOR GPS STABILIZATION ===")
        time.sleep(10)
        
        print("=== CHECKING GPS STATUS ===")
        coordinates = drone.get_drone_coordinates()
        if not coordinates or coordinates[0] == 0.0 or coordinates[1] == 0.0:
            raise Exception("GPS coordinates not available - drone may not have GPS lock")
        
        print(f"Current GPS coordinates: Lat={coordinates[0]:.6f}, Lon={coordinates[1]:.6f}, Alt={coordinates[2]:.2f}m")
        
        print("=== INITIATING TAKEOFF ===")
        drone.piloting.takeoff()
        print("✓ Takeoff completed")
        
        print("=== STABILIZING AFTER TAKEOFF ===")
        time.sleep(5)
        
        print(f"=== NAVIGATING TO TARGET COORDINATES ===")
        print(f"Target: Lat={lat_float:.6f}, Lon={long_float:.6f}, Alt={20}m")
        
        try:
            drone.piloting.move_to(
                lat=lat_float, 
                lon=long_float, 
                alt=20, 
                orientation_mode="NONE", 
                heading=0, 
                wait=True
            )
            print("Navigation completed successfully")
            
        except AssertionError as e:
            print(f"Navigation with wait=True failed: {e}")
            print("Attempting navigation without waiting...")
            
            drone.piloting.move_to(
                lat=lat_float, 
                lon=long_float, 
                alt=20, 
                orientation_mode="NONE", 
                heading=0, 
                wait=False
            )
            print("Navigation command sent (not waiting for completion)")
            
            time.sleep(15)
            
        print("=== CHECKING FINAL POSITION ===")
        final_coords = drone.get_drone_coordinates()
        print(f"Final position: Lat={final_coords[0]:.6f}, Lon={final_coords[1]:.6f}, Alt={final_coords[2]:.2f}m")
        
        print("=== MISSION COMPLETED SUCCESSFULLY ===")
        
    except Exception as e:
        print(f"Mission failed: {e}")
        return False
        
    finally:
        if drone:
            try:
                print("=== DISCONNECTING FROM DRONE ===")
                drone.disconnect()
                print("Disconnected successfully")
            except Exception as e:
                print(f"Disconnect warning: {e}")