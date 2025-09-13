import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QSlider, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap

class ColorDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Color Detection')
        self.setGeometry(100, 100, 200, 150)

        # Create a central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create layout
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Create labels for images
        self.original_label = QLabel() 
        self.mask_label = QLabel()
        self.result_label = QLabel()

        self.layout.addWidget(self.original_label)
        self.layout.addWidget(self.mask_label)
        self.layout.addWidget(self.result_label)

        # Add a QLabel to display the current HSV values
        self.hsv_value_label = QLabel()  # Create a label for displaying HSV values
        self.layout.addWidget(self.hsv_value_label)  # Add the label to the layout

        # Create sliders for HSV range adjustment
        self.h_lower_slider = self.create_slider('H Lower', 0, 179)
        self.h_upper_slider = self.create_slider('H Upper', 0, 179)
        self.s_lower_slider = self.create_slider('S Lower', 0, 255)
        self.s_upper_slider = self.create_slider('S Upper', 0, 255)
        self.v_lower_slider = self.create_slider('V Lower', 0, 255)
        self.v_upper_slider = self.create_slider('V Upper', 0, 255)

        self.layout.addWidget(self.h_lower_slider)
        self.layout.addWidget(self.h_upper_slider)
        self.layout.addWidget(self.s_lower_slider)
        self.layout.addWidget(self.s_upper_slider)
        self.layout.addWidget(self.v_lower_slider)
        self.layout.addWidget(self.v_upper_slider)

        # Create a button to save HSV limits
        self.save_button = QPushButton("Save HSV Limits")
        self.save_button.clicked.connect(self.save_hsv_limits)  # Connect button to save method
        self.layout.addWidget(self.save_button)  # Add the button to the layout

        # Initialize the video capture
        # self.video_source =  "rtsp://admin:infinity-2060@192.168.1.64:554" # Use 0 for the default camera, or replace with your RTSP URL
        self.video_source = 0
        self.cap = cv2.VideoCapture(self.video_source)

        # Check if the video capture is opened successfully
        if not self.cap.isOpened():
            print("Error: Could not open video source.")
            exit()

        # Update the timer interval to achieve approximately 25 FPS
        self.timer = self.startTimer(1)  # 1000 ms / 25 FPS = 40 ms

        # Connect slider value changes to the update method
        self.h_lower_slider.valueChanged.connect(self.update_sliders)
        self.h_upper_slider.valueChanged.connect(self.update_sliders)
        self.s_lower_slider.valueChanged.connect(self.update_sliders)
        self.s_upper_slider.valueChanged.connect(self.update_sliders)
        self.v_lower_slider.valueChanged.connect(self.update_sliders)
        self.v_upper_slider.valueChanged.connect(self.update_sliders)

    def create_slider(self, label, min_value, max_value):
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_value)
        slider.setMaximum(max_value)
        slider.setValue(min_value)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(1)
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

        # Convert images to QImage format for display
        self.display_image(self.original_label, self.image)
        self.display_image(self.mask_label, mask)
        self.display_image(self.result_label, result)

    def display_image(self, label, image):
        # Resize the image to fit the label while maintaining aspect ratio
        max_width = label.width()
        max_height = label.height()
        height, width = image.shape[:2]

        # Calculate the aspect ratio
        aspect_ratio = width / height

        if width > max_width or height > max_height:
            if aspect_ratio > 1:  # Wider than tall
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:  # Taller than wide
                new_height = max_height
                new_width = int(max_height * aspect_ratio)
        else:
            new_width, new_height = width, height

        # Resize the image
        resized_image = cv2.resize(image, (new_width, new_height))

        if len(resized_image.shape) == 2:  # Grayscale image
            resized_image = cv2.cvtColor(resized_image, cv2.COLOR_GRAY2BGR)
        else:  # Color image
            resized_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)

        height, width, channel = resized_image.shape
        bytes_per_line = 3 * width
        q_image = QImage(resized_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        label.setPixmap(QPixmap.fromImage(q_image))

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ColorDetectionApp()
    window.show()
    sys.exit(app.exec_())
