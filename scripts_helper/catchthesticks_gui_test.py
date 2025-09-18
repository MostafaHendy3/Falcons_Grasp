import sys
import cv2
import numpy as np
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QThread, pyqtSignal

# Define color ranges for detection
# H Lower: 94, H Upper: 111, S Lower: 141, S Upper: 204, V Lower: 21, V Upper: 255
# H Lower: 125, H Upper: 162, S Lower: 77, S Upper: 255, V Lower: 90, V Upper: 255

# colors = {
#     "light blue": ((94, 141, 21), (111, 204, 255)),  # Approximate HSV range for dark green
#     "purple": ((125, 77, 90), (162, 255, 255)),
#     "yellow": ((25,52,93),(41,255,255)),  # Approximate HSV range for pink
#     "Red": ((171,175,116),(179,255,255)),
#     "green": ((56,20,0),(87,255,255)),  # Approximate HSV range for purple
#     "orange": ((6,175,46),(13,255,255)),  # Approximate HSV range for light green
#     # "Black": ((0, 0, 0), (180, 255, 30)),  # Approximate HSV range for black
#     # "White": ((0, 0, 200), (180, 25, 255)),  # Approximate HSV range for white
#     # "Brown": ((10, 100, 20), (20, 255, 200)),  # Approximate HSV range for brown
#     # "Blue": ((100, 100, 100), (130, 255, 255))  # Approximate HSV range for blue
# }

colors = {
    "red": ((166,166,100),(179,255,255)),
    "brown": ((0,117,119),(22,255,255)),
    "pink": ((143,99,129),(162,143,255)),
    "blue": ((90, 140, 146), (122, 198, 255)),
    "green":((50,80,138),(67,255,255)),
    "dark green": ((76,94,73),(88,255,255)),
    "yellow": ((22,81,144),(53,255,255)),
    "white":((98,0,216),(121,56,255)),
    "black": ((83,0,0),(179,79,88)),
    "purple": ((133,80,0),(144,255,255))
}

class VideoCaptureWorker(QThread):
    frame_ready = pyqtSignal(QtGui.QImage)  # Signal to send the frame to the main thread

    def __init__(self, rtsp_url):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.running = True  # Control the running state

    def run(self):
        cap = cv2.VideoCapture(self.rtsp_url)

        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame. Attempting to reconnect...")
                cap.release()
                cap = cv2.VideoCapture(self.rtsp_url)
                continue

            # Resize frame for faster processing
            frame = cv2.resize(frame, (640, 480))  # Adjust size as needed
            processed_frame = self.detect_custom_colors(frame)

            # Convert the frame to RGB format for Qt
            rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            q_image = QtGui.QImage(rgb_frame.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)

            # Emit the frame ready signal
            self.frame_ready.emit(q_image)

        cap.release()

    def detect_custom_colors(self, frame):
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        detected_colors = set()

        for color_name, (lower, upper) in colors.items():
            mask = cv2.inRange(hsv_frame, np.array(lower), np.array(upper))
            
            # Find contours in the mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
# if area > 200:  # Only consider contours with area greater than 200
    # # Approximate the contour to a polygon
    # epsilon = 0.02 * cv2.arcLength(contour, True)  # Adjust epsilon for approximation accuracy
    # approx = cv2.approxPolyDP(contour, epsilon, True)  # Approximate the contour

    # # Check if the approximated contour has 4 vertices (indicating a rectangle)
    # if len(approx) == 4:
    #     # Optionally check aspect ratio
    #     x, y, w, h = cv2.boundingRect(approx)  # Get the bounding box
    #     aspect_ratio = float(w) / h  # Calculate aspect ratio
    #     if 0.8 < aspect_ratio < 1.2:  # Check if aspect ratio is close to 1 (square)
    #         detected_colors.add(color_name)  # Add color to detected colors
    #         # Draw the contour on the original frame
    #         cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)  # Green contours

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 1500 :  # Only consider contours with area greater than 200
                    detected_colors.add(color_name)  # Add color to detected colors
                    # Draw the contour on the original frame
                    print(f"{color_name} area {area}")
                    cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)  # Green contours

        print(f"Detected colors: {detected_colors}")
        return frame  # Return the frame with contours drawn

    def stop(self):
        self.running = False
        self.quit()  # Properly stop the thread

class StreamWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTSP Stream")
        self.label = QtWidgets.QLabel(self)
        self.label.setScaledContents(True)
        self.setFixedSize(800, 600)
        self.label.setFixedSize(800, 600)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.label)

    def update_frame(self, q_image):
        self.label.setPixmap(QtGui.QPixmap.fromImage(q_image))

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # rtsp_url = "rtsp://admin:infinity-2060@192.168.0.18:554"  # Replace with your RTSP stream URL
    rtsp_url = 0
    worker = VideoCaptureWorker(rtsp_url)

    # Create a window for the stream
    stream_window = StreamWindow()
    stream_window.show()

    # Connect the frame_ready signal to update the stream window
    worker.frame_ready.connect(stream_window.update_frame)

    worker.start()  # Start the video capture thread

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("Stopping...")
        worker.stop()  # Stop the worker thread when closing
