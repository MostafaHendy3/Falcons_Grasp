import sys
import cv2
import numpy as np
import threading
import time
import paho.mqtt.client as mqtt

# Define color ranges for detection
colors = {
    "red": ((166, 166, 0), (179, 255, 255)),
    "cyan": ((99, 175, 40), (109, 255, 255)),
    "pink": ((130, 98, 5), (150, 151, 255)),
    "purple": ((125, 151, 0), (143, 255, 255)),
    "blue": ((104, 155, 146), (119, 255, 255)),
    "white": ((89, 80, 122), (109, 115, 255)),
    "dark green": ((79, 49, 0), (91, 255, 255)),
    "green": ((60, 33, 0), (76, 255, 255)),
    "yellow": ((21, 81, 144), (42, 255, 255)),
    "black": ((102, 0, 0), (160, 255, 43))
}

detected_colors = [set() for _ in range(4)]
color_detection_counts = {color: 0 for color in colors.keys()}


class CameraThread(threading.Thread):
    def __init__(self, rtsp_url, camera_index, crop_coords, mqtt_client):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.camera_index = camera_index
        self.crop_coords = crop_coords
        self.running = False
        self.paused = False
        self.condition = threading.Condition()
        self.frame_count = 0
        self.detecting = False  # Flag to control detection
        self.mqtt_client = mqtt_client  # MQTT client instance
        self.color_detection_counters = {color: 0 for color in colors.keys()}

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.rtsp_url)

        while self.running:
            with self.condition:
                if self.paused:
                    self.condition.wait()
                    continue
            
            ret, frame = cap.read()
            if not ret:
                print(f"Camera {self.camera_index} failed to read frame. Attempting to reconnect...")
                cap.release()
                cap = cv2.VideoCapture(self.rtsp_url)
                continue

            # Crop the frame using the specified coordinates
            x_start, y_start, x_end, y_end = self.crop_coords
            cropped_frame = frame[y_start:y_end, x_start:x_end]

            # Only detect colors if detecting is enabled
            if self.detecting:
                self.detect_custom_colors(cropped_frame)

            self.frame_count += 1
            time.sleep(0.001)

        cap.release()

    def detect_custom_colors(self, frame):
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        for color_name, (lower, upper) in colors.items():
            mask = cv2.inRange(hsv_frame, np.array(lower), np.array(upper))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            detected = False  # Flag to check if the color was detected in this frame

            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 5000:
                    continue
                else:
                    print(f"Camera {self.camera_index} - Color: {color_name}, Area: {area}")
                    detected_colors[self.camera_index].add(color_name)
                    detected = True  # Set detected flag to True
                    break

            # Update the detection counter
            if detected:
                self.color_detection_counters[color_name] += 1
            else:
                self.color_detection_counters[color_name] = max(0, self.color_detection_counters[color_name] - 1)  # Decrease if not detected

            # Publish the color count if detected in the last 10 frames
            if self.color_detection_counters[color_name] >= 10:
                self.publish_color_count()  # Publish the count of detected colors
                self.color_detection_counters[color_name] = 0  # Reset the counter after publishing

        if detected_colors:
            print(f"Camera {self.camera_index} Detected colors: {detected_colors[self.camera_index]}")
    def publish_color_count(self):
        num_colors = len(detected_colors[self.camera_index])*10
        try:
            # Publish the number of detected colors with QoS level 1
            self.mqtt_client.publish(f"FalconGrasp/camera/{self.camera_index}", num_colors)
        except Exception as e:
            print(f"Error publishing to MQTT: {e}")

    def stop(self):
        self.running = False
        with self.condition:
            self.condition.notify()

    def pause(self):
        with self.condition:
            self.paused = True

    def resume(self):
        with self.condition:
            self.paused = False
            self.condition.notify()

    def start_detection(self):
        self.detecting = True

    def stop_detection(self):
        self.detecting = False
        # Clear detected colors when stopping detection
        detected_colors[self.camera_index].clear()
        print(f"Camera {self.camera_index} detection stopped. Cleared detected colors.")


class VideoCaptureManager:
    def __init__(self, rtsp_urls, crop_coords_list, mqtt_client):
        self.camera_threads = []
        for i, url in enumerate(rtsp_urls):
            thread = CameraThread(url, i, crop_coords_list[i], mqtt_client)  # Pass the MQTT client
            self.camera_threads.append(thread)

    def start_all(self):
        for thread in self.camera_threads:
            if not thread.is_alive():
                thread.running = True
                thread.paused = False
                thread.start()
            else:
                thread.resume()

    def stop_all(self):
        for thread in self.camera_threads:
            thread.stop()
        for thread in self.camera_threads:
            thread.join()

    def pause_all(self):
        for thread in self.camera_threads:
            if thread.is_alive():
                thread.pause()
            else:
                print(f"Thread {thread.camera_index} is not alive and cannot be paused.")

    def resume_all(self):
        for thread in self.camera_threads:
            thread.resume()


def on_mqtt_message(client, userdata, message):
    if message.topic == "FalconGrasp/game/start":
        print(f"Received MQTT message to start: {message.payload.decode()}")
        for thread in manager.camera_threads:
            thread.start_detection()  # Start detection for all threads
    elif message.topic == "FalconGrasp/game/stop":
        print(f"Received MQTT message to stop: {message.payload.decode()}")
        for thread in manager.camera_threads:
            thread.stop_detection()  # Stop detection for all threads
        print("All camera threads have paused detection.")


def on_mqtt_disconnect(client, userdata, rc):
    print("Disconnected from MQTT broker. Attempting to reconnect...")
    while True:
        try:
            client.reconnect()
            print("Reconnected to MQTT broker.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    rtsp_urls = [
        "rtsp://admin:infinity-2060@192.168.0.18:554",
        "rtsp://admin:infinity-2060@192.168.0.19:554",
        "rtsp://admin:infinity-2060@192.168.0.20:554",
        "rtsp://admin:infinity-2060@192.168.0.21:554"
    ]

    # Define the cropping coordinates for each camera (x_start, y_start, x_end, y_end)
    crop_coords_list = [
        (450, 370, 820, 900),  # Camera 1
        (450, 370, 840, 900),  # Camera 2
        (450, 370, 830, 900),  # Camera 3
        (460, 350, 840, 700),  # Camera 4
       
    ]

    # Set up MQTT client
    mqtt_client = mqtt.Client()
    mqtt_client.on_message = on_mqtt_message
    mqtt_client.on_disconnect = on_mqtt_disconnect  # Set the disconnect callback
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.subscribe("FalconGrasp/game/start")
    mqtt_client.subscribe("FalconGrasp/game/stop")
    mqtt_client.loop_start()

    # Initialize the VideoCaptureManager
    manager = VideoCaptureManager(rtsp_urls, crop_coords_list, mqtt_client)
    manager.start_all()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        manager.stop_all()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()