import cv2
import time
import queue
import logging
import olympe
import datetime
import csv
import os

from ultralytics import YOLO
from . import navigation

_log = logging.getLogger(__name__)

_model = YOLO('yolov5su')

DURATION = 200


class Tracker:
    def __init__(self, drone, output_directory, mode_type):
        self.drone = drone
        self.model = _model
        self.mode_type = mode_type
        self.output_directory = output_directory
        self.media = drone.camera.media
        self.csv_file_path = os.path.join(output_directory, 'telemetry_log.csv')
        self.FPS = 1 / 60
        self.FPS_MS = int(self.FPS * 1000)

        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["timestamp", "x", "y", "z", "move_x", "move_y", "move_z", "frame"])

    def track(self):
        while self.media.running:
            try:
                yuv_frame = self.media.frame_queue.get(timeout=0.1)
                self.media.frame_counter += 1

                if (self.media.frame_counter % 40) == 0:
                    info = yuv_frame.info()
                    height, width = (  # noqa
                        info["raw"]["frame"]["info"]["height"],
                        info["raw"]["frame"]["info"]["width"],
                    )

                    cv2_cvt_color_flag = {
                        olympe.VDEF_I420: cv2.COLOR_YUV2BGR_I420,
                        olympe.VDEF_NV12: cv2.COLOR_YUV2BGR_NV12,
                    }[yuv_frame.format()]

                    cv2frame = cv2.cvtColor(yuv_frame.as_ndarray(), cv2_cvt_color_flag)
                    x_direction, y_direction, z_direction = navigation.get_next_action(
                        cv2frame, self.model, self.output_directory, self.media.frame_counter
                    )

                    telemetry = self.drone.get_drone_coordinates()
                    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                    with open(self.csv_file_path, mode='a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow([
                            timestamp,
                            telemetry[0], telemetry[1], telemetry[2],
                            x_direction, y_direction, z_direction,
                            self.media.frame_counter,
                        ])

                    _log.debug(
                        "frame=%d move=(%.2f, %.2f, %.2f) pos=(%.6f, %.6f, %.2fm)",
                        self.media.frame_counter, x_direction, y_direction, z_direction,
                        telemetry[0], telemetry[1], telemetry[2],
                    )

                    if self.mode_type != "test":
                        self.drone.piloting.move_by(x_direction, y_direction, z_direction, 0)

            except queue.Empty:
                continue

        yuv_frame.unref()


def run(drone, output_directory, mode_type):
    _log.info("tracker starting — mode=%s duration=%ds", mode_type, DURATION)
    tracker = Tracker(drone, output_directory, mode_type)

    drone.camera.media.setup_recording()
    drone.camera.media.start_recording()
    _log.info("recording started")
    time.sleep(5)

    drone.camera.media.setup_stream(yuv_frame_processing=tracker.track)
    drone.camera.media.start_stream()
    _log.info("stream started")

    cv2.namedWindow('tracking', cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow('tracking', 500, 500)
    cv2.moveWindow('tracking', 0, 0)

    time.sleep(DURATION)

    drone.camera.media.stop_stream()
    _log.info("stream stopped")
    drone.camera.media.stop_recording()
    drone.camera.media.download_last_media()
    _log.info("recording saved")
