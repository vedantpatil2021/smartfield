import cv2
import time
import queue
import olympe
from SoftwarePilot import SoftwarePilot
from ultralytics import YOLO
import navigation as navigation
import sys
import json
import time
import csv 
import os
import datetime


DURATION = 200 # duration in seconds

# Retrieve the filename from command-line arguments
if len(sys.argv) < 2:
    print("Usage: python controller.py <output_directory>")
    sys.exit(1)

output_directory = sys.argv[1]

# Define CSV file path to store telemetry data
# Define the CSV file path
csv_file_path = os.path.join(output_directory, 'telemetry_log.csv')

# Ensure the CSV file has a header row
if not os.path.exists(csv_file_path):
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "x", "y", "z", "move_x", "move_y", "move_z", "frame"])


# Runs what to do on every yuv_frame of the stream, modify it as needed
class Tracker:
    def __init__(self, drone, model):
        self.drone = drone
        self.media = drone.camera.media
        self.model = model
        self.frame = None
        self.FPS = 1/60
        self.FPS_MS = int(self.FPS * 1000)

    def track(self):
        while self.media.running:
            try:
                yuv_frame = self.media.frame_queue.get(timeout=0.1)
                self.media.frame_counter += 1

                if (self.media.frame_counter % 40) == 0: # note: adjust this number to change how often the drone moves (every 20 frames in this case)
                    # the VideoFrame.info() dictionary contains some useful information
                    # such as the video resolution
                    info = yuv_frame.info()

                    height, width = (  # noqa
                        info["raw"]["frame"]["info"]["height"],
                        info["raw"]["frame"]["info"]["width"],
                    )

                    # yuv_frame.vmeta() returns a dictionary that contains additional
                    # metadata from the drone (GPS coordinates, battery percentage, ...)

                    # convert pdraw YUV flag to OpenCV YUV flag
                    cv2_cvt_color_flag = {
                        olympe.VDEF_I420: cv2.COLOR_YUV2BGR_I420,
                        olympe.VDEF_NV12: cv2.COLOR_YUV2BGR_NV12,
                    }[yuv_frame.format()]

                    cv2frame = cv2.cvtColor(yuv_frame.as_ndarray(), cv2_cvt_color_flag)

                    x_direction, y_direction, z_direction = navigation.get_next_action(cv2frame, self.model, output_directory, self.media.frame_counter)  # KEY LINE
                    #self.update_frame(cv2.imread('result.jpg'))

                    # save telemetry 
                   
                    telemetry = drone.get_drone_coordinates()
                
                     # Convert time.time() to datetime object
                    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                    # Append telemetry data to CSV file
                    with open(csv_file_path, mode='a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow([timestamp, telemetry[0], telemetry[1], telemetry[2], x_direction, y_direction, z_direction, self.media.frame_counter])

                    self.drone.piloting.move_by(x_direction, y_direction, z_direction, 0)

                # cv2.imwrite(os.path.join(self.download_dir, "test{}.jpg".format(self.frame_counter)), cv2frame)
               
            except queue.Empty:
                continue

        # You should process your frames here and release (unref) them when you're done.
        # Don't hold a reference on your frames for too long to avoid memory leaks and/or memory
        # pool exhaustion.
        yuv_frame.unref()


# Setup a parrot anafi drone, connected through a controller, without a specific download directory
sp = SoftwarePilot()

os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib_config'
os.environ['YOLO_CONFIG_DIR'] = '/tmp/yolo_config'
os.environ['FONTCONFIG_PATH'] = '/tmp/fontconfig'
os.environ['FONTCONFIG_FILE'] = '/tmp/fontconfig/fonts.conf'
os.environ['XDG_CONFIG_HOME'] = '/tmp/xdg_config'
os.environ['XDG_DATA_HOME'] = '/tmp/xdg_data'
os.environ['XDG_CACHE_HOME'] = '/tmp/xdg_cache'
os.environ['OLYMPE_HOME'] = '/tmp/olympe'

# Create all necessary directories
for path in [
    os.environ['MPLCONFIGDIR'],
    os.environ['YOLO_CONFIG_DIR'],
    os.environ['FONTCONFIG_PATH'],
    os.path.join(os.environ['XDG_CONFIG_HOME']),
    os.path.join(os.environ['XDG_DATA_HOME'], 'parrot', 'olympe'),
    os.environ['OLYMPE_HOME'],
    '/tmp/yolo_models'
]:
    os.makedirs(path, exist_ok=True)

# Specify the model path
model_path = '/tmp/yolo_models/yolov5su.pt'

model = YOLO(model_path)

# Connect to the drone
drone = sp.setup_drone("parrot_anafi", 1, "None")
drone.connect()

# Create a tracker object
tracker = Tracker(drone, model)

# set up recording
drone.camera.media.setup_recording()
drone.camera.media.start_recording()

# wait for drone to stabilize
time.sleep(5)

# Start the stream
drone.camera.media.setup_stream(yuv_frame_processing=tracker.track)
drone.camera.media.start_stream() 

# set window properties
cv2.namedWindow('tracking', cv2.WINDOW_KEEPRATIO)
cv2.resizeWindow('tracking', 500, 500)
cv2.moveWindow('tracking', 0, 0)

# set track duration in seconds
time.sleep(DURATION)
drone.camera.media.stop_stream()

# stop recording
drone.camera.media.stop_recording()
drone.camera.media.download_last_media()