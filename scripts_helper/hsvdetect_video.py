import sys
import cv2
import numpy as np
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QSlider, QVBoxLayout, 
                             QHBoxLayout, QWidget, QPushButton, QGroupBox, QGridLayout, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QFont

class ColorDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('HSV Color Detection with Video Recording')
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
        self.video_source = 0
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
        self.timer = self.startTimer(1)  # 1000 ms / 25 FPS = 40 ms

        # Connect slider value changes to the update method
        self.h_lower_slider.valueChanged.connect(self.update_sliders)
        self.h_upper_slider.valueChanged.connect(self.update_sliders)
        self.s_lower_slider.valueChanged.connect(self.update_sliders)
        self.s_upper_slider.valueChanged.connect(self.update_sliders)
        self.v_lower_slider.valueChanged.connect(self.update_sliders)
        self.v_upper_slider.valueChanged.connect(self.update_sliders)

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
        
        self.mask_title = QLabel("HSV Mask")
        self.mask_title.setAlignment(Qt.AlignCenter)
        self.mask_title.setFont(QFont("Arial", 10, QFont.Bold))
        
        self.mask_label = QLabel()
        self.mask_label.setMinimumSize(300, 200)
        self.mask_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mask_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        self.mask_label.setAlignment(Qt.AlignCenter)
        self.mask_label.setText("HSV Mask")
        self.mask_label.setScaledContents(False)  # Let Qt handle scaling
        
        self.result_title = QLabel("Filtered Result")
        self.result_title.setAlignment(Qt.AlignCenter)
        self.result_title.setFont(QFont("Arial", 10, QFont.Bold))
        
        self.result_label = QLabel()
        self.result_label.setMinimumSize(300, 200)
        self.result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setText("Filtered Result")
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
        
        # HSV Controls Group
        self.create_hsv_controls()
        
        # Recording Controls Group
        self.create_recording_controls()
        
        # HSV Values Display Group
        self.create_hsv_display()
        
        # Add stretch to push everything to top
        self.control_layout.addStretch()
        
        self.main_layout.addWidget(self.control_panel, 1)  # Takes 1/3 of horizontal space

    def create_hsv_controls(self):
        """Create HSV slider controls"""
        self.hsv_group = QGroupBox("HSV Range Controls")
        self.hsv_layout = QGridLayout()
        self.hsv_group.setLayout(self.hsv_layout)
        
        # Create sliders with labels
        self.h_lower_slider = self.create_labeled_slider("H Lower:", 0, 179, 0)
        self.h_upper_slider = self.create_labeled_slider("H Upper:", 0, 179, 179)
        self.s_lower_slider = self.create_labeled_slider("S Lower:", 0, 255, 0)
        self.s_upper_slider = self.create_labeled_slider("S Upper:", 0, 255, 255)
        self.v_lower_slider = self.create_labeled_slider("V Lower:", 0, 255, 0)
        self.v_upper_slider = self.create_labeled_slider("V Upper:", 0, 255, 255)
        
        # Add sliders to grid layout
        sliders = [
            ("H Lower:", self.h_lower_slider, 0),
            ("H Upper:", self.h_upper_slider, 1),
            ("S Lower:", self.s_lower_slider, 2),
            ("S Upper:", self.s_upper_slider, 3),
            ("V Lower:", self.v_lower_slider, 4),
            ("V Upper:", self.v_upper_slider, 5)
        ]
        
        for label_text, slider, row in sliders:
            label = QLabel(label_text)
            value_label = QLabel(str(slider.value()))
            value_label.setMinimumWidth(30)
            slider.value_label = value_label  # Store reference for updates
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(str(v)))
            
            self.hsv_layout.addWidget(label, row, 0)
            self.hsv_layout.addWidget(slider, row, 1)
            self.hsv_layout.addWidget(value_label, row, 2)
        
        # Save button
        self.save_button = QPushButton("Save HSV Limits")
        self.save_button.clicked.connect(self.save_hsv_limits)
        self.save_button.setStyleSheet("QPushButton { padding: 8px; font-weight: bold; }")
        self.hsv_layout.addWidget(self.save_button, 6, 0, 1, 3)
        
        self.control_layout.addWidget(self.hsv_group)

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

    def create_hsv_display(self):
        """Create HSV values display"""
        self.hsv_display_group = QGroupBox("Current HSV Values")
        self.hsv_display_layout = QVBoxLayout()
        self.hsv_display_group.setLayout(self.hsv_display_layout)
        
        self.hsv_value_label = QLabel("H: 0-179, S: 0-255, V: 0-255")
        self.hsv_value_label.setWordWrap(True)
        self.hsv_value_label.setStyleSheet("""
            QLabel { 
                padding: 10px; 
                font-family: monospace; 
                background-color: #f0f0f0; 
                border: 1px solid #ccc; 
                border-radius: 5px; 
            }
        """)
        
        self.hsv_display_layout.addWidget(self.hsv_value_label)
        self.control_layout.addWidget(self.hsv_display_group)

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
        h_lower = self.h_lower_slider.value()
        h_upper = self.h_upper_slider.value()
        s_lower = self.s_lower_slider.value()
        s_upper = self.s_upper_slider.value()
        v_lower = self.v_lower_slider.value()
        v_upper = self.v_upper_slider.value()

        # Ensure that the upper bounds are greater than the lower bounds
        if h_lower > h_upper:
            self.h_upper_slider.setValue(h_lower)  # Adjust upper slider
        if s_lower > s_upper:
            self.s_upper_slider.setValue(s_lower)  # Adjust upper slider
        if v_lower > v_upper:
            self.v_upper_slider.setValue(v_lower)  # Adjust upper slider

        # Print the current HSV values
        hsv_values = f"H Lower: {h_lower}, H Upper: {h_upper},\nLower: {s_lower}, S Upper: {s_upper}, V Lower: {v_lower}, \nV Upper: {v_upper}"
        print(f"Current HSV Values: {hsv_values}")

        # Update the label to show current HSV values on the GUI
        self.hsv_value_label.setText(hsv_values)  # Set the text of the label

    def timerEvent(self, event):
        # Capture frame-by-frame
        ret, self.image = self.cap.read()
        
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
        # Convert the image to HSV color space
        hsv_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2HSV)

        # Get the current positions of the sliders
        h_lower = self.h_lower_slider.value()
        h_upper = self.h_upper_slider.value()
        s_lower = self.s_lower_slider.value()
        s_upper = self.s_upper_slider.value()
        v_lower = self.v_lower_slider.value()
        v_upper = self.v_upper_slider.value()

        # Define the HSV range for color detection
        lower_bound = np.array([h_lower, s_lower, v_lower])
        upper_bound = np.array([h_upper, s_upper, v_upper])

        # Create a mask for the specified color range
        mask = cv2.inRange(hsv_image, lower_bound, upper_bound)

        # Bitwise-AND mask and original image
        result = cv2.bitwise_and(self.image, self.image, mask=mask)

        # Record frame if recording is active
        if self.is_recording and self.video_writer is not None:
            self.video_writer.write(self.image)

        # Convert images to QImage format for display
        self.display_image(self.original_label, self.image)
        self.display_image(self.mask_label, mask)
        self.display_image(self.result_label, result)

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

    def save_hsv_limits(self):
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

    def start_recording(self):
        """Start video recording"""
        if not self.is_recording:
            # Get frame dimensions
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Could not read frame to get dimensions.")
                return
            
            self.frame_height, self.frame_width = frame.shape[:2]
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.recording_filename = f"hsvdetect_recording_{timestamp}.mp4"
            
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
