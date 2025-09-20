import sys
import cv2
import numpy as np
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QSlider, QVBoxLayout, 
                             QHBoxLayout, QWidget, QPushButton, QGroupBox, QGridLayout, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QFont

# PINKHSV LIMITS: PINK 
        #    H Lower: 148, H Upper: 165
            # S Lower: 34, S Upper: 133
            # V Lower: 107, V Upper: 255

            # LAB LIMITS:
            # L Lower: 55, L Upper: 100
            # A Lower: 19, A Upper: 59
            # B Lower: -25, B Upper: 6

        # REDHSV LIMITS: RED
        # HSV LIMITS:
        # H Lower: 170, H Upper: 179
        # S Lower: 128, S Upper: 255
        # V Lower: 109, V Upper: 255

        # LAB LIMITS:
        # L Lower: 37, L Upper: 100
        # A Lower: 58, A Upper: 128
        # B Lower: -127, B Upper: 128



        # GREENHSV LIMITS: GREEN
        #     HSV LIMITS:
        #     H Lower: 66, H Upper: 88
        #     S Lower: 114, S Upper: 255
        #     V Lower: 39, V Upper: 255

        #     LAB LIMITS:
        #     L Lower: 39, L Upper: 95
        #     A Lower: -55, A Upper: 18
        #     B Lower: -10, B Upper: 23

        # CYANHSV LIMITS: CYAN
        # HSV LIMITS:
        # H Lower: 90, H Upper: 103
        # S Lower: 104, S Upper: 181
        # V Lower: 246, V Upper: 254

        # LAB LIMITS:
        # L Lower: 30, L Upper: 95
        # A Lower: -99, A Upper: -14
        # B Lower: -31, B Upper: -13


        # DARK GREENHSV LIMITS: DARK GREEN
        # HSV LIMITS:
        # H Lower: 81, H Upper: 90
        # S Lower: 120, S Upper: 205
        # V Lower: 107, V Upper: 255

        # LAB LIMITS:
        # L Lower: 42, L Upper: 92
        # A Lower: -49, A Upper: -27
        # B Lower: -10, B Upper: 2


class ColorDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Hybrid HSV+LAB Color Detection - Counting Unique Colors')
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)

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
        # self.video_source =  "rtsp://admin:infinity-2060@192.168.1.64:554" # Use 0 for the default camera, or replace with your RTSP URL
        # self.video_source = "/home/mostafa/UXE/games_UXE_2025/game2/recordings/hsvdetect_recording_20250918_163814.mp4"
        self.video_source = "/home/mostafa/UXE/games_UXE_2025/game2/recordings/hsvdetect_recording_20250918_163536.mp4"
        # self.video_source = "/home/mostafa/UXE/games_UXE_2025/game2/recordings/hsvdetect_recording_20250918_163427.mp4"
        self.cap = cv2.VideoCapture(self.video_source)

        # Check if the video capture is opened successfully
        if not self.cap.isOpened():
            print("Error: Could not open video source.")
            exit()

        # Initialize video recording variables
        self.video_writer = None
        self.is_recording = False
        self.recording_filename = None
        self.frame_width = None
        self.frame_height = None

        # Update the timer interval to achieve approximately 25 FPS
        self.timer = self.startTimer(40)  # 1000 ms / 25 FPS = 40 ms
        self.is_paused = False
        self.paused_frame = None  # Store the paused frame for live updates
        
        # Stick detection and counting variables - Using calibrated values from your data
        # LAB ranges converted to OpenCV format: L*2.55, A+127, B+127 (to handle 0-255 range)
        # PINKHSV LIMITS: PINK 
        #    H Lower: 148, H Upper: 165
            # S Lower: 34, S Upper: 133
            # V Lower: 107, V Upper: 255

            # LAB LIMITS:
            # L Lower: 55, L Upper: 100
            # A Lower: 19, A Upper: 59
            # B Lower: -25, B Upper: 6

        # REDHSV LIMITS: RED
        # HSV LIMITS:
        # H Lower: 170, H Upper: 179
        # S Lower: 128, S Upper: 255
        # V Lower: 109, V Upper: 255

        # LAB LIMITS:
        # L Lower: 37, L Upper: 100
        # A Lower: 58, A Upper: 128
        # B Lower: -127, B Upper: 128



        # GREENHSV LIMITS: GREEN
        #     HSV LIMITS:
        #     H Lower: 66, H Upper: 88
        #     S Lower: 114, S Upper: 255
        #     V Lower: 39, V Upper: 255

        #     LAB LIMITS:
        #     L Lower: 39, L Upper: 95
        #     A Lower: -55, A Upper: 18
        #     B Lower: -10, B Upper: 23

        # CYANHSV LIMITS: CYAN
        # HSV LIMITS:
        # H Lower: 90, H Upper: 103
        # S Lower: 104, S Upper: 181
        # V Lower: 246, V Upper: 254

        # LAB LIMITS:
        # L Lower: 30, L Upper: 95
        # A Lower: -99, A Upper: -14
        # B Lower: -31, B Upper: -13


        # DARK GREENHSV LIMITS: DARK GREEN
        # HSV LIMITS:
        # H Lower: 81, H Upper: 90
        # S Lower: 120, S Upper: 205
        # V Lower: 107, V Upper: 255

        # LAB LIMITS:
        # L Lower: 42, L Upper: 92
        # A Lower: -49, A Upper: -27
        # B Lower: -10, B Upper: 2
        self.stick_colors = {
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
        
        self.detected_sticks = {}  # Store detected stick counts
        self.total_sticks = 0
        
        # Try to load calibrated ranges from file on startup
        self.load_calibrated_ranges_from_file()

        # Connect slider value changes to the update method
        self.l_lower_slider.valueChanged.connect(self.update_sliders)
        self.l_upper_slider.valueChanged.connect(self.update_sliders)
        self.a_lower_slider.valueChanged.connect(self.update_sliders)
        self.a_upper_slider.valueChanged.connect(self.update_sliders)
        self.b_lower_slider.valueChanged.connect(self.update_sliders)
        self.b_upper_slider.valueChanged.connect(self.update_sliders)
        
        # Connect sliders to live update when paused
        self.l_lower_slider.valueChanged.connect(self.update_paused_view)
        self.l_upper_slider.valueChanged.connect(self.update_paused_view)
        self.a_lower_slider.valueChanged.connect(self.update_paused_view)
        self.a_upper_slider.valueChanged.connect(self.update_paused_view)
        self.b_lower_slider.valueChanged.connect(self.update_paused_view)
        self.b_upper_slider.valueChanged.connect(self.update_paused_view)

    def create_video_panel(self):
        """Create the left panel with video displays"""
        self.video_panel = QWidget()
        self.video_layout = QVBoxLayout()
        self.video_panel.setLayout(self.video_layout)
        
        # Create group box for video displays
        self.video_group = QGroupBox("Video Feeds")
        self.video_group_layout = QVBoxLayout()
        self.video_group.setLayout(self.video_group_layout)
        
        # Create labels for images with titles
        self.original_title = QLabel("Original Video")
        self.original_title.setAlignment(Qt.AlignCenter)
        self.original_title.setFont(QFont("Arial", 10, QFont.Bold))
        
        self.original_label = QLabel()
        self.original_label.setMinimumSize(300, 200)
        self.original_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.original_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setText("Original Video")
        self.original_label.setScaledContents(False)  # Let Qt handle scaling
        
        self.mask_title = QLabel("Detection Mask")
        self.mask_title.setAlignment(Qt.AlignCenter)
        self.mask_title.setFont(QFont("Arial", 10, QFont.Bold))
        
        self.mask_label = QLabel()
        self.mask_label.setMinimumSize(300, 200)
        self.mask_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mask_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        self.mask_label.setAlignment(Qt.AlignCenter)
        self.mask_label.setText("Detection Mask")
        self.mask_label.setScaledContents(False)  # Let Qt handle scaling
        
        self.result_title = QLabel("Stick Detection Result")
        self.result_title.setAlignment(Qt.AlignCenter)
        self.result_title.setFont(QFont("Arial", 10, QFont.Bold))
        
        self.result_label = QLabel()
        self.result_label.setMinimumSize(300, 200)
        self.result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setText("Stick Detection Result")
        self.result_label.setScaledContents(False)  # Let Qt handle scaling
        
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
        
        # Detection Method Controls
        self.create_detection_controls()
        
        # LAB Controls Group
        self.create_lab_controls()
        
        # HSV Controls Group (for hybrid mode)
        self.create_hsv_controls()
        
        # Recording Controls Group
        self.create_recording_controls()
        
        # Detection Results Display
        self.create_detection_results()
        
        # LAB Values Display Group
        self.create_lab_display()
        
        # Add stretch to push everything to top
        self.control_layout.addStretch()
        
        # Logo Group - anchored at bottom
        self.create_logo_display()
        
        self.main_layout.addWidget(self.control_panel, 1)  # Takes 1/3 of horizontal space

    def create_detection_controls(self):
        """Create detection method selection controls"""
        self.detection_group = QGroupBox("Detection Method")
        self.detection_layout = QVBoxLayout()
        self.detection_group.setLayout(self.detection_layout)
        
        # Detection method selection
        from PyQt5.QtWidgets import QRadioButton, QButtonGroup
        self.detection_method_group = QButtonGroup()
        
        self.lab_only_radio = QRadioButton("LAB Only")
        self.hsv_only_radio = QRadioButton("HSV Only")
        self.hybrid_radio = QRadioButton("Hybrid HSV+LAB")
        
        self.hybrid_radio.setChecked(True)  # Default to hybrid
        
        self.detection_method_group.addButton(self.lab_only_radio, 0)
        self.detection_method_group.addButton(self.hsv_only_radio, 1)
        self.detection_method_group.addButton(self.hybrid_radio, 2)
        
        self.detection_layout.addWidget(self.lab_only_radio)
        self.detection_layout.addWidget(self.hsv_only_radio)
        self.detection_layout.addWidget(self.hybrid_radio)
        
        # Connect to method change
        self.detection_method_group.buttonClicked.connect(self.on_detection_method_changed)
        
        self.control_layout.addWidget(self.detection_group)

    def create_hsv_controls(self):
        """Create HSV slider controls for hybrid mode"""
        self.hsv_group = QGroupBox("HSV Controls (Hybrid Mode)")
        self.hsv_layout = QGridLayout()
        self.hsv_group.setLayout(self.hsv_layout)
        
        # Create HSV sliders
        self.h_lower_slider = self.create_labeled_slider("H Lower:", 0, 179, 0)
        self.h_upper_slider = self.create_labeled_slider("H Upper:", 0, 179, 179)
        self.s_lower_slider = self.create_labeled_slider("S Lower:", 0, 255, 50)
        self.s_upper_slider = self.create_labeled_slider("S Upper:", 0, 255, 255)
        self.v_lower_slider = self.create_labeled_slider("V Lower:", 0, 255, 50)
        self.v_upper_slider = self.create_labeled_slider("V Upper:", 0, 255, 255)
        
        # Add sliders to grid layout
        hsv_sliders = [
            ("H Lower:", self.h_lower_slider, 0),
            ("H Upper:", self.h_upper_slider, 1),
            ("S Lower:", self.s_lower_slider, 2),
            ("S Upper:", self.s_upper_slider, 3),
            ("V Lower:", self.v_lower_slider, 4),
            ("V Upper:", self.v_upper_slider, 5)
        ]
        
        for label_text, slider, row in hsv_sliders:
            label = QLabel(label_text)
            value_label = QLabel(str(slider.value()))
            value_label.setMinimumWidth(30)
            slider.value_label = value_label
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(str(v)))
            
            self.hsv_layout.addWidget(label, row, 0)
            self.hsv_layout.addWidget(slider, row, 1)
            self.hsv_layout.addWidget(value_label, row, 2)
        
        # Connect HSV sliders to update functions
        for slider in [self.h_lower_slider, self.h_upper_slider, self.s_lower_slider, 
                      self.s_upper_slider, self.v_lower_slider, self.v_upper_slider]:
            slider.valueChanged.connect(self.update_paused_view)
        
        # Save button for HSV only
        self.save_hsv_button = QPushButton("Save HSV Limits")
        self.save_hsv_button.clicked.connect(self.save_hsv_limits)
        self.save_hsv_button.setStyleSheet("QPushButton { padding: 8px; font-weight: bold; background-color: #e74c3c; color: white; border-radius: 4px; }")
        self.hsv_layout.addWidget(self.save_hsv_button, 6, 0, 1, 3)
        
        self.control_layout.addWidget(self.hsv_group)

    def create_detection_results(self):
        """Create detection results display"""
        self.results_group = QGroupBox("Stick Detection Results")
        self.results_layout = QVBoxLayout()
        self.results_group.setLayout(self.results_layout)
        
        # Total count display - emphasize color count
        self.total_count_label = QLabel("Unique Colors: 0 | Total Sticks: 0")
        self.total_count_label.setStyleSheet("""
            QLabel { 
                padding: 8px; 
                font-weight: bold; 
                font-size: 14px;
                border: 2px solid #2ecc71; 
                border-radius: 5px; 
                background-color: #e8f8f5; 
                color: #27ae60;
            }
        """)
        
        # Individual color counts
        self.color_counts_label = QLabel("Color Breakdown:\nNo colors detected")
        self.color_counts_label.setStyleSheet("""
            QLabel { 
                padding: 8px; 
                font-family: monospace; 
                background-color: #f8f9fa; 
                border: 1px solid #dee2e6; 
                border-radius: 5px; 
            }
        """)
        self.color_counts_label.setWordWrap(True)
        
        self.results_layout.addWidget(self.total_count_label)
        self.results_layout.addWidget(self.color_counts_label)
        
        # Save All Limits Button
        self.save_all_button = QPushButton("💾 Save All Limits (HSV + LAB)")
        self.save_all_button.clicked.connect(self.save_all_limits)
        self.save_all_button.setStyleSheet("""
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
            QPushButton:pressed { background-color: #1e8449; }
        """)
        self.results_layout.addWidget(self.save_all_button)
        
        # Load Calibrated Ranges Button
        self.load_ranges_button = QPushButton("📂 Load Calibrated Ranges")
        self.load_ranges_button.clicked.connect(self.load_calibrated_ranges_from_file)
        self.load_ranges_button.setStyleSheet("""
            QPushButton { 
                padding: 10px; 
                font-weight: bold; 
                background-color: #f39c12; 
                color: white; 
                border: none; 
                border-radius: 6px; 
            }
            QPushButton:hover { background-color: #e67e22; }
            QPushButton:pressed { background-color: #d35400; }
        """)
        self.results_layout.addWidget(self.load_ranges_button)
        
        self.control_layout.addWidget(self.results_group)

    def on_detection_method_changed(self):
        """Handle detection method change"""
        method_id = self.detection_method_group.checkedId()
        if method_id == 0:
            print("Switched to LAB only detection")
        elif method_id == 1:
            print("Switched to HSV only detection")
        elif method_id == 2:
            print("Switched to Hybrid HSV+LAB detection")
        
        # Update the paused view if currently paused
        self.update_paused_view()

    def create_lab_controls(self):
        """Create LAB slider controls"""
        self.lab_group = QGroupBox("LAB Range Controls")
        self.lab_layout = QGridLayout()
        self.lab_group.setLayout(self.lab_layout)
        
        # Create sliders with labels for LAB color space:
        # L: 0-100 (Lightness) - slider shows actual L values
        # A: -127 to +128 (Green-Red) - slider shows 0-255, converted to actual range for display/saving
        # B: -127 to +128 (Blue-Yellow) - slider shows 0-255, converted to actual range for display/saving
        self.l_lower_slider = self.create_labeled_slider("L Lower:", 0, 100, 0)
        self.l_upper_slider = self.create_labeled_slider("L Upper:", 0, 100, 100)
        self.a_lower_slider = self.create_labeled_slider("A Lower:", 0, 255, 127)  # Default to 127 (0 in actual LAB)
        self.a_upper_slider = self.create_labeled_slider("A Upper:", 0, 255, 255)
        self.b_lower_slider = self.create_labeled_slider("B Lower:", 0, 255, 127)  # Default to 127 (0 in actual LAB)
        self.b_upper_slider = self.create_labeled_slider("B Upper:", 0, 255, 255)
        
        # Add sliders to grid layout
        sliders = [
            ("L Lower:", self.l_lower_slider, 0),
            ("L Upper:", self.l_upper_slider, 1),
            ("A Lower:", self.a_lower_slider, 2),
            ("A Upper:", self.a_upper_slider, 3),
            ("B Lower:", self.b_lower_slider, 4),
            ("B Upper:", self.b_upper_slider, 5)
        ]
        
        for label_text, slider, row in sliders:
            label = QLabel(label_text)
            value_label = QLabel(str(slider.value()))
            value_label.setMinimumWidth(30)
            slider.value_label = value_label  # Store reference for updates
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(str(v)))
            
            self.lab_layout.addWidget(label, row, 0)
            self.lab_layout.addWidget(slider, row, 1)
            self.lab_layout.addWidget(value_label, row, 2)
        
        # Save button for LAB only
        self.save_lab_button = QPushButton("Save LAB Limits")
        self.save_lab_button.clicked.connect(self.save_lab_limits)
        self.save_lab_button.setStyleSheet("QPushButton { padding: 8px; font-weight: bold; background-color: #3498db; color: white; border-radius: 4px; }")
        self.lab_layout.addWidget(self.save_lab_button, 6, 0, 1, 3)
        
        self.control_layout.addWidget(self.lab_group)

    def create_recording_controls(self):
        """Create recording control buttons"""
        self.recording_group = QGroupBox("Video Recording")
        self.recording_layout = QVBoxLayout()
        self.recording_group.setLayout(self.recording_layout)
        
        # Recording buttons
        self.button_layout = QHBoxLayout()
        self.start_recording_button = QPushButton("🔴 Start Recording")
        self.stop_recording_button = QPushButton("⏹️ Stop Recording")
        
        self.start_recording_button.clicked.connect(self.start_recording)
        self.stop_recording_button.clicked.connect(self.stop_recording)
        self.stop_recording_button.setEnabled(False)
        
        # Pause/Resume button
        self.pause_button = QPushButton("⏸️ Pause Stream")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setStyleSheet("""
            QPushButton { 
                padding: 10px; 
                font-weight: bold; 
                background-color: #f39c12; 
                color: white; 
                border: none; 
                border-radius: 5px; 
            }
            QPushButton:hover { background-color: #e67e22; }
        """)
        
        # Style buttons
        self.start_recording_button.setStyleSheet("""
            QPushButton { 
                padding: 10px; 
                font-weight: bold; 
                background-color: #4CAF50; 
                color: white; 
                border: none; 
                border-radius: 5px; 
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        
        self.stop_recording_button.setStyleSheet("""
            QPushButton { 
                padding: 10px; 
                font-weight: bold; 
                background-color: #f44336; 
                color: white; 
                border: none; 
                border-radius: 5px; 
            }
            QPushButton:hover { background-color: #da190b; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        
        self.button_layout.addWidget(self.start_recording_button)
        self.button_layout.addWidget(self.stop_recording_button)
        
        # Add pause button to the layout
        self.recording_layout.addWidget(self.pause_button)
        
        # Recording status
        self.recording_status_label = QLabel("⚫ Not Recording")
        self.recording_status_label.setAlignment(Qt.AlignCenter)
        self.recording_status_label.setStyleSheet("""
            QLabel { 
                padding: 8px; 
                font-weight: bold; 
                border: 2px solid #ddd; 
                border-radius: 5px; 
                background-color: #f9f9f9; 
            }
        """)
        
        self.recording_layout.addLayout(self.button_layout)
        self.recording_layout.addWidget(self.recording_status_label)
        
        self.control_layout.addWidget(self.recording_group)

    def create_lab_display(self):
        """Create LAB values display"""
        self.lab_display_group = QGroupBox("Current LAB Values")
        self.lab_display_layout = QVBoxLayout()
        self.lab_display_group.setLayout(self.lab_display_layout)
        
        self.lab_value_label = QLabel("LAB Ranges:\nL: 0-100 (Lightness)\nA: -127 to +128 (Green-Red)\nB: -127 to +128 (Blue-Yellow)")
        self.lab_value_label.setWordWrap(True)
        self.lab_value_label.setStyleSheet("""
            QLabel { 
                padding: 10px; 
                font-family: monospace; 
                background-color: #f0f0f0; 
                border: 1px solid #ccc; 
                border-radius: 5px; 
            }
        """)
        
        self.lab_display_layout.addWidget(self.lab_value_label)
        self.control_layout.addWidget(self.lab_display_group)

    def create_logo_display(self):
        """Create logo display at bottom right"""
        self.logo_group = QGroupBox("")
        self.logo_group.setMaximumHeight(300)  # Limit height
        self.logo_layout = QVBoxLayout()
        self.logo_group.setLayout(self.logo_layout)
        
        # Create logo label
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setMaximumHeight(300)
        self.logo_label.setScaledContents(True)
        
        # Load and set the logo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "Infinity_logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                # Scale the logo to fit within the label while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_label.setPixmap(scaled_pixmap)
            else:
                self.logo_label.setText("Logo not found")
        else:
            self.logo_label.setText("Logo file not found")
        
        self.logo_layout.addWidget(self.logo_label)
        self.control_layout.addWidget(self.logo_group)

    def create_labeled_slider(self, label_text, min_val, max_val, initial_val):
        """Create a slider with proper range and initial value"""
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(initial_val)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval((max_val - min_val) // 10)
        return slider


    def update_sliders(self):
        # Get the current positions of the sliders
        l_lower = self.l_lower_slider.value()
        l_upper = self.l_upper_slider.value()
        a_lower = self.a_lower_slider.value()
        a_upper = self.a_upper_slider.value()
        b_lower = self.b_lower_slider.value()
        b_upper = self.b_upper_slider.value()

        # Ensure that the upper bounds are greater than the lower bounds
        if l_lower > l_upper:
            self.l_upper_slider.setValue(l_lower)  # Adjust upper slider
        if a_lower > a_upper:
            self.a_upper_slider.setValue(a_lower)  # Adjust upper slider
        if b_lower > b_upper:
            self.b_upper_slider.setValue(b_lower)  # Adjust upper slider

        # Convert A and B values to actual LAB range (-127 to +128)
        a_lower_actual = a_lower - 127
        a_upper_actual = a_upper - 127
        b_lower_actual = b_lower - 127
        b_upper_actual = b_upper - 127

        # Print the current LAB values
        lab_values = f"L Lower: {l_lower}, L Upper: {l_upper},\nA Lower: {a_lower_actual}, A Upper: {a_upper_actual},\nB Lower: {b_lower_actual}, B Upper: {b_upper_actual}"
        print(f"Current LAB Values: {lab_values}")

        # Update the label to show current LAB values on the GUI
        self.lab_value_label.setText(lab_values)  # Set the text of the label

    def update_paused_view(self):
        """Update the paused frame view with current slider values"""
        if not self.is_paused or self.paused_frame is None:
            return
            
        # Process the paused frame with current slider values
        self.process_frame_with_sliders(self.paused_frame)

    def timerEvent(self, event):
        # Skip processing if paused
        if self.is_paused:
            return
            
        # Capture frame-by-frame
        ret, self.image = self.cap.read()
        
        # Apply enhanced filtering pipeline for better detection
        if ret:
            # 1. Gaussian blur for initial noise reduction
            self.image = cv2.GaussianBlur(self.image, (5, 5), 0)
            
            # 2. Bilateral filter for noise reduction while preserving edges
            self.image = cv2.bilateralFilter(self.image, d=9, sigmaColor=75, sigmaSpace=75)
            
            # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization) on LAB L-channel
            lab_temp = cv2.cvtColor(self.image, cv2.COLOR_BGR2LAB)
            l_temp, a_temp, b_temp = cv2.split(lab_temp)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l_temp = clahe.apply(l_temp)
            lab_temp = cv2.merge([l_temp, a_temp, b_temp])
            self.image = cv2.cvtColor(lab_temp, cv2.COLOR_LAB2BGR)
        
        # Store the current frame for paused updates
        if ret:
            self.paused_frame = self.image.copy()
        
        if not ret:
            print("Error: Could not read frame.")
            # Handle the error by displaying a message on the GUI
            self.original_label.setText("Error: Could not read frame.")  # Display error message
            self.mask_label.clear()  # Clear the mask label
            self.result_label.clear()  # Clear the result label
           # Attempt to reopen the video capture
            self.cap.release()  # Release the current capture
            self.cap = cv2.VideoCapture(self.video_source)  # Reinitialize the video capture
            
            # Check if the video capture is opened successfully
            if not self.cap.isOpened():
                print("Error: Could not reopen video source.")
                return  # Exit the method if reopening fails

            return  # Exit the method if frame reading fails
        # Perform hybrid stick detection
        mask, result, stick_counts = self.hybrid_stick_detection(self.image)
        
        # Update stick counting displays
        self.update_stick_counts(stick_counts)

        # Record frame if recording is active
        if self.is_recording and self.video_writer is not None:
            self.video_writer.write(self.image)

        # Convert images to QImage format for display
        self.display_image(self.original_label, self.image)
        self.display_image(self.mask_label, mask)
        self.display_image(self.result_label, result)

    def process_frame_with_sliders(self, frame):
        """Process a specific frame with current slider values"""
        # Apply enhanced filtering pipeline
        # 1. Gaussian blur for initial noise reduction
        frame = cv2.GaussianBlur(frame, (5, 5), 0)
        
        # 2. Bilateral filter for noise reduction while preserving edges
        frame = cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)
        
        # 3. CLAHE on LAB L-channel
        lab_temp = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_temp, a_temp, b_temp = cv2.split(lab_temp)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l_temp = clahe.apply(l_temp)
        lab_temp = cv2.merge([l_temp, a_temp, b_temp])
        frame = cv2.cvtColor(lab_temp, cv2.COLOR_LAB2BGR)
        
        # Perform hybrid stick detection
        mask, result, stick_counts = self.hybrid_stick_detection(frame)
        
        # Update stick counting displays
        self.update_stick_counts(stick_counts)

        # Display the updated images
        self.display_image(self.original_label, frame)
        self.display_image(self.mask_label, mask)
        self.display_image(self.result_label, result)

    def hybrid_stick_detection(self, frame):
        """Perform hybrid HSV+LAB stick detection and counting"""
        method_id = self.detection_method_group.checkedId()
        
        # Convert to both color spaces
        hsv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lab_image = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        
        combined_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        result_frame = frame.copy()
        stick_counts = {}
        
        # Color mapping for visualization - Updated for your colors
        color_bgr_map = {
            'pink': (203, 192, 255), 'purple': (128, 0, 128), 'light_green': (144, 238, 144),
            'blue': (255, 0, 0), 'yellow': (0, 255, 255), 'red': (0, 0, 255),
            'dark_green': (0, 100, 0), 'cyan': (255, 255, 0)
        }
        
        for color_name, ranges in self.stick_colors.items():
            color_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            
            if method_id == 0:  # LAB only
                # Use current slider values for LAB only mode
                if hasattr(self, 'l_lower_slider'):
                    l_lower = int(self.l_lower_slider.value() * 2.55)
                    l_upper = int(self.l_upper_slider.value() * 2.55)
                    a_lower = self.a_lower_slider.value()
                    a_upper = self.a_upper_slider.value()
                    b_lower = self.b_lower_slider.value()
                    b_upper = self.b_upper_slider.value()
                    
                    lab_lower = np.array([l_lower, a_lower, b_lower])
                    lab_upper = np.array([l_upper, a_upper, b_upper])
                    color_mask = cv2.inRange(lab_image, lab_lower, lab_upper)
                else:
                    # Fallback to predefined ranges if sliders not available
                    lab_lower = np.array(ranges['lab'][0])
                    lab_upper = np.array(ranges['lab'][1])
                    color_mask = cv2.inRange(lab_image, lab_lower, lab_upper)
                
            elif method_id == 1:  # HSV only
                # Use current slider values for HSV only mode
                if hasattr(self, 'h_lower_slider'):
                    h_lower = self.h_lower_slider.value()
                    h_upper = self.h_upper_slider.value()
                    s_lower = self.s_lower_slider.value()
                    s_upper = self.s_upper_slider.value()
                    v_lower = self.v_lower_slider.value()
                    v_upper = self.v_upper_slider.value()
                    
                    hsv_lower = np.array([h_lower, s_lower, v_lower])
                    hsv_upper = np.array([h_upper, s_upper, v_upper])
                    color_mask = cv2.inRange(hsv_image, hsv_lower, hsv_upper)
                else:
                    # Fallback to predefined ranges if sliders not available
                    hsv_lower = np.array(ranges['hsv'][0])
                    hsv_upper = np.array(ranges['hsv'][1])
                    color_mask = cv2.inRange(hsv_image, hsv_lower, hsv_upper)
                
            elif method_id == 2:  # Hybrid HSV+LAB
                # Get current slider values for fine-tuning
                if hasattr(self, 'l_lower_slider'):
                    l_lower = int(self.l_lower_slider.value() * 2.55)
                    l_upper = int(self.l_upper_slider.value() * 2.55)
                    a_lower = self.a_lower_slider.value()
                    a_upper = self.a_upper_slider.value()
                    b_lower = self.b_lower_slider.value()
                    b_upper = self.b_upper_slider.value()
                    
                    h_lower = self.h_lower_slider.value()
                    h_upper = self.h_upper_slider.value()
                    s_lower = self.s_lower_slider.value()
                    s_upper = self.s_upper_slider.value()
                    v_lower = self.v_lower_slider.value()
                    v_upper = self.v_upper_slider.value()
                    
                    # Create masks from both color spaces
                    lab_mask = cv2.inRange(lab_image, 
                                         np.array([l_lower, a_lower, b_lower]),
                                         np.array([l_upper, a_upper, b_upper]))
                    hsv_mask = cv2.inRange(hsv_image,
                                         np.array([h_lower, s_lower, v_lower]),
                                         np.array([h_upper, s_upper, v_upper]))
                    
                    # Combine masks (intersection for more precise detection)
                    color_mask = cv2.bitwise_and(lab_mask, hsv_mask)
                else:
                    # Fallback to predefined ranges
                    lab_lower = np.array(ranges['lab'][0])
                    lab_upper = np.array(ranges['lab'][1])
                    hsv_lower = np.array(ranges['hsv'][0])
                    hsv_upper = np.array(ranges['hsv'][1])
                    
                    lab_mask = cv2.inRange(lab_image, lab_lower, lab_upper)
                    hsv_mask = cv2.inRange(hsv_image, hsv_lower, hsv_upper)
                    color_mask = cv2.bitwise_and(lab_mask, hsv_mask)
            
            # Apply enhanced morphological operations to clean up the mask
            kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            
            # Remove small noise (like reflections)
            color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel_small, iterations=2)
            # Fill small gaps
            color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel_large, iterations=1)
            # Final cleanup
            color_mask = cv2.medianBlur(color_mask, 3)
            
            # Find and count sticks (contours) for this color
            contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            stick_count = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 500:  # Minimum area for a stick
                    # Calculate aspect ratio to filter stick-like shapes
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = max(w, h) / min(w, h)
                    
                    if aspect_ratio > 2.0:  # Stick-like shape
                        stick_count += 1
                        
                        # Draw bounding box and label on result frame
                        color_bgr = color_bgr_map.get(color_name, (255, 255, 255))
                        cv2.rectangle(result_frame, (x, y), (x + w, y + h), color_bgr, 2)
                        cv2.putText(result_frame, f"{color_name}", (x, y - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_bgr, 2)
            
            stick_counts[color_name] = stick_count
            combined_mask = cv2.bitwise_or(combined_mask, color_mask)
        
        return combined_mask, result_frame, stick_counts

    def update_stick_counts(self, stick_counts):
        """Update the stick counting displays - emphasizing color count"""
        total_objects = sum(stick_counts.values())
        unique_colors = sum(1 for count in stick_counts.values() if count > 0)
        self.total_sticks = total_objects
        self.unique_colors = unique_colors
        
        # Update total count - emphasize colors over objects
        self.total_count_label.setText(f"Unique Colors: {unique_colors} | Total Sticks: {total_objects}")
        
        # Update color breakdown
        if unique_colors > 0:
            breakdown_text = f"Color Breakdown ({unique_colors} colors detected):\n"
            for color, count in stick_counts.items():
                if count > 0:
                    breakdown_text += f"{color.capitalize()}: {count} sticks\n"
        else:
            breakdown_text = "Color Breakdown:\nNo colors detected"
        
        self.color_counts_label.setText(breakdown_text.strip())
        
        # Store current detection results for saving
        self.detected_sticks = stick_counts

    def display_image(self, label, image):
        # Get the label's current size
        label_width = label.width()
        label_height = label.height()
        
        # Skip if label hasn't been sized yet
        if label_width <= 1 or label_height <= 1:
            return
            
        image_height, image_width = image.shape[:2]
        
        # Calculate scaling factors to fit image within label while maintaining aspect ratio
        scale_x = label_width / image_width
        scale_y = label_height / image_height
        scale = min(scale_x, scale_y)  # Use the smaller scale to ensure image fits completely
        
        # Calculate new dimensions
        new_width = int(image_width * scale)
        new_height = int(image_height * scale)
        
        # Resize the image
        resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Convert color space if needed
        if len(resized_image.shape) == 2:  # Grayscale image
            resized_image = cv2.cvtColor(resized_image, cv2.COLOR_GRAY2BGR)
        else:  # Color image
            resized_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        
        # Create QImage
        height, width, channel = resized_image.shape
        bytes_per_line = 3 * width
        q_image = QImage(resized_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        # Create pixmap and scale it to fit the label exactly
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(label_width, label_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        label.setPixmap(scaled_pixmap)

    def save_lab_limits(self):
        # Get the current positions of the sliders
        l_lower = self.l_lower_slider.value()
        l_upper = self.l_upper_slider.value()
        a_lower = self.a_lower_slider.value()
        a_upper = self.a_upper_slider.value()
        b_lower = self.b_lower_slider.value()
        b_upper = self.b_upper_slider.value()

        # Convert A and B values to actual LAB range
        a_lower_actual = a_lower - 127
        a_upper_actual = a_upper - 127
        b_lower_actual = b_lower - 127
        b_upper_actual = b_upper - 127

        # Prepare the data to be saved
        lab_limits = f"L Lower: {l_lower}, L Upper: {l_upper}, A Lower: {a_lower_actual}, A Upper: {a_upper_actual}, B Lower: {b_lower_actual}, B Upper: {b_upper_actual}\n"

        # Save to a file
        with open("lab_limits.txt", "a") as file:  # Append to the file
            file.write(lab_limits)

        print("LAB limits saved to lab_limits.txt")  # Confirmation message

    def save_hsv_limits(self):
        """Save current HSV slider values"""
        # Get the current positions of the sliders
        h_lower = self.h_lower_slider.value()
        h_upper = self.h_upper_slider.value()
        s_lower = self.s_lower_slider.value()
        s_upper = self.s_upper_slider.value()
        v_lower = self.v_lower_slider.value()
        v_upper = self.v_upper_slider.value()

        # Prepare the data to be saved
        hsv_limits = f"H Lower: {h_lower}, H Upper: {h_upper}, S Lower: {s_lower}, S Upper: {s_upper}, V Lower: {v_lower}, V Upper: {v_upper}\n"

        # Save to a file
        with open("hsv_limits.txt", "a") as file:  # Append to the file
            file.write(hsv_limits)

        print("HSV limits saved to hsv_limits.txt")  # Confirmation message

    def save_all_limits(self):
        """Save both HSV and LAB limits with timestamp and detection method"""
        from datetime import datetime
        
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get detection method
        method_id = self.detection_method_group.checkedId()
        method_names = ["LAB Only", "HSV Only", "Hybrid HSV+LAB"]
        current_method = method_names[method_id] if method_id >= 0 else "Unknown"
        
        # Get HSV values
        h_lower = self.h_lower_slider.value()
        h_upper = self.h_upper_slider.value()
        s_lower = self.s_lower_slider.value()
        s_upper = self.s_upper_slider.value()
        v_lower = self.v_lower_slider.value()
        v_upper = self.v_upper_slider.value()
        
        # Get LAB values
        l_lower = self.l_lower_slider.value()
        l_upper = self.l_upper_slider.value()
        a_lower = self.a_lower_slider.value()
        a_upper = self.a_upper_slider.value()
        b_lower = self.b_lower_slider.value()
        b_upper = self.b_upper_slider.value()
        
        # Convert A and B values to actual LAB range
        a_lower_actual = a_lower - 127
        a_upper_actual = a_upper - 127
        b_lower_actual = b_lower - 127
        b_upper_actual = b_upper - 127
        
        # Get current stick counts and unique colors
        total_sticks = self.total_sticks
        unique_colors = getattr(self, 'unique_colors', 0)
        
        # Prepare comprehensive data
        all_limits = f"""
========================================
DETECTION SESSION: {timestamp}
Detection Method: {current_method}
Unique Colors Detected: {unique_colors}
Total Sticks Detected: {total_sticks}
========================================

HSV LIMITS:
H Lower: {h_lower}, H Upper: {h_upper}
S Lower: {s_lower}, S Upper: {s_upper}
V Lower: {v_lower}, V Upper: {v_upper}

LAB LIMITS:
L Lower: {l_lower}, L Upper: {l_upper}
A Lower: {a_lower_actual}, A Upper: {a_upper_actual}
B Lower: {b_lower_actual}, B Upper: {b_upper_actual}

DETECTION RESULTS:
{self.get_current_detection_summary()}

========================================

"""
        
        # Save to combined file
        with open("all_detection_limits.txt", "a") as file:
            file.write(all_limits)
        
        # Also save to individual files for backward compatibility
        hsv_limits = f"H Lower: {h_lower}, H Upper: {h_upper}, S Lower: {s_lower}, S Upper: {s_upper}, V Lower: {v_lower}, V Upper: {v_upper}\n"
        with open("hsv_limits.txt", "a") as file:
            file.write(hsv_limits)
        
        lab_limits = f"L Lower: {l_lower}, L Upper: {l_upper}, A Lower: {a_lower_actual}, A Upper: {a_upper_actual}, B Lower: {b_lower_actual}, B Upper: {b_upper_actual}\n"
        with open("lab_limits.txt", "a") as file:
            file.write(lab_limits)
        
        print(f"All limits saved successfully!")
        print(f"- Combined file: all_detection_limits.txt")
        print(f"- HSV file: hsv_limits.txt")
        print(f"- LAB file: lab_limits.txt")
        print(f"Detection method: {current_method}")
        print(f"Unique colors detected: {unique_colors}")
        print(f"Total sticks detected: {total_sticks}")

    def get_current_detection_summary(self):
        """Get a summary of current detection results"""
        if hasattr(self, 'detected_sticks') and self.detected_sticks:
            summary = []
            for color, count in self.detected_sticks.items():
                if count > 0:
                    summary.append(f"{color.replace('_', ' ').title()}: {count}")
            return "\n".join(summary) if summary else "No sticks detected"
        else:
            return "No detection results available"

    def load_calibrated_ranges_from_file(self):
        """Load calibrated color ranges from the all_detection_limits.txt file"""
        try:
            with open("all_detection_limits.txt", "r") as file:
                content = file.read()
                
            # Parse the file and extract the latest ranges for each color
            sessions = content.split("========================================")
            color_ranges = {}
            
            for session in sessions:
                if "DETECTION SESSION:" in session and "HSV LIMITS:" in session:
                    lines = session.strip().split('\n')
                    
                    # Extract color name (last line before separator)
                    color_name = None
                    for line in reversed(lines):
                        if line.strip() and not line.startswith("DETECTION") and not line.startswith("HSV") and not line.startswith("LAB") and "Lower:" not in line and "Upper:" not in line and "No detection" not in line:
                            color_name = line.strip().lower().replace(' ', '_')
                            break
                    
                    if color_name:
                        # Extract HSV values
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
                                       (lab_l_upper, lab_a_upper, lab_b_upper))
                            }
            
            if color_ranges:
                self.stick_colors = color_ranges
                print(f"Loaded {len(color_ranges)} calibrated color ranges from file:")
                for color in color_ranges.keys():
                    print(f"  - {color.replace('_', ' ').title()}")
                return True
            else:
                print("No valid color ranges found in file")
                return False
                
        except FileNotFoundError:
            print("all_detection_limits.txt not found - using default ranges")
            return False
        except Exception as e:
            print(f"Error loading calibrated ranges: {e}")
            return False

    def start_recording(self):
        """Start video recording"""
        if not self.is_recording:
            # Get frame dimensions
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Could not read frame to get dimensions.")
                return
            
            # Apply bilateral filter for consistency
            frame = cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)
            self.frame_height, self.frame_width = frame.shape[:2]
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.recording_filename = f"labdetect_recording_{timestamp}.mp4"
            
            # Create videos directory if it doesn't exist
            videos_dir = "recordings"
            if not os.path.exists(videos_dir):
                os.makedirs(videos_dir)
            
            full_path = os.path.join(videos_dir, self.recording_filename)
            
            # Define codec and create VideoWriter object
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # You can also try 'XVID'
            fps = 25.0  # Match the timer FPS
            
            self.video_writer = cv2.VideoWriter(full_path, fourcc, fps, (self.frame_width, self.frame_height))
            
            if self.video_writer.isOpened():
                self.is_recording = True
                self.start_recording_button.setEnabled(False)
                self.stop_recording_button.setEnabled(True)
                self.recording_status_label.setText(f"🔴 Recording: {self.recording_filename}")
                self.recording_status_label.setStyleSheet("""
                    QLabel { 
                        padding: 8px; 
                        font-weight: bold; 
                        border: 2px solid #f44336; 
                        border-radius: 5px; 
                        background-color: #ffebee; 
                        color: #c62828;
                    }
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
            
            self.start_recording_button.setEnabled(True)
            self.stop_recording_button.setEnabled(False)
            self.recording_status_label.setText("⚫ Not Recording")
            self.recording_status_label.setStyleSheet("""
                QLabel { 
                    padding: 8px; 
                    font-weight: bold; 
                    border: 2px solid #ddd; 
                    border-radius: 5px; 
                    background-color: #f9f9f9; 
                }
            """)
            
            print(f"Recording saved: {self.recording_filename}")

    def toggle_pause(self):
        """Toggle video pause/resume"""
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.pause_button.setText("▶️ Resume Stream")
            self.pause_button.setStyleSheet("""
                QPushButton { 
                    padding: 10px; 
                    font-weight: bold; 
                    background-color: #2ecc71; 
                    color: white; 
                    border: none; 
                    border-radius: 5px; 
                }
                QPushButton:hover { background-color: #27ae60; }
            """)
            print("Video paused")
            # Store current frame for live updates when paused
            if hasattr(self, 'image') and self.image is not None:
                self.paused_frame = self.image.copy()
        else:
            self.pause_button.setText("⏸️ Pause Stream")
            self.pause_button.setStyleSheet("""
                QPushButton { 
                    padding: 10px; 
                    font-weight: bold; 
                    background-color: #f39c12; 
                    color: white; 
                    border: none; 
                    border-radius: 5px; 
                }
                QPushButton:hover { background-color: #e67e22; }
            """)
            print("Video resumed")
            
    def resizeEvent(self, event):
        """Handle window resize event"""
        super().resizeEvent(event)
        # Force a refresh of the video displays after resize
        if hasattr(self, 'image') and self.image is not None:
            # Trigger a timer event to refresh the displays
            self.timerEvent(None)

    def closeEvent(self, event):
        """Handle application close event"""
        # Stop recording if active
        if self.is_recording:
            self.stop_recording()
        
        # Release video capture
        if self.cap:
            self.cap.release()
        
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ColorDetectionApp()
    window.show()
    sys.exit(app.exec_())
