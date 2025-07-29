def run(drone):
    drone.connect()
    drone.piloting.land()
    drone.disconnect()