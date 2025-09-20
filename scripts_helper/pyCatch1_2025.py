import sys
import cv2
import numpy as np
import threading
import time
import paho.mqtt.client as mqtt

# Enhanced Color Detection Script with LAB+HSV Hybrid Filtering and Live Display
# 
# Features:
# - Bilateral filtering (blur) for noise reduction while preserving edges
# - HSV color space detection for robust color identification
# - LAB color space detection for enhanced accuracy (optional)
# - Area-based filtering for object validation
# - Morphological operations for mask cleanup
# - Live video display with detection visualization
# - Unique color counting from 9 defined colors (scoring system)
# - Automatic FPS detection and playback speed control for video files
# 
# Filtering Pipeline:
# 1. Bilateral blur filter
# 2. HSV color detection (standard mode) or HSV+LAB hybrid (enhanced mode)
# 3. Area filtering only (no aspect ratio filtering)
# 
# Scoring System:
# - Counts unique colors detected from the 9 defined colors: red, cyan, pink, purple, blue, white, dark green, green, yellow, black
# - Score = number of unique colors × 10
# 
# Video Support:
# - RTSP streams: Real-time processing with minimal delay
# - Video files (.mp4, .avi, .mov, .mkv): Automatic FPS detection and proper playback speed
# - Video files automatically loop when they reach the end
# 
# Configuration:
# - Set USE_ENHANCED_DETECTION = True (line ~77) for calibrated LAB+HSV detection
# - Set DISPLAY_FRAMES = True (line ~80) to show live video feed with detections
# - Press 'q' or ESC in any display window to close all windows



# Enhanced calibrated color ranges with both HSV and LAB (optional for better accuracy)
calibrated_colors = {
    'pink': {
                'hsv': ((149, 30, 115), (170, 185, 255)), 
                'lab': ((int(15*2.55), 26+127, -19+127), (int(100*2.55), 61+127, 5+127)),  # Convert L*2.55, A+127, B+127
                'area_min': 100, 'area_max': 50000
            },
            'blue': {
                'hsv': ((106, 70, 187), (129, 233, 255)),
                'lab': ((int(43*2.55), 1+127, -65+127), (int(84*2.55), 27+127, -25+127)),  # Convert L*2.55, A+127, B+127
                'area_min': 100, 'area_max': 50000
            },

            'purple': {
                'hsv': ((132, 66, 19), (148, 255, 255)),
                'lab': ((int(0*2.55), 25+127, -127+127), (int(100*2.55), 128+127, -19+127)),  # Convert L*2.55, A+127, B+127
                'area_min': 100, 'area_max': 50000
            },
            'red': {
                'hsv': ((170, 128, 109), (179, 255, 255)),
                'lab': ((int(37*2.55), 58+127, 0), (int(100*2.55), 128+127, 128+127)),  # Convert L*2.55, A+127, B+127
                'area_min': 100, 'area_max': 50000
            },
            'green': {
                'hsv': ((43, 42, 50), (64, 201, 255)),
                'lab': ((int(30*2.55), -127+127, 21+127), (int(100*2.55), -20+127, 60+127)),  # Convert L*2.55, A+127, B+127
                'area_min': 100, 'area_max': 50000
            },
            'cyan': {
                'hsv': ((90, 104, 246), (103, 181, 254)),
                'lab': ((int(30*2.55), -99+127, -31+127), (int(95*2.55), -14+127, -13+127)),  # Convert L*2.55, A+127, B+127
                'area_min': 100, 'area_max': 50000
            },
            'dark_green': {
                'hsv': ((70, 125, 143), (88, 195, 255)),    
                'lab': ((int(21*2.55), -58+127, 4+127), (int(85*2.55), -33+127, 19+127)),  # Convert L*2.55, A+127, B+127
                'area_min': 100, 'area_max': 50000
            },
            'yellow': {
                'hsv': ((19, 82, 179), (32, 255, 255)),
                'lab': ((int(50*2.55), -69+127, 54+127), (int(100*2.55), 128+127, 128+127)),  # Convert L*2.55, A+127, B+127
                'area_min': 100, 'area_max': 50000
            },
            'white': {
                'hsv': ((10, 0, 180), (116, 19, 255)),
                'lab': ((int(85*2.55), -3+127, -8+127), (int(100*2.55), 17+127, 12+127)),  # Convert L*2.55, A+127, B+127
                'area_min': 100, 'area_max': 50000
            },
            'black': {
                'hsv': ((0, 0, 59), (179, 60, 161)),
                'lab': ((int(13*2.55), -1+127, -9+127), (int(45*2.55), 14+127, 6+127)),  # Convert L*2.55, A+127, B+127
                'area_min': 100, 'area_max': 50000
            },
}

