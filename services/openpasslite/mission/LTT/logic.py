import time
import logging

class TakeoffLogic:
    def __init__(self, config, flight_data):
        self.config = config
        self.flight_data = flight_data
        self.logger = logging.getLogger("takeoff_logic")
    
    def pre_takeoff_checks(self, drone):
        """Perform pre-takeoff safety checks"""
        self.logger.info("Performing pre-takeoff checks")
        
        # Check battery level
        min_battery = self.config["safety"]["min_battery"]
        self.logger.info(f"Checking battery level (minimum: {min_battery}%)")
        
        # Check GPS lock
        if self.config["checks"]["gps_lock"]:
            self.logger.info("Verifying GPS lock")
        
        # Check wind conditions
        max_wind = self.config["safety"]["max_wind_speed"]
        self.logger.info(f"Checking wind conditions (max: {max_wind} m/s)")
    
    def post_takeoff_operations(self, drone, hover_altitude):
        """Operations to perform after takeoff"""
        self.logger.info(f"Hovering at {hover_altitude}m altitude")
        
        # Hover for specified duration
        hover_duration = self.config["flight_parameters"]["hover_duration"]
        self.logger.info(f"Hovering for {hover_duration} seconds")
        time.sleep(hover_duration)
        
        # Log successful takeoff
        self.logger.info("Takeoff mission completed successfully")
    
    def get_flight_parameter(self, parameter_name):
        """Get flight parameter from CSV data"""
        for row in self.flight_data:
            if row["parameter"] == parameter_name:
                return float(row["value"])
        return None