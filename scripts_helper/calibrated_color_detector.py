import sys
import cv2
import numpy as np
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QSlider, QVBoxLayout, 
                             QHBoxLayout, QWidget, QPushButton, QGroupBox, QGridLayout, 
                             QSizePolicy, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QFont

class CalibratedColorDetector(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Calibrated Color Detector - Hybrid HSV+LAB')
        self.setGeometry(100, 100, 1600, 1000)
        self.setMinimumSize(1400, 900)

        # Create a central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create main layout
        self.main_layout = QHBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Create left panel for video displays
        self.create_video_panel()
        
        # Create right panel for controls
        self.create_control_panel()

        # Initialize the video capture
        # self.video_source = "/home/mostafa/UXE/games_UXE_2025/game2/recordings/hsvdetect_recording_20250918_163814.mp4"
        self.video_source = "/home/mostafa/UXE/games_UXE_2025/game2/recordings/hsvdetect_recording_20250918_163536.mp4"
        # self.video_source = "/home/mostafa/UXE/games_UXE_2025/game2/recordings/hsvdetect_recording_20250918_163427.mp4"
        # self.video_source = "rtsp://admin:infinity-2060@192.168.1.64:554"  # RTSP option
        # self.video_source = 0  # Webcam option
        
        self.cap = cv2.VideoCapture(self.video_source)

        # Check if the video capture is opened successfully
        if not self.cap.isOpened():
            print("Error: Could not open video source.")
            exit()

        # Initialize variables
        self.is_recording = False
        self.video_writer = None
        self.recording_filename = None
        self.frame_width = None
        self.frame_height = None
        self.is_paused = False
        self.paused_frame = None
        # hsv values


        # # Load calibrated color ranges from your exact data - CORRECTED VALUES
        self.calibrated_colors = {
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
            
            
            
        }
        
        # Color visualization mapping
        self.color_bgr_map = {
            'pink': (203, 192, 255), 'purple': (128, 0, 128), 'light_green': (144, 238, 144),
            'blue': (255, 0, 0), 'yellow': (0, 255, 255), 'red': (0, 0, 255),
            'dark_green': (0, 100, 0), 'cyan': (255, 255, 0)
        }
        
        self.detected_objects = {}
        self.total_objects = 0
        
        # Try to load updated calibrated ranges from file
        self.load_calibrated_ranges_from_file()

        # Start timer for video processing
        self.timer = self.startTimer(40)  # 25 FPS

    def create_video_panel(self):
        """Create the left panel with video displays"""
        self.video_panel = QWidget()
        self.video_layout = QVBoxLayout()
        self.video_panel.setLayout(self.video_layout)
        
        # Create group box for video displays
        self.video_group = QGroupBox("Video Feeds")
        self.video_group_layout = QVBoxLayout()
        self.video_group.setLayout(self.video_group_layout)
        
        # Original video display
        self.original_title = QLabel("Original Video")
        self.original_title.setAlignment(Qt.AlignCenter)
        self.original_title.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.original_label = QLabel()
        self.original_label.setMinimumSize(400, 300)
        self.original_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.original_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setText("Original Video")
        self.original_label.setScaledContents(False)
        
        # Detection mask display
        self.mask_title = QLabel("Detection Mask")
        self.mask_title.setAlignment(Qt.AlignCenter)
        self.mask_title.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.mask_label = QLabel()
        self.mask_label.setMinimumSize(400, 300)
        self.mask_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mask_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        self.mask_label.setAlignment(Qt.AlignCenter)
        self.mask_label.setText("Detection Mask")
        self.mask_label.setScaledContents(False)
        
        # Detection result display
        self.result_title = QLabel("Color Detection Result")
        self.result_title.setAlignment(Qt.AlignCenter)
        self.result_title.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.result_label = QLabel()
        self.result_label.setMinimumSize(400, 300)
        self.result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setText("Color Detection Result")
        self.result_label.setScaledContents(False)
        
        # Add video displays to group
        self.video_group_layout.addWidget(self.original_title)
        self.video_group_layout.addWidget(self.original_label)
        self.video_group_layout.addWidget(self.mask_title)
        self.video_group_layout.addWidget(self.mask_label)
        self.video_group_layout.addWidget(self.result_title)
        self.video_group_layout.addWidget(self.result_label)
        
        self.video_layout.addWidget(self.video_group)
        self.main_layout.addWidget(self.video_panel, 2)  # Takes 2/3 of horizontal space

    def create_control_panel(self):
        """Create the right panel with controls"""
        self.control_panel = QWidget()
        self.control_layout = QVBoxLayout()
        self.control_panel.setLayout(self.control_layout)
        
        # Detection method controls
        self.create_detection_method_controls()
        
        # Area filtering controls
        self.create_area_controls()
        
        # Detection results display
        self.create_detection_results()
        
        # Video controls
        self.create_video_controls()
        
        # File management
        self.create_file_controls()
        
        # Add stretch to push everything to top
        self.control_layout.addStretch()
        
        # Logo section
        self.create_logo_section()
        
        self.main_layout.addWidget(self.control_panel, 1)  # Takes 1/3 of horizontal space

    def create_detection_method_controls(self):
        """Create detection method selection controls"""
        self.method_group = QGroupBox("Detection Method")
        self.method_layout = QVBoxLayout()
        self.method_group.setLayout(self.method_layout)
        
        # Detection method selection
        self.detection_method_group = QButtonGroup()
        
        self.lab_only_radio = QRadioButton("LAB Only")
        self.hsv_only_radio = QRadioButton("HSV Only")
        self.hybrid_radio = QRadioButton("Hybrid HSV+LAB (Recommended)")
        
        self.hybrid_radio.setChecked(True)  # Default to hybrid
        
        self.detection_method_group.addButton(self.lab_only_radio, 0)
        self.detection_method_group.addButton(self.hsv_only_radio, 1)
        self.detection_method_group.addButton(self.hybrid_radio, 2)
        
        self.method_layout.addWidget(self.lab_only_radio)
        self.method_layout.addWidget(self.hsv_only_radio)
        self.method_layout.addWidget(self.hybrid_radio)
        
        # Connect to method change
        self.detection_method_group.buttonClicked.connect(self.on_detection_method_changed)
        
        self.control_layout.addWidget(self.method_group)

    def create_area_controls(self):
        """Create area filtering controls"""
        self.area_group = QGroupBox("Area Filtering")
        self.area_layout = QGridLayout()
        self.area_group.setLayout(self.area_layout)
        
        # Minimum area slider
        self.area_min_label = QLabel("Min Area:")
        self.area_min_slider = QSlider(Qt.Horizontal)
        self.area_min_slider.setMinimum(1000)
        self.area_min_slider.setMaximum(5000)
        self.area_min_slider.setValue(1000)
        self.area_min_value_label = QLabel("1000")
        self.area_min_slider.valueChanged.connect(lambda v: self.area_min_value_label.setText(str(v)))
        
        # Maximum area slider
        self.area_max_label = QLabel("Max Area:")
        self.area_max_slider = QSlider(Qt.Horizontal)
        self.area_max_slider.setMinimum(5000)
        self.area_max_slider.setMaximum(100000)
        self.area_max_slider.setValue(50000)
        self.area_max_value_label = QLabel("50000")
        self.area_max_slider.valueChanged.connect(lambda v: self.area_max_value_label.setText(str(v)))
        
        # Add to layout
        self.area_layout.addWidget(self.area_min_label, 0, 0)
        self.area_layout.addWidget(self.area_min_slider, 0, 1)
        self.area_layout.addWidget(self.area_min_value_label, 0, 2)
        
        self.area_layout.addWidget(self.area_max_label, 1, 0)
        self.area_layout.addWidget(self.area_max_slider, 1, 1)
        self.area_layout.addWidget(self.area_max_value_label, 1, 2)
        
        # Apply area limits button
        self.apply_area_button = QPushButton("Apply Area Limits")
        self.apply_area_button.clicked.connect(self.apply_area_limits)
        self.apply_area_button.setStyleSheet("""
            QPushButton { 
                padding: 8px; 
                font-weight: bold; 
                background-color: #16a085; 
                color: white; 
                border: none; 
                border-radius: 4px; 
            }
            QPushButton:hover { background-color: #138d75; }
        """)
        self.area_layout.addWidget(self.apply_area_button, 2, 0, 1, 3)
        
        self.control_layout.addWidget(self.area_group)

    def create_detection_results(self):
        """Create detection results display"""
        self.results_group = QGroupBox("Detection Results")
        self.results_layout = QVBoxLayout()
        self.results_group.setLayout(self.results_layout)
        
        # Total count display
        self.total_count_label = QLabel("Total Objects: 0")
        self.total_count_label.setStyleSheet("""
            QLabel { 
                padding: 10px; 
                font-weight: bold; 
                font-size: 16px;
                border: 2px solid #3498db; 
                border-radius: 8px; 
                background-color: #ebf3fd; 
                color: #2980b9;
            }
        """)
        
        # Individual color counts
        self.color_counts_label = QLabel("Color Breakdown:\nNo objects detected")
        self.color_counts_label.setStyleSheet("""
            QLabel { 
                padding: 10px; 
                font-family: monospace; 
                font-size: 12px;
                background-color: #f8f9fa; 
                border: 1px solid #dee2e6; 
                border-radius: 6px; 
                min-height: 150px;
            }
        """)
        self.color_counts_label.setWordWrap(True)
        
        self.results_layout.addWidget(self.total_count_label)
        self.results_layout.addWidget(self.color_counts_label)
        
        self.control_layout.addWidget(self.results_group)

    def create_video_controls(self):
        """Create video control buttons"""
        self.video_controls_group = QGroupBox("Video Controls")
        self.video_controls_layout = QVBoxLayout()
        self.video_controls_group.setLayout(self.video_controls_layout)
        
        # Pause/Resume button
        self.pause_button = QPushButton("⏸️ Pause")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setStyleSheet("""
            QPushButton { 
                padding: 12px; 
                font-weight: bold; 
                font-size: 14px;
                background-color: #f39c12; 
                color: white; 
                border: none; 
                border-radius: 6px; 
            }
            QPushButton:hover { background-color: #e67e22; }
        """)
        
        # Recording button
        self.record_button = QPushButton("🔴 Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet("""
            QPushButton { 
                padding: 12px; 
                font-weight: bold; 
                font-size: 14px;
                background-color: #e74c3c; 
                color: white; 
                border: none; 
                border-radius: 6px; 
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        
        self.video_controls_layout.addWidget(self.pause_button)
        self.video_controls_layout.addWidget(self.record_button)
        
        self.control_layout.addWidget(self.video_controls_group)

    def create_file_controls(self):
        """Create file management controls"""
        self.file_group = QGroupBox("File Management")
        self.file_layout = QVBoxLayout()
        self.file_group.setLayout(self.file_layout)
        
        # Load calibrated ranges button
        self.load_button = QPushButton("📂 Load Calibrated Ranges")
        self.load_button.clicked.connect(self.load_calibrated_ranges_from_file)
        self.load_button.setStyleSheet("""
            QPushButton { 
                padding: 10px; 
                font-weight: bold; 
                background-color: #27ae60; 
                color: white; 
                border: none; 
                border-radius: 6px; 
            }
            QPushButton:hover { background-color: #229954; }
        """)
        
        # Save detection results button
        self.save_button = QPushButton("💾 Save Detection Results")
        self.save_button.clicked.connect(self.save_detection_results)
        self.save_button.setStyleSheet("""
            QPushButton { 
                padding: 10px; 
                font-weight: bold; 
                background-color: #8e44ad; 
                color: white; 
                border: none; 
                border-radius: 6px; 
            }
            QPushButton:hover { background-color: #7d3c98; }
        """)
        
        self.file_layout.addWidget(self.load_button)
        self.file_layout.addWidget(self.save_button)
        
        self.control_layout.addWidget(self.file_group)

    def create_logo_section(self):
        """Create logo display at bottom"""
        self.logo_group = QGroupBox("")
        self.logo_group.setMaximumHeight(200)
        self.logo_layout = QVBoxLayout()
        self.logo_group.setLayout(self.logo_layout)
        
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setMaximumHeight(200)
        self.logo_label.setScaledContents(True)
        
        # Try to load logo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "Infinity_logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_label.setPixmap(scaled_pixmap)
            else:
                self.logo_label.setText("Calibrated Color Detector\nv1.0")
        else:
            self.logo_label.setText("Calibrated Color Detector\nv1.0")
        
        self.logo_layout.addWidget(self.logo_label)
        self.control_layout.addWidget(self.logo_group)

    def on_detection_method_changed(self):
        """Handle detection method change"""
        method_id = self.detection_method_group.checkedId()
        methods = ["LAB Only", "HSV Only", "Hybrid HSV+LAB"]
        print(f"Detection method changed to: {methods[method_id]}")

    def timerEvent(self, event):
        """Main video processing loop"""
        if self.is_paused:
            return
            
        # Capture frame
        ret, frame = self.cap.read()

        
        if not ret:
            # Try to loop video if it's a file
            if isinstance(self.video_source, str) and os.path.isfile(self.video_source):
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                return
            else:
                print("Error: Could not read frame")
                return
        # Apply bilateral filter for noise reduction while preserving edges
        if ret:
            frame = cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)
        
        # Store current frame for paused processing
        self.paused_frame = frame.copy()
        
        # Perform color detection
        mask, result, detections = self.detect_colors(frame)
        
        # Update detection results
        self.update_detection_display(detections)
        
        # Record frame if recording
        if self.is_recording and self.video_writer is not None:
            self.video_writer.write(frame)
        
        # Display images
        self.display_image(self.original_label, frame)
        self.display_image(self.mask_label, mask)
        self.display_image(self.result_label, result)

    def detect_colors(self, frame):
        """Main color detection function using calibrated ranges"""
        method_id = self.detection_method_group.checkedId()
        
        # Convert to both color spaces
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lab_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        
        combined_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        result_frame = frame.copy()
        detections = {}
        
        for color_name, ranges in self.calibrated_colors.items():
            color_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            
            if method_id == 0:  # LAB only
                lab_lower = np.array(ranges['lab'][0])
                lab_upper = np.array(ranges['lab'][1])
                color_mask = cv2.inRange(lab_frame, lab_lower, lab_upper)
                
            elif method_id == 1:  # HSV only
                hsv_lower = np.array(ranges['hsv'][0])
                hsv_upper = np.array(ranges['hsv'][1])
                color_mask = cv2.inRange(hsv_frame, hsv_lower, hsv_upper)
                
            elif method_id == 2:  # Hybrid HSV+LAB
                # Create masks from both color spaces
                lab_lower = np.array(ranges['lab'][0])
                lab_upper = np.array(ranges['lab'][1])
                hsv_lower = np.array(ranges['hsv'][0])
                hsv_upper = np.array(ranges['hsv'][1])
                
                lab_mask = cv2.inRange(lab_frame, lab_lower, lab_upper)
                hsv_mask = cv2.inRange(hsv_frame, hsv_lower, hsv_upper)
                
                # Combine masks (intersection for precision)
                color_mask = cv2.bitwise_and(lab_mask, hsv_mask)
            
            # Clean up the mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            # color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)
            color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)
            
            # Find and count objects
            contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            object_count = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Get area limits for this color (with fallback to global limits)
                color_info = self.calibrated_colors.get(color_name, {})
                area_min = color_info.get('area_min', self.area_min_slider.value())
                area_max = color_info.get('area_max', self.area_max_slider.value())
                
                # Apply area filtering
                if area_min <= area <= area_max:
                    # Calculate additional shape metrics
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
                    
                    # Filter by aspect ratio for more realistic objects
                    if aspect_ratio < 10:  # Avoid very thin/long objects
                        object_count += 1
                        
                        # Draw detection on result frame
                        color_bgr = self.color_bgr_map.get(color_name, (255, 255, 255))
                        
                        cv2.rectangle(result_frame, (x, y), (x + w, y + h), color_bgr, 2)
                        cv2.putText(result_frame, f"{color_name.replace('_', ' ').title()}", 
                                   (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_bgr, 2)
                        
                        # Add area and aspect ratio info
                        cv2.putText(result_frame, f"A:{int(area)} R:{aspect_ratio:.1f}", 
                                   (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color_bgr, 1)
            
            detections[color_name] = object_count
            combined_mask = cv2.bitwise_or(combined_mask, color_mask)
        
        return combined_mask, result_frame, detections

    def update_detection_display(self, detections):
        """Update the detection results display"""
        total = sum(detections.values())
        self.total_objects = total
        self.detected_objects = detections
        
        # Update total count
        self.total_count_label.setText(f"Total Objects: {total}")
        
        # Update color breakdown
        if total > 0:
            breakdown_text = "Color Breakdown:\n"
            for color, count in detections.items():
                if count > 0:
                    color_display = color.replace('_', ' ').title()
                    breakdown_text += f"{color_display}: {count}\n"
        else:
            breakdown_text = "Color Breakdown:\nNo objects detected"
        
        self.color_counts_label.setText(breakdown_text.strip())

    def display_image(self, label, image):
        """Display image in QLabel with proper scaling"""
        if image is None:
            return
            
        label_width = label.width()
        label_height = label.height()
        
        if label_width <= 1 or label_height <= 1:
            return
            
        # Handle grayscale images
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Calculate scaling
        image_height, image_width = image.shape[:2]
        scale_x = label_width / image_width
        scale_y = label_height / image_height
        scale = min(scale_x, scale_y)
        
        new_width = int(image_width * scale)
        new_height = int(image_height * scale)
        
        # Resize image
        resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Create QImage and QPixmap
        height, width, channel = resized_image.shape
        bytes_per_line = 3 * width
        q_image = QImage(resized_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(label_width, label_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        label.setPixmap(scaled_pixmap)

    def toggle_pause(self):
        """Toggle video pause/resume"""
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.pause_button.setText("▶️ Resume")
            self.pause_button.setStyleSheet("""
                QPushButton { 
                    padding: 12px; 
                    font-weight: bold; 
                    font-size: 14px;
                    background-color: #27ae60; 
                    color: white; 
                    border: none; 
                    border-radius: 6px; 
                }
                QPushButton:hover { background-color: #229954; }
            """)
            print("Video paused")
        else:
            self.pause_button.setText("⏸️ Pause")
            self.pause_button.setStyleSheet("""
                QPushButton { 
                    padding: 12px; 
                    font-weight: bold; 
                    font-size: 14px;
                    background-color: #f39c12; 
                    color: white; 
                    border: none; 
                    border-radius: 6px; 
                }
                QPushButton:hover { background-color: #e67e22; }
            """)
            print("Video resumed")

    def toggle_recording(self):
        """Toggle video recording"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start video recording"""
        if not self.is_recording and hasattr(self, 'paused_frame') and self.paused_frame is not None:
            # Get frame dimensions
            self.frame_height, self.frame_width = self.paused_frame.shape[:2]
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.recording_filename = f"color_detection_recording_{timestamp}.mp4"
            
            # Create recordings directory if it doesn't exist
            recordings_dir = "recordings"
            if not os.path.exists(recordings_dir):
                os.makedirs(recordings_dir)
            
            full_path = os.path.join(recordings_dir, self.recording_filename)
            
            # Define codec and create VideoWriter object
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 25.0
            
            self.video_writer = cv2.VideoWriter(full_path, fourcc, fps, (self.frame_width, self.frame_height))
            
            if self.video_writer.isOpened():
                self.is_recording = True
                self.record_button.setText("⏹️ Stop Recording")
                self.record_button.setStyleSheet("""
                    QPushButton { 
                        padding: 12px; 
                        font-weight: bold; 
                        font-size: 14px;
                        background-color: #c0392b; 
                        color: white; 
                        border: none; 
                        border-radius: 6px; 
                    }
                    QPushButton:hover { background-color: #a93226; }
                """)
                print(f"Started recording: {full_path}")
            else:
                print("Error: Could not open video writer.")
                self.video_writer = None

    def stop_recording(self):
        """Stop video recording"""
        if self.is_recording and self.video_writer is not None:
            self.is_recording = False
            self.video_writer.release()
            self.video_writer = None
            
            self.record_button.setText("🔴 Start Recording")
            self.record_button.setStyleSheet("""
                QPushButton { 
                    padding: 12px; 
                    font-weight: bold; 
                    font-size: 14px;
                    background-color: #e74c3c; 
                    color: white; 
                    border: none; 
                    border-radius: 6px; 
                }
                QPushButton:hover { background-color: #c0392b; }
            """)
            
            print(f"Recording saved: {self.recording_filename}")

    def load_calibrated_ranges_from_file(self):
        """Load calibrated color ranges from all_detection_limits.txt"""
        try:
            with open("all_detection_limits.txt", "r") as file:
                content = file.read()
                
            # Parse the file and extract the latest ranges for each color
            sessions = content.split("========================================")
            color_ranges = {}
            
            for session in sessions:
                if "DETECTION SESSION:" in session and "HSV LIMITS:" in session:
                    lines = session.strip().split('\n')
                    
                    # Extract color name (last non-empty line before separator)
                    color_name = None
                    for line in reversed(lines):
                        line = line.strip()
                        if (line and not line.startswith("DETECTION") and 
                            not line.startswith("HSV") and not line.startswith("LAB") and 
                            "Lower:" not in line and "Upper:" not in line and 
                            "No detection" not in line and "Total Sticks" not in line):
                            color_name = line.lower().replace(' ', '_')
                            break
                    
                    if color_name:
                        # Extract HSV and LAB values
                        hsv_values = {}
                        lab_values = {}
                        
                        for line in lines:
                            if "H Lower:" in line:
                                parts = line.split(',')
                                hsv_values['h_lower'] = int(parts[0].split(':')[1].strip())
                                hsv_values['h_upper'] = int(parts[1].split(':')[1].strip())
                            elif "S Lower:" in line:
                                parts = line.split(',')
                                hsv_values['s_lower'] = int(parts[0].split(':')[1].strip())
                                hsv_values['s_upper'] = int(parts[1].split(':')[1].strip())
                            elif "V Lower:" in line:
                                parts = line.split(',')
                                hsv_values['v_lower'] = int(parts[0].split(':')[1].strip())
                                hsv_values['v_upper'] = int(parts[1].split(':')[1].strip())
                            elif "L Lower:" in line:
                                parts = line.split(',')
                                lab_values['l_lower'] = int(parts[0].split(':')[1].strip())
                                lab_values['l_upper'] = int(parts[1].split(':')[1].strip())
                            elif "A Lower:" in line:
                                parts = line.split(',')
                                lab_values['a_lower'] = int(parts[0].split(':')[1].strip())
                                lab_values['a_upper'] = int(parts[1].split(':')[1].strip())
                            elif "B Lower:" in line:
                                parts = line.split(',')
                                lab_values['b_lower'] = int(parts[0].split(':')[1].strip())
                                lab_values['b_upper'] = int(parts[1].split(':')[1].strip())
                        
                        if len(hsv_values) == 6 and len(lab_values) == 6:
                            # Convert LAB A,B values back to 0-255 range for OpenCV
                            lab_a_lower = lab_values['a_lower'] + 127
                            lab_a_upper = lab_values['a_upper'] + 127
                            lab_b_lower = lab_values['b_lower'] + 127
                            lab_b_upper = lab_values['b_upper'] + 127
                            lab_l_lower = int(lab_values['l_lower'] * 2.55)
                            lab_l_upper = int(lab_values['l_upper'] * 2.55)
                            
                            color_ranges[color_name] = {
                                'hsv': ((hsv_values['h_lower'], hsv_values['s_lower'], hsv_values['v_lower']),
                                       (hsv_values['h_upper'], hsv_values['s_upper'], hsv_values['v_upper'])),
                                'lab': ((lab_l_lower, lab_a_lower, lab_b_lower),
                                       (lab_l_upper, lab_a_upper, lab_b_upper)),
                                'area_min': 500,  # Default area limits
                                'area_max': 50000
                            }
            
            if color_ranges:
                self.calibrated_colors = color_ranges
                print(f"✅ Loaded {len(color_ranges)} calibrated color ranges:")
                for color in color_ranges.keys():
                    print(f"  - {color.replace('_', ' ').title()}")
                return True
            else:
                print("❌ No valid color ranges found in file")
                return False
                
        except FileNotFoundError:
            print("❌ all_detection_limits.txt not found - using default ranges")
            return False
        except Exception as e:
            print(f"❌ Error loading calibrated ranges: {e}")
            return False

    def save_detection_results(self):
        """Save current detection results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detection_results_{timestamp}.txt"
        
        method_id = self.detection_method_group.checkedId()
        methods = ["LAB Only", "HSV Only", "Hybrid HSV+LAB"]
        current_method = methods[method_id]
        
        results_text = f"""
========================================
COLOR DETECTION RESULTS
Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Detection Method: {current_method}
========================================

TOTAL OBJECTS DETECTED: {self.total_objects}

COLOR BREAKDOWN:
"""
        
        if self.detected_objects:
            for color, count in self.detected_objects.items():
                if count > 0:
                    color_display = color.replace('_', ' ').title()
                    results_text += f"{color_display}: {count}\n"
        else:
            results_text += "No objects detected\n"
        
        results_text += "\n========================================\n"
        
        try:
            with open(filename, "w") as file:
                file.write(results_text)
            print(f"✅ Detection results saved to: {filename}")
        except Exception as e:
            print(f"❌ Error saving results: {e}")

    def apply_area_limits(self):
        """Apply current area slider values to all colors"""
        min_area = self.area_min_slider.value()
        max_area = self.area_max_slider.value()
        
        for color_name in self.calibrated_colors.keys():
            self.calibrated_colors[color_name]['area_min'] = min_area
            self.calibrated_colors[color_name]['area_max'] = max_area
        
        print(f"✅ Applied area limits: {min_area} - {max_area} to all colors")

    def closeEvent(self, event):
        """Handle application close"""
        if self.is_recording:
            self.stop_recording()
        
        if self.cap:
            self.cap.release()
        
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    detector = CalibratedColorDetector()
    detector.show()
    sys.exit(app.exec_())