# Flag to enable enhanced detection (set to True for better accuracy)
USE_ENHANCED_DETECTION = False

# Flag to enable frame display (set to True to show live video feed)
DISPLAY_FRAMES = True

detected_colors = [set() for _ in range(5)]
color_detection_counts = {color: 0 for color in calibrated_colors.keys()}


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
        self.color_detection_counters = {color: 0 for color in calibrated_colors.keys()}
        self.current_frame = None  # Store current frame for display
        self.display_frame = None  # Store frame with detection overlay
        self.is_video_file = self.rtsp_url.endswith(('.mp4', '.avi', '.mov', '.mkv'))  # Check if it's a video file
        self.fps = 30  # Default FPS, will be updated when cap is opened
        self.playback_speed_multiplier = 1.0  # 1.0 = normal speed, 0.5 = half speed, 2.0 = double speed

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.rtsp_url)
        
        # Get FPS for video files to control playback speed
        if self.is_video_file and cap.isOpened():
            self.fps = cap.get(cv2.CAP_PROP_FPS)
            if self.fps <= 0:  # Some videos don't report FPS correctly
                self.fps = 25  # Default to 25 FPS
            print(f"Camera {self.camera_index} - Video file detected, FPS: {self.fps}")
        else:
            print(f"Camera {self.camera_index} - RTSP stream detected")

        while self.running:
            with self.condition:
                if self.paused:
                    self.condition.wait()
                    continue
            
            ret, frame = cap.read()
            if not ret:
                if self.is_video_file:
                    # For video files, loop back to beginning
                    print(f"Camera {self.camera_index} - Video ended, looping back to start")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    # For RTSP streams, attempt to reconnect
                    print(f"Camera {self.camera_index} failed to read frame. Attempting to reconnect...")
                    cap.release()
                    cap = cv2.VideoCapture(self.rtsp_url)
                    continue

            # Crop the frame using the specified coordinates
            x_start, y_start, x_end, y_end = self.crop_coords
            cropped_frame = frame[y_start:y_end, x_start:x_end]
            
            # Store current frame for display
            self.current_frame = frame.copy()
            self.display_frame = frame.copy()

            # Only detect colors if detecting is enabled
            if self.detecting:
                self.detect_custom_colors(cropped_frame, x_start, y_start)

            self.frame_count += 1
            
            # Control playback speed based on source type
            if self.is_video_file:
                # For video files, sleep to match original FPS with speed multiplier
                time.sleep((1.0 / self.fps) / self.playback_speed_multiplier)
            else:
                # For RTSP streams, minimal sleep to prevent CPU overload
                time.sleep(0.001)

        cap.release()

    def detect_custom_colors(self, frame, crop_x_offset=0, crop_y_offset=0):
        # Apply bilateral filter for noise reduction while preserving edges
        filtered_frame = cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)
        
        # Convert to both HSV and LAB color spaces for hybrid detection
        hsv_frame = cv2.cvtColor(filtered_frame, cv2.COLOR_BGR2HSV)
        lab_frame = cv2.cvtColor(filtered_frame, cv2.COLOR_BGR2LAB)

        # Choose detection method based on flag
        if USE_ENHANCED_DETECTION:
            self.detect_enhanced_colors(hsv_frame, lab_frame, crop_x_offset, crop_y_offset)
        else:
            self.detect_standard_colors(hsv_frame, crop_x_offset, crop_y_offset)

    def detect_standard_colors(self, hsv_frame, crop_x_offset=0, crop_y_offset=0):
        """Standard color detection using original HSV ranges"""
        frame_object_count = 0  # Count objects in this frame
        
        # Color mapping for visualization
        color_bgr_map = {
            'red': (0, 0, 255), 'cyan': (255, 255, 0), 'pink': (203, 192, 255), 
            'purple': (128, 0, 128), 'blue': (255, 0, 0), 'white': (255, 255, 255),
            'dark green': (0, 100, 0), 'green': (0, 255, 0), 'yellow': (0, 255, 255), 
            'black': (0, 0, 0)
        }
        
        for color_name, ranges in calibrated_colors.items():
            hsv_lower = np.array(ranges['hsv'][0])
            hsv_upper = np.array(ranges['hsv'][1])
            # Create HSV mask
            hsv_mask = cv2.inRange(hsv_frame, np.array(hsv_lower), np.array(hsv_upper))
            
            # Clean up the mask with morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            color_mask = cv2.morphologyEx(hsv_mask, cv2.MORPH_CLOSE, kernel)
            # color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)
            
            contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            detected = False  # Flag to check if the color was detected in this frame
            color_object_count = 0  # Count objects of this color

            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 5000:
                    continue
                
                # Get bounding box for display
                x, y, w, h = cv2.boundingRect(contour)
                
                # Count valid objects (area filtering only)
                color_object_count += 1  # Count each valid object
                frame_object_count += 1  # Count towards total frame objects
                print(f"Camera {self.camera_index} - Color: {color_name}, Area: {area}")
                detected_colors[self.camera_index].add(color_name)
                detected = True  # Set detected flag to True
                
                # Draw detection on display frame if enabled
                if DISPLAY_FRAMES and self.display_frame is not None:
                    # Adjust coordinates for full frame display (add crop offset)
                    display_x = x + crop_x_offset
                    display_y = y + crop_y_offset
                    color_bgr = color_bgr_map.get(color_name, (255, 255, 255))
                    
                    # Draw bounding box
                    cv2.rectangle(self.display_frame, (display_x, display_y), 
                                (display_x + w, display_y + h), color_bgr, 2)
                    
                    # Draw label
                    cv2.putText(self.display_frame, f"{color_name.replace('_', ' ').title()}", 
                              (display_x, display_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_bgr, 2)
                    
                    # Draw area info only
                    cv2.putText(self.display_frame, f"Area: {int(area)}", 
                              (display_x, display_y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color_bgr, 1)

            # Update the detection counter
            if detected:
                self.color_detection_counters[color_name] += 1
            else:
                self.color_detection_counters[color_name] = max(0, self.color_detection_counters[color_name] - 1)  # Decrease if not detected

            # Publish the color count if detected in the last 10 frames
            if self.color_detection_counters[color_name] >= 10:
                self.publish_color_count()  # Publish the count of detected colors
                self.color_detection_counters[color_name] = 0  # Reset the counter after publishing

        # Add info overlay on display frame
        if DISPLAY_FRAMES and self.display_frame is not None:
            # Draw crop region rectangle
            cv2.rectangle(self.display_frame, (crop_x_offset, crop_y_offset), 
                         (crop_x_offset + hsv_frame.shape[1], crop_y_offset + hsv_frame.shape[0]), 
                         (0, 255, 0), 2)
            
            # Add camera info emphasizing color count
            num_colors = len(detected_colors[self.camera_index])
            info_text = f"Camera {self.camera_index} | Colors: {num_colors}/9 | Objects: {frame_object_count}"
            cv2.putText(self.display_frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Add detection status
            status_text = "DETECTING" if self.detecting else "PAUSED"
            status_color = (0, 255, 0) if self.detecting else (0, 0, 255)
            cv2.putText(self.display_frame, status_text, (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)

        if detected_colors:
            print(f"Camera {self.camera_index} Detected colors: {detected_colors[self.camera_index]}, Total objects: {frame_object_count}")

    def detect_enhanced_colors(self, hsv_frame, lab_frame, crop_x_offset=0, crop_y_offset=0):
        """Enhanced color detection using calibrated HSV+LAB hybrid approach"""
        frame_object_count = 0  # Count objects in this frame
        
        # Color mapping for visualization
        color_bgr_map = {
            'pink': (203, 192, 255), 'purple': (128, 0, 128), 'blue': (255, 0, 0), 
            'red': (0, 0, 255), 'green': (0, 255, 0), 'cyan': (255, 255, 0),
            'dark_green': (0, 100, 0), 'yellow': (0, 255, 255)
        }
        
        for color_name, ranges in calibrated_colors.items():
            # Create masks from both color spaces
            lab_lower = np.array(ranges['lab'][0])
            lab_upper = np.array(ranges['lab'][1])
            hsv_lower = np.array(ranges['hsv'][0])
            hsv_upper = np.array(ranges['hsv'][1])
            
            lab_mask = cv2.inRange(lab_frame, lab_lower, lab_upper)
            hsv_mask = cv2.inRange(hsv_frame, hsv_lower, hsv_upper)
            
            # Combine masks (intersection for precision)
            color_mask = cv2.bitwise_and(lab_mask, hsv_mask)
            
            # Clean up the mask with morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)
            
            contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            detected = False  # Flag to check if the color was detected in this frame
            color_object_count = 0  # Count objects of this color

            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Get area limits for this color
                area_min = ranges.get('area_min', 1000)
                area_max = ranges.get('area_max', 50000)
                
                if area < area_min or area > area_max:
                    continue
                
                # Get bounding box for display
                x, y, w, h = cv2.boundingRect(contour)
                
                # Count valid objects (area filtering only)
                color_object_count += 1  # Count each valid object
                frame_object_count += 1  # Count towards total frame objects
                print(f"Camera {self.camera_index} - Enhanced Color: {color_name}, Area: {area}")
                detected_colors[self.camera_index].add(color_name)
                detected = True  # Set detected flag to True
                
                # Draw detection on display frame if enabled
                if DISPLAY_FRAMES and self.display_frame is not None:
                    # Adjust coordinates for full frame display (add crop offset)
                    display_x = x + crop_x_offset
                    display_y = y + crop_y_offset
                    color_bgr = color_bgr_map.get(color_name, (255, 255, 255))
                    
                    # Draw bounding box
                    cv2.rectangle(self.display_frame, (display_x, display_y), 
                                (display_x + w, display_y + h), color_bgr, 2)
                    
                    # Draw label
                    cv2.putText(self.display_frame, f"{color_name.replace('_', ' ').title()}", 
                              (display_x, display_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_bgr, 2)
                    
                    # Draw area info only
                    cv2.putText(self.display_frame, f"Area: {int(area)}", 
                              (display_x, display_y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color_bgr, 1)

            # Update the detection counter (using original colors dict keys for compatibility)
            if color_name in self.color_detection_counters:
                if detected:
                    self.color_detection_counters[color_name] += 1
                else:
                    self.color_detection_counters[color_name] = max(0, self.color_detection_counters[color_name] - 1)

                # Publish the color count if detected in the last 10 frames
                if self.color_detection_counters[color_name] >= 10:
                    self.publish_color_count()  # Publish the count of detected colors
                    self.color_detection_counters[color_name] = 0  # Reset the counter after publishing

        # Add info overlay on display frame for enhanced detection
        if DISPLAY_FRAMES and self.display_frame is not None:
            # Draw crop region rectangle
            cv2.rectangle(self.display_frame, (crop_x_offset, crop_y_offset), 
                         (crop_x_offset + hsv_frame.shape[1], crop_y_offset + hsv_frame.shape[0]), 
                         (0, 255, 0), 2)
            
            # Add camera info emphasizing color count
            num_colors = len(detected_colors[self.camera_index])
            info_text = f"Camera {self.camera_index} (Enhanced) | Colors: {num_colors}/9 | Objects: {frame_object_count}"
            cv2.putText(self.display_frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Add detection status
            status_text = "DETECTING" if self.detecting else "PAUSED"
            status_color = (0, 255, 0) if self.detecting else (0, 0, 255)
            cv2.putText(self.display_frame, status_text, (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)

        if detected_colors:
            print(f"Camera {self.camera_index} Enhanced Detected colors: {detected_colors[self.camera_index]}, Total objects: {frame_object_count}")
    def publish_color_count(self):
        # Send the number of unique colors detected from the 9 defined colors
        num_colors = len(detected_colors[self.camera_index])
        score = num_colors * 10  # Multiply by 10 for scoring system
        try:
            # Publish the number of detected unique colors with QoS level 1
            self.mqtt_client.publish(f"FalconGrasp/camera/{self.camera_index}", score)
            print(f"Camera {self.camera_index} - Published score: {score} (based on {num_colors} unique colors)")
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
    
    def set_playback_speed(self, speed_multiplier):
        """Set playback speed for video files (1.0 = normal, 0.5 = half speed, 2.0 = double speed)"""
        if self.is_video_file:
            self.playback_speed_multiplier = speed_multiplier
            print(f"Camera {self.camera_index} - Playback speed set to {speed_multiplier}x")
        else:
            print(f"Camera {self.camera_index} - Speed control only available for video files, not RTSP streams")


class VideoCaptureManager:
    def __init__(self, rtsp_urls, crop_coords_list, mqtt_client):
        self.camera_threads = []
        for i, url in enumerate(rtsp_urls):
            thread = CameraThread(url, i, crop_coords_list[i], mqtt_client)  # Pass the MQTT client
            self.camera_threads.append(thread)
        self.display_active = False

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

    def start_display(self):
        """Start the display windows for all cameras"""
        if DISPLAY_FRAMES:
            self.display_active = True
            for i, thread in enumerate(self.camera_threads):
                window_name = f"Camera {i} - Color Detection"
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(window_name, 960, 540)  # Resize to half of 1920x1080
            print("Display windows created. Press 'q' in any window to quit display, 'ESC' to close all.")

    def update_display(self):
        """Update all camera display windows"""
        if not self.display_active or not DISPLAY_FRAMES:
            return
        
        for i, thread in enumerate(self.camera_threads):
            if thread.display_frame is not None:
                window_name = f"Camera {i} - Color Detection"
                cv2.imshow(window_name, thread.display_frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # 'q' or ESC key
            self.stop_display()
            return False
        return True

    def stop_display(self):
        """Stop and close all display windows"""
        if self.display_active:
            cv2.destroyAllWindows()
            self.display_active = False
            print("Display windows closed.")
    
    def set_all_playback_speed(self, speed_multiplier):
        """Set playback speed for all video file cameras"""
        for thread in self.camera_threads:
            thread.set_playback_speed(speed_multiplier)


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
    # rtsp_urls = [
    #     "rtsp://admin:infinity-2060@192.168.0.18:554",
    #     "rtsp://admin:infinity-2060@192.168.0.19:554",
    #     "rtsp://admin:infinity-2060@192.168.0.20:554",
    #     "rtsp://admin:infinity-2060@192.168.0.21:554",
    #     "rtsp://admin:infinity-2060@192.168.0.22:554"
    # ]

    # # Define the cropping coordinates for each camera (x_start, y_start, x_end, y_end)
    # crop_coords_list = [
    #     (450, 370, 820, 900),  # Camera 1
    #     (450, 370, 840, 900),  # Camera 2
    #     (450, 370, 830, 900),  # Camera 3
    #     (460, 350, 840, 700),  # Camera 4
    #     (450, 350, 830, 720)   # Camera 5
    # ]
    rtsp_urls = ["/home/mostafa/UXE/games_UXE_2025/game2/recordings/hsvdetect_recording_20250918_163814.mp4"]
    crop_coords_list = [(0,0,1920,1080)]

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
    
    # Start display if enabled
    if DISPLAY_FRAMES:
        manager.start_display()

    try:
        while True:
            if DISPLAY_FRAMES:
                # Update display and check for quit signal
                if not manager.update_display():
                    break
            time.sleep(0.033)  # ~30 FPS display update rate
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        if DISPLAY_FRAMES:
            manager.stop_display()
        manager.stop_all()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()