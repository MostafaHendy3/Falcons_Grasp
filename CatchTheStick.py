"""CatchTheStick (Falcon's Grasp) — PyQt5 game UI

Consolidated imports and improved QtMultimedia error if missing. Behavior unchanged.
"""

import csv
from datetime import datetime
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
from PyQt5.QtGui import QMovie,QPainter, QColor, QFont,QFontDatabase ,QImage, QPixmap,QPen, QPainterPath , QPolygonF
from PyQt5.QtCore import QTimer,Qt, pyqtSignal, pyqtSlot ,QThread , QTime,QSize,QRectF,QPointF, QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget ,QGridLayout,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QTableWidget,QTableWidgetItem,QHeaderView,QFrame
import math 
import csv , requests ,time
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets
import paho.mqtt.client as mqtt
import numpy as np
try:
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
except Exception as e:
    raise ImportError(
        "Missing PyQt5 multimedia backend. Install system packages: 'sudo apt install -y python3-pyqt5 python3-pyqt5.qtmultimedia libqt5multimedia5 libqt5multimedia5-plugins libqt5multimediawidgets5' or use pip: 'python3 -m pip install PyQt5'"
    ) from e
final_screen_timer_idle = 30000

TimerValue = 15000
global scaled
scaled = 1
teamName = ""
global scored
scored = 0
homeOpened = False

list_players_name = [
    "[1] Player1",  # Temporary name 1
    "[2] Player2",  # Temporary name 2
    "[3] Player3",  # Temporary name 3
    "[4] Player4",  # Temporary name 4
    "[5] Player5"   # Temporary name 5
]
list_players_id = []
list_top5_CatchTheStick = []
finalscore = 0


list_players_score = [0,0,0,0,0,0,0]

import time
import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

class MqttThread(QThread):
    message_signal = pyqtSignal(list)
    start_signal = pyqtSignal()
    stop_signal = pyqtSignal()
    restart_signal = pyqtSignal()
    activate_signal = pyqtSignal()
    deactivate_signal = pyqtSignal()

    def __init__(self, broker='localhost', port=1883):
        super().__init__()
        self.data_topics = [
            "CatchTheStick/TeamName/Pub",
            "CatchTheStick/score/Pub",
            "CatchTheStick/camera/0",
            "CatchTheStick/camera/1",   
            "CatchTheStick/camera/2",
            "CatchTheStick/camera/3",
            "CatchTheStick/camera/4"
        ]
        self.control_topics = [
            "CatchTheStick/game/start",
            "CatchTheStick/game/stop",
            "CatchTheStick/game/restart",
            "CatchTheStick/game/timer",
            "CatchTheStick/game/Activate",
            "CatchTheStick/game/Deactivate",
            "CatchTheStick/game/timerfinal"
        ]
        self.broker = broker
        self.port = port
        self.client = mqtt.Client()
        self.subscribed = False

    def run(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker, self.port)
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        for topic in self.control_topics:
            client.subscribe(topic)

    def on_message(self, client, userdata, msg):
        print(f"Received message '{msg.payload.decode()}' on topic '{msg.topic}'")

        if msg.topic == "CatchTheStick/game/start":
            self.handle_start()
        elif msg.topic == "CatchTheStick/game/Activate":
            self.handle_Activate()
        elif msg.topic == "CatchTheStick/game/Deactivate":
            self.deactivate_signal.emit()
        elif msg.topic == "CatchTheStick/game/stop":
            if msg.payload.decode() == "0":
                self.handle_stop()
            elif msg.payload.decode() == "1":
                self.unsubscribe_from_data_topics()
                
        elif msg.topic == "CatchTheStick/game/restart":
            print("Game restarted")
            self.handle_restart()
        elif msg.topic == "CatchTheStick/game/timer":
            global TimerValue
            TimerValue = int(msg.payload.decode())*1000
            print(TimerValue)
            with open("file2.txt", "w") as file:  # Open the file in append mode
                file.write(f"{TimerValue}\n")  # Write the value followed by a newline
        elif msg.topic == "CatchTheStick/game/timerfinal":
            global final_screen_timer_idle
            final_screen_timer_idle = int(msg.payload.decode())*1000
            print(final_screen_timer_idle)
            # Save final_screen_timer_idle to file.txt
            with open("file.txt", "w") as file:  # Open the file in append mode
                file.write(f"{final_screen_timer_idle}\n")  # Write the value followed by a newline

        else:
            if self.subscribed:
                self.handle_data_message(msg)

    def handle_data_message(self, msg):
        # Check if the client is currently subscribed to any topics and if the message's topic is one of them
        if self.subscribed and msg.topic in self.data_topics:
            # make a list of data and topic number
            list_data = []
            list_data.append(msg.topic) 
            list_data.append(msg.payload.decode())
            print(list_data)
            self.message_signal.emit(list_data)
        else:
            print(f"Received message from non-subscribed or unknown topic: {msg.topic}")

    def handle_restart(self):
        print("Game restarted")
        # self.subscribe_to_data_topics()
        self.restart_signal.emit()     

    def handle_start(self):
        print("Game started")
        self.subscribe_to_data_topics()
        self.start_signal.emit()

    def handle_Activate(self):
        print("Game Activated")
        # self.subscribe_to_data_topics()
        self.activate_signal.emit()

    def handle_stop(self):
        print("Game stopped")
        self.unsubscribe_from_data_topics()
        self.stop_signal.emit()
        # self.client.disconnect()

   
    def subscribe_to_data_topics(self):
        if not self.subscribed:
            for topic in self.data_topics:
                self.client.subscribe(topic)
            self.subscribed = True

    def unsubscribe_from_data_topics(self):
        if self.subscribed:
            for topic in self.data_topics:
                self.client.unsubscribe(topic)
            self.subscribed = False
    


class Final_Screen(QtWidgets.QMainWindow):
    def load_custom_font(self, font_path):
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            print(f"Failed to load font: {font_path}")
            return "Default"  # Return a default font name in case of failure
        font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            font_family = font_families[0]
            print(f"Font Family Loaded: {font_family}")  # Print to verify the font family name
            return font_family
        else:
            print(f"No font families found for: {font_path}")
            return "Default"
    def showTable(self):
        self.Label.hide()
        self.Label2.show()
        self.tableWidget_2.show()
        self.UpdateTable()
    def TimerWidget(self,centralwidget):
        self.Countdown = QtWidgets.QWidget(centralwidget)
        self.Label = QtWidgets.QLabel(centralwidget)
        # self.Label.setGeometry(QtCore.QRect(0, 0, 800, 1100))    
    def hideTable(self):
        self.Label2.hide()
        self.tableWidget_2.hide()
    def UpdateTable(self):
        # Initialize an empty dictionary to store team data
        
        global list_top5_CatchTheStick
        # Sort the list_team dictionary by score in descending order
        sorted_data = sorted(list_top5_CatchTheStick, key=lambda item: item[1], reverse=True)
        print(sorted_data)

        # # Clear the table before updating
        # self.tableWidget_2.clearContents()
        # self.tableWidget_2.setRowCount(0)  # Make sure to reset row count

        # Loop over the top 5 items in the sorted data
        for i, (team, score) in enumerate(sorted_data):
            if i >= 5:  # Stop after the top 5
                break

            # # Insert a new row
            # self.tableWidget_2.insertRow(i)

            # Create and set the team name item
            team_item = QtWidgets.QTableWidgetItem(team)
            team_item.setTextAlignment(QtCore.Qt.AlignCenter)  # Center align the text
            self.tableWidget_2.setItem(i, 0, team_item)

            # Create and set the score item
            score_item = QtWidgets.QTableWidgetItem(str(score))
            score_item.setTextAlignment(QtCore.Qt.AlignCenter)  # Center align the text
            self.tableWidget_2.setItem(i, 1, score_item)     
    def setupTimer(self):
        # Start the GIF
        self.movie.start()
        # # timer
        # self.timer.setSingleShot(True)
        # self.timer.setTimerType(Qt.PreciseTimer)
        
        # self.timer.timeout.connect(lambda:(
        #     self.showTable()
        # ))
        # self.timer.start(2000)
        
        # self.timer2.setSingleShot(True)
        # self.timer2.timeout.connect(lambda:(
        #     self.hideTable()
        # ))
        # self.timer2.setTimerType(Qt.PreciseTimer)
        # self.timer2.start(7000)
        
    
    def setupUi(self, Home):
        Home.setObjectName("Home")
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        Home.setLayoutDirection(QtCore.Qt.LeftToRight)
        Home.setAutoFillBackground(False)
        Home.setStyleSheet("/* Base Styling for Application */\n"
"* {\n"
"    color: #ffffff;  /* Default text color for dark theme */\n"
"}\n"
"\n"
"/* General Background */\n"
"QWidget {\n"
"    background-color: transparent;  /* Transparent background for all widgets */\n"
"}\n"
"\n"
"/* QPushButton Styling */\n"
"QPushButton {\n"
"    background-color: #2e4053;  /* Darker muted blue background */\n"
"    color: #ffffff;  /* White text color */\n"
"    border: 1px solid #3b5998;  /* Slightly lighter border */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 8px 16px;  /* Padding inside the button */\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #4c669f;  /* Medium muted blue on hover */\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #1c2833;  /* Even darker muted blue when pressed */\n"
"}\n"
"\n"
"/* QLabel Styling */\n"
"QLabel {\n"
"    color: #b3e5fc;  /* White text color */\n"
"}\n"
"\n"
"/* QLineEdit Styling */\n"
"QLineEdit {\n"
"    border: 1px solid #3b5998;  /* Border color */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 4px 8px;  /* Padding inside the line edit */\n"
"    background-color: #2e4053;  /* Darker muted blue background */\n"
"    color: #ffffff;  /* White text color */\n"
"}\n"
"\n"
"/* QTableWidget Styling */\n"
"QTableWidget {\n"
"    background-color: transparent;  /* Transparent background */\n"
"    color: #ffffff;  /* White text color */\n"
"    gridline-color: #3b5998;  /* Medium muted blue gridline color */\n"
"    selection-background-color: transparent;  /* Transparent selection background */\n"
"    selection-color: #ffffff;  /* White selection text color */\n"
"    border: 1px solid #3b5998;  /* Border around the table */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 4px;  /* Padding inside the table */\n"
"    margin: 8px;  /* Margin around the table */\n"
"}\n"
"\n"
"QHeaderView::section { \n"
"    background-color: #001f3f;  /* Dark blue background for header sections */\n"
"    color: #ffffff;  /* White text color for header sections */\n"
"    padding: 5px;  /* Padding for header sections */\n"
"    border: 1px solid #3b5998;  /* Border color to match table */\n"
"}\n"
"\n"
"QHeaderView {\n"
"    background-color: transparent;  /* Transparent background */\n"
"}\n"
"\n"
"QTableCornerButton::section {\n"
"    background-color: transparent;  /* Transparent background */\n"
"}\n"
"\n"
"QTableWidget::item {\n"
"    padding: 4px;  /* Padding for items */\n"
"    border: none;  /* No border for items */\n"
"}\n"
"\n"
"QTableWidget::item:selected {\n"
"    background-color: transparent;  /* Transparent background for selected items */\n"
"    color: #2e4053;  /* Blue text color for selected items */\n"
"}\n"
"\n"
"QTableWidget::item:hover {\n"
"    background-color: #001f3f;  /* Dark blue background on hover */\n"
"}\n"
"\n"
"/* QScrollBar Styling */\n"
"QScrollBar:vertical, QScrollBar:horizontal {\n"
"    background-color: #1c2833;  /* Deep muted blue background for scrollbar */\n"
"    border: 1px solid #3b5998;  /* Border color */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"}\n"
"\n"
"QScrollBar::handle:vertical, QScrollBar::handle:horizontal {\n"
"    background-color: #2e4053;  /* Darker muted blue handle */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"}\n"
"\n"
"QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {\n"
"    background-color: #4c669f;  /* Medium muted blue handle on hover */\n"
"}\n"
"\n"
"/* QTabWidget Styling */\n"
"QTabWidget::pane {\n"
"    border: 1px solid #3b5998;  /* Border around tabs */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"}\n"
"\n"
"QTabBar::tab {\n"
"    background-color: #2e4053;  /* Dark blue tab background */\n"
"    color: #ffffff;  /* White text color */\n"
"    border: 1px solid #3b5998;  /* Border color */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 8px 16px;  /* Padding inside tabs */\n"
"}\n"
"\n"
"QTabBar::tab:selected {\n"
"    background-color: #4c669f;  /* Medium muted blue background for selected tab */\n"
"    color: #ffffff;  /* White text color for selected tab */\n"
"}\n"
"\n"
"/* Circular Countdown Timer Styling */\n"
".circular-countdown {\n"
"    border: 8px solid #1c2833;  /* Deep muted blue background for the circle */\n"
"    border-radius: 50%;  /* Makes the border circular */\n"
"    width: 100px;  /* Width of the countdown circle */\n"
"    height: 100px;  /* Height of the countdown circle */\n"
"    background-color: #1c2833;  /* Deep muted blue background */\n"
"    color: #ffffff;  /* White text color */\n"
"    display: flex;  /* Center the text inside */\n"
"    align-items: center;  /* Center vertically */\n"
"    justify-content: center;  /* Center horizontally */\n"
"    font-size: 24px;  /* Text size */\n"
"    position: relative;  /* For positioning overlay */\n"
"}\n"
"\n"
"/* Styling for Countdown Progress */\n"
".circular-countdown.progress {\n"
"    border-color: #3b5998;  /* Medium muted blue color during progress */\n"
"}\n"
"\n"
"/* Styling for Countdown Finished */\n"
".circular-countdown.finished {\n"
"    border-color: #32cd32;  /* Green color when finished */\n"
"}\n"
"\n"
"/* Optional: Styling for Overlay Background Widget */\n"
".circular-countdown-background {\n"
"    position: absolute;  /* Position it on top of the countdown */\n"
"    top: 0;\n"
"    left: 0;\n"
"    width: 100%;\n"
"    height: 100%;\n"
"    background-color: rgba(0, 0, 0, 0.5);  /* Semi-transparent dark overlay */\n"
"    border-radius: 50%;  /* Match the circular shape */\n"
"}\n"
"")
        self.centralwidget = QtWidgets.QWidget(Home)
        # print(QtWidgets.QDesktopWidget().screenGeometry())
        Home.setGeometry(0, 0, QtWidgets.QDesktopWidget().screenGeometry().width(), QtWidgets.QDesktopWidget().screenGeometry().height())
        print(Home.geometry().width())
        self.font_family = self.load_custom_font("Assets/Fonts/GOTHIC.TTF")  # Update with the correct path
        self.font_family_good = self.load_custom_font("Assets/Fonts/good_times_rg.ttf")  # Update with the correct path

        # self.scaleFactor = 
        # if QtWidgets.QDesktopWidget().screenGeometry().width() > 1920:
        if Home.geometry().width() > 1080:
                self.movie= QMovie("Assets/1k/portrait/portrait_CatchTheStick_final.gif")
                self.movie.setCacheMode(QMovie.CacheAll) 
                print("1")
                self.scale = 2
        else:
                self.movie= QMovie("Assets/1k/portrait/portrait_CatchTheStick_final.gif")
                self.movie.setCacheMode(QMovie.CacheAll) 
                print("2")
                self.scale = 1
        self.Background = QtWidgets.QLabel(self.centralwidget)
        self.Background.setScaledContents(True)
        # self.Background.setGeometry(0, 0, QtWidgets.QDesktopWidget().screenGeometry().width(), QtWidgets.QDesktopWidget().screenGeometry().height())
        self.Background.setGeometry(0, 0, Home.geometry().width(), Home.geometry().height())
        self.Background.setText("")
        self.Background.setMovie(self.movie)
        self.Background.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.timer = QTimer(Home)
        self.timer2 = QTimer(Home)
        self.setupTimer()
        self.TimerWidget(self.centralwidget)
        self.Label2 = QtWidgets.QLabel(self.centralwidget)
        # self.Label.setGeometry(QtCore.QRect(0, 0, 800, 1100))
        # self.Label.setGeometry(QtCore.QRect(1050, 900, 400, 800))
        self.Label2.setGeometry(QtCore.QRect(350*self.scale, 400*self.scale, 400*self.scale, 150*self.scale))
        self.Label2.setText(str(finalscore))  # Ensure the number is converted to a string
        self.Label2.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(35*self.scale)
        font.setFamily(self.font_family_good)
        self.Label2.setFont(font)
        self.Label2.setStyleSheet("color: rgb(255, 255, 255);")
        self.Label2.hide()
        self.Label2.raise_()
        
        self.frame_2 = QtWidgets.QFrame(self.centralwidget)
        self.frame_2.setGeometry(QtCore.QRect(200*self.scale, 750*self.scale, 650*self.scale, 415*self.scale))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy)
        # self.frame_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        # self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.gridLayout = QtWidgets.QGridLayout(self.frame_2)
        self.gridLayout.setObjectName("gridLayout")
        self.tableWidget_2 = QtWidgets.QTableWidget(self.frame_2)
        # self.tableWidget_2.hide()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableWidget_2.sizePolicy().hasHeightForWidth())
        self.tableWidget_2.setSizePolicy(sizePolicy)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(102, 171, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(65, 142, 235))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(14, 57, 108))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(19, 75, 144))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.HighlightedText, brush)
        brush = QtGui.QBrush(QtGui.QColor(141, 184, 235))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(102, 171, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(65, 142, 235))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(14, 57, 108))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(19, 75, 144))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.HighlightedText, brush)
        brush = QtGui.QBrush(QtGui.QColor(141, 184, 235))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(102, 171, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(65, 142, 235))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(14, 57, 108))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(19, 75, 144))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.HighlightedText, brush)
        brush = QtGui.QBrush(QtGui.QColor(28, 113, 216))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.tableWidget_2.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(25*self.scale)
        font.setBold(False)
        font.setItalic(False)
        # font.setWeight(75)
        self.tableWidget_2.setFont(font)
        self.tableWidget_2.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.tableWidget_2.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tableWidget_2.setAutoFillBackground(False)
        self.tableWidget_2.setStyleSheet("")
        self.tableWidget_2.setLineWidth(0)
        self.tableWidget_2.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableWidget_2.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableWidget_2.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.tableWidget_2.setAutoScroll(False)
        self.tableWidget_2.setAutoScrollMargin(0)
        self.tableWidget_2.setProperty("showDropIndicator", False)
        self.tableWidget_2.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tableWidget_2.setTextElideMode(QtCore.Qt.ElideLeft)
        self.tableWidget_2.setShowGrid(False)
        self.tableWidget_2.setGridStyle(QtCore.Qt.NoPen)
        self.tableWidget_2.setWordWrap(True)
        self.tableWidget_2.setCornerButtonEnabled(True)
        self.tableWidget_2.setRowCount(5)
        self.tableWidget_2.setColumnCount(2)
        self.tableWidget_2.setObjectName("tableWidget_2")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setVerticalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(22*self.scale)
        item.setFont(font)
        self.tableWidget_2.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(22*self.scale)
        item.setFont(font)
        self.tableWidget_2.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsDropEnabled|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsTristate)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(0, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(0, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(1, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(1, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(2, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(2, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(3, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(3, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(4, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(4, 1, item)

        self.tableWidget_2.horizontalHeader().setVisible(True)
        self.tableWidget_2.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidget_2.horizontalHeader().setDefaultSectionSize(300*self.scale)
        self.tableWidget_2.horizontalHeader().setMinimumSectionSize(100*self.scale)
        self.tableWidget_2.horizontalHeader().setStretchLastSection(False)
        self.tableWidget_2.verticalHeader().setVisible(False)
        self.tableWidget_2.verticalHeader().setCascadingSectionResizes(True)
        self.tableWidget_2.verticalHeader().setDefaultSectionSize(65*self.scale)
        self.tableWidget_2.verticalHeader().setMinimumSectionSize(50*self.scale)
        self.tableWidget_2.verticalHeader().setStretchLastSection(False)
        self.gridLayout.addWidget(self.tableWidget_2, 0, 0, 1, 1)
        
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(204, 224, 248))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(76, 96, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(102, 129, 161))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(204, 224, 248))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(204, 224, 248))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(76, 96, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(102, 129, 161))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(204, 224, 248))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(204, 224, 248))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(76, 96, 120))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(102, 129, 161))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(153, 193, 241))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.centralwidget.setPalette(palette)
        self.centralwidget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.centralwidget.setAutoFillBackground(False)
        self.centralwidget.setStyleSheet("")
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        # self.dateTimeEdit = QtWidgets.QDateTimeEdit(self.centralwidget)
        # self.dateTimeEdit.setGeometry(QtCore.QRect(706*self.scale, 950*self.scale, 506*self.scale, 40*self.scale))
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        # sizePolicy.setHorizontalStretch(1)
        # sizePolicy.setVerticalStretch(1)
        # sizePolicy.setHeightForWidth(self.dateTimeEdit.sizePolicy().hasHeightForWidth())
        # self.dateTimeEdit.setSizePolicy(sizePolicy)
        # font = QtGui.QFont()
        # font.setPointSize(25*self.scale)
        # self.dateTimeEdit.setFont(font)
        # self.dateTimeEdit.setFocusPolicy(QtCore.Qt.NoFocus)    
        # self.dateTimeEdit.setAutoFillBackground(False)
        # self.dateTimeEdit.setStyleSheet("Color: #5ce1e6;")
        # self.dateTimeEdit.setAlignment(QtCore.Qt.AlignCenter)
        # self.dateTimeEdit.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        # self.dateTimeEdit.setDateTime(QtCore.QDateTime(QtCore.QDate(2024, 7, 22), QtCore.QTime(0, 0, 0)))
        # self.dateTimeEdit.setDisplayFormat("dd MMM yyyy - hh:mm AP")
        # self.dateTimeEdit.setTimeSpec(QtCore.Qt.LocalTime)
        # current_date_time = QtCore.QDateTime.currentDateTime()
        # self.dateTimeEdit.setDateTime(current_date_time)
        # self.dateTimeEdit.setObjectName("dateTimeEdit")
        
        Home.setCentralWidget(self.centralwidget)
        self.UpdateTable()
        self.showTable()
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(22*self.scale)
        font.setBold(True)
        font.setWeight(75)
        self.tableWidget_2.setFont(font)
        self.retranslateUi(Home)
        
        QtCore.QMetaObject.connectSlotsByName(Home)              
    def retranslateUi(self, Home):
        _translate = QtCore.QCoreApplication.translate
        Home.setWindowTitle(_translate("Home", "MainWindow"))
        # self.label.setText(_translate("Home", "Top 5"))
        # self.tableWidget_2.setSortingEnabled(True)
        # item = self.tableWidget_2.verticalHeaderItem(0)
        # item.setText(_translate("Home", "Rank 1"))
        # item = self.tableWidget_2.verticalHeaderItem(1)
        # item.setText(_translate("Home", "Rank 2"))
        # item = self.tableWidget_2.verticalHeaderItem(2)
        # item.setText(_translate("Home", "Rank 3"))
        # item = self.tableWidget_2.verticalHeaderItem(3)
        # item.setText(_translate("Home", "Rank 4"))
        # item = self.tableWidget_2.verticalHeaderItem(4)
        # item.setText(_translate("Home", "Rank 5"))
        item = self.tableWidget_2.horizontalHeaderItem(0)
        item.setText(_translate("Home", "Team"))
        item = self.tableWidget_2.horizontalHeaderItem(1)
        item.setText(_translate("Home", "Score"))
        # __sortingEnabled = self.tableWidget_2.isSortingEnabled()
        # self.tableWidget_2.setSortingEnabled(False)
        # item = self.tableWidget_2.item(0, 0)
        # item.setText(_translate("Home", "Team 1"))
        # item = self.tableWidget_2.item(0, 1)
        # item.setText(_translate("Home", "5"))
        # item = self.tableWidget_2.item(1, 0)
        # item.setText(_translate("Home", "Team 2"))
        # item = self.tableWidget_2.item(1, 1)
        # item.setText(_translate("Home", "6"))
        # item = self.tableWidget_2.item(2, 0)
        # item.setText(_translate("Home", "Team 3"))
        # item = self.tableWidget_2.item(2, 1)
        # item.setText(_translate("Home", "548"))
        # item = self.tableWidget_2.item(3, 0)
        # item.setText(_translate("Home", "Team 5"))
        # item = self.tableWidget_2.item(3, 1)
        # item.setText(_translate("Home", "2"))
        # item = self.tableWidget_2.item(4, 0)
        # item.setText(_translate("Home", "Team 55"))
        # item = self.tableWidget_2.item(4, 1)
        # item.setText(_translate("Home", "55"))
        # self.tableWidget_2.setSortingEnabled(__sortingEnabled)
        # self.label_4.setText(_translate("Home", "Designed By www.uxe.ai"))

    
    def closeEvent(self, event):
            if hasattr(self, 'movie'):
                self.movie.stop()
                self.movie.setCacheMode(QMovie.CacheNone)
                self.movie = None
            
            # If you're using a QLabel to display the movie, clear it
            if hasattr(self, 'Background'):
                self.Background.clear()
            event.accept()
            super().closeEvent(event)   
  
class Active_screen(QWidget):
    def __init__(self):
        super().__init__()
        self.mqtt_thread =MqttThread('localhost')
        # self.mqtt_thread.start_signal.connect(self.start_game)
        # self.mqtt_thread.stop_signal.connect(self.stop_game)
        self.mqtt_thread.restart_signal.connect(self.restart_game)
        self.mqtt_thread.message_signal.connect(lambda data: self.ReceiveData(data))
        self.mqtt_thread.start()
        self.player = QMediaPlayer()    



    def play_audio(self):
        """Load and play the audio file."""
        audio_file = "mp3/2066.wav"  # Change to your audio file path
        absolute_path = os.path.abspath(audio_file)
        print("Absolute path:", absolute_path)
        self.player.setMedia(QMediaContent(QtCore.QUrl.fromLocalFile(absolute_path)))
        self.player.setVolume(100)  # Set volume (0-100)
        self.player.play()  # Start playing the audio
        
        # Connect the mediaStatusChanged signal to stop playback when finished
        self.player.mediaStatusChanged.connect(self.check_media_status)
        
    def play_audio_2(self):
        """Load and play the audio file."""
        audio_file = "mp3/2066.wav"  # Change to your audio file path
        absolute_path = os.path.abspath(audio_file)
        print("Absolute path:", absolute_path)
        self.player.setMedia(QMediaContent(QtCore.QUrl.fromLocalFile(absolute_path)))
        self.player.setVolume(100)  # Set volume (0-100)
        self.player.play()  # Start playing the audio
        
        # Connect the mediaStatusChanged signal to stop playback when finished
        self.player.mediaStatusChanged.connect(self.check_media_status)
        

    def check_media_status(self, status):
        """Check media status and stop playback if finished."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.stop()  # Stop playback when audio finishes
        
    
        
    
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        # Start the serial reader thread
        print(MainWindow.geometry().width())
        if MainWindow.geometry().width() > 1080:
                self.movie= QMovie("Assets/1k/portrait/portrait_CatchTheStick_Active.gif")
                self.movie.setCacheMode(QMovie.CacheAll) 
                print("1")
                self.scale = 2
        else:
                self.movie= QMovie("Assets/1k/portrait/portrait_CatchTheStick_Active.gif")
                self.movie.setCacheMode(QMovie.CacheAll) 
                print("2")
                self.scale = 1   

        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Ignored)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        # MainWindow.setSizePolicy(sizePolicy)
        # MainWindow.setMaximumSize(QtCore.QSize(1920*self.scale, 1080*self.scale))
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setObjectName("centralwidget")
        
        font = QtGui.QFont()
        self.font_family = self.load_custom_font("Assets/Fonts/GOTHIC.TTF")  # Update with the correct path
        self.font_family_good = self.load_custom_font("Assets/Fonts/good_times_rg.ttf")  # Update with the correct path
        font.setBold(True)
        font.setFamily(self.font_family)        
        

        
        # self.mqtt_thread =MqttThread('localhost')
        # # self.mqtt_thread.message_signal.connect(lambda data: self.Gauge.setValue(data))
        # self.mqtt_thread.start_signal.connect(self.start_game)
        # self.mqtt_thread.stop_signal.connect(self.stop_game)
        # self.mqtt_thread.restart_signal.connect(self.restart_game)
        # self.mqtt_thread.start()
        
       
        font = QtGui.QFont()
        font.setFamily(self.font_family)
        MainWindow.setStyleSheet("/* Base Styling for Application */\n"
"* {\n"
"    color: #ffffff;  /* Default text color for dark theme */\n"
"}\n"
"\n"
"/* General Background */\n"
"QWidget {\n"
"    background-color: transparent;  /* Transparent background for all widgets */\n"
"}\n"
"\n"
"/* QPushButton Styling */\n"
"QPushButton {\n"
"    background-color: #2e4053;  /* Darker muted blue background */\n"
"    color: #ffffff;  /* White text color */\n"
"    border: 1px solid #3b5998;  /* Slightly lighter border */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 8px 16px;  /* Padding inside the button */\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #4c669f;  /* Medium muted blue on hover */\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #1c2833;  /* Even darker muted blue when pressed */\n"
"}\n"
"\n"
"/* QLabel Styling */\n"
"QLabel {\n"
"    color: #b3e5fc;  /* White text color */\n"
"}\n"
"\n"
"/* QLineEdit Styling */\n"
"QLineEdit {\n"
"    border: 1px solid #3b5998;  /* Border color */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 4px 8px;  /* Padding inside the line edit */\n"
"    background-color: #2e4053;  /* Darker muted blue background */\n"
"    color: #ffffff;  /* White text color */\n"
"}\n"
"\n"
"/* QTableWidget Styling */\n"
"QTableWidget {\n"
"    background-color: transparent;  /* Transparent background */\n"
"    color: #ffffff;  /* White text color */\n"
"    gridline-color: #3b5998;  /* Medium muted blue gridline color */\n"
"    selection-background-color: transparent;  /* Transparent selection background */\n"
"    selection-color: #ffffff;  /* White selection text color */\n"
"    border: 1px solid #3b5998;  /* Border around the table */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 4px;  /* Padding inside the table */\n"
"    margin: 8px;  /* Margin around the table */\n"
"}\n"
"\n"
"QHeaderView::section { \n"
"    background-color: #001f3f;  /* Dark blue background for header sections */\n"
"    color: #ffffff;  /* White text color for header sections */\n"
"    padding: 5px;  /* Padding for header sections */\n"
"    border: 1px solid #3b5998;  /* Border color to match table */\n"
"}\n"
"\n"
"QHeaderView {\n"
"    background-color: transparent;  /* Transparent background */\n"
"}\n"
"\n"
"QTableCornerButton::section {\n"
"    background-color: transparent;  /* Transparent background */\n"
"}\n"
"\n"
"QTableWidget::item {\n"
"    padding: 4px;  /* Padding for items */\n"
"    border: none;  /* No border for items */\n"
"}\n"
"\n"
"QTableWidget::item:selected {\n"
"    background-color: transparent;  /* Transparent background for selected items */\n"
"    color: #2e4053;  /* Blue text color for selected items */\n"
"}\n"
"\n"
"QTableWidget::item:hover {\n"
"    background-color: #001f3f;  /* Dark blue background on hover */\n"
"}\n"
"\n"
"/* QScrollBar Styling */\n"
"QScrollBar:vertical, QScrollBar:horizontal {\n"
"    background-color: #1c2833;  /* Deep muted blue background for scrollbar */\n"
"    border: 1px solid #3b5998;  /* Border color */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"}\n"
"\n"
"QScrollBar::handle:vertical, QScrollBar::handle:horizontal {\n"
"    background-color: #2e4053;  /* Darker muted blue handle */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"}\n"
"\n"
"QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {\n"
"    background-color: #4c669f;  /* Medium muted blue handle on hover */\n"
"}\n"
"\n"
"/* QTabWidget Styling */\n"
"QTabWidget::pane {\n"
"    border: 1px solid #3b5998;  /* Border around tabs */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"}\n"
"\n"
"QTabBar::tab {\n"
"    background-color: #2e4053;  /* Dark blue tab background */\n"
"    color: #ffffff;  /* White text color */\n"
"    border: 1px solid #3b5998;  /* Border color */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 8px 16px;  /* Padding inside tabs */\n"
"}\n"
"\n"
"QTabBar::tab:selected {\n"
"    background-color: #4c669f;  /* Medium muted blue background for selected tab */\n"
"    color: #ffffff;  /* White text color for selected tab */\n"
"}\n"
"\n"
"/* Circular Countdown Timer Styling */\n"
".circular-countdown {\n"
"    border: 8px solid #1c2833;  /* Deep muted blue background for the circle */\n"
"    border-radius: 50%;  /* Makes the border circular */\n"
"    width: 100px;  /* Width of the countdown circle */\n"
"    height: 100px;  /* Height of the countdown circle */\n"
"    background-color: #1c2833;  /* Deep muted blue background */\n"
"    color: #ffffff;  /* White text color */\n"
"    display: flex;  /* Center the text inside */\n"
"    align-items: center;  /* Center vertically */\n"
"    justify-content: center;  /* Center horizontally */\n"
"    font-size: 24px;  /* Text size */\n"
"    position: relative;  /* For positioning overlay */\n"
"}\n"
"\n"
"/* Styling for Countdown Progress */\n"
".circular-countdown.progress {\n"
"    border-color: #3b5998;  /* Medium muted blue color during progress */\n"
"}\n"
"\n"
"/* Styling for Countdown Finished */\n"
".circular-countdown.finished {\n"
"    border-color: #32cd32;  /* Green color when finished */\n"
"}\n"
"\n"
"/* Optional: Styling for Overlay Background Widget */\n"
".circular-countdown-background {\n"
"    position: absolute;  /* Position it on top of the countdown */\n"
"    top: 0;\n"
"    left: 0;\n"
"    width: 100%;\n"
"    height: 100%;\n"
"    background-color: rgba(0, 0, 0, 0.5);  /* Semi-transparent dark overlay */\n"
"    border-radius: 50%;  /* Match the circular shape */\n"
"}\n"
"\n"
)

        # self.dateTimeEdit = QtWidgets.QDateTimeEdit(self.centralwidget)
        # self.dateTimeEdit.setGeometry(QtCore.QRect(706*self.scale, 950*self.scale, 506*self.scale, 40*self.scale))
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        # sizePolicy.setHorizontalStretch(1)
        # sizePolicy.setVerticalStretch(1)
        # sizePolicy.setHeightForWidth(self.dateTimeEdit.sizePolicy().hasHeightForWidth())
        # self.dateTimeEdit.setSizePolicy(sizePolicy)
        # font = QtGui.QFont()
        # font.setPointSize(25*self.scale)
        # self.dateTimeEdit.setFont(font)
        # self.dateTimeEdit.setFocusPolicy(QtCore.Qt.NoFocus)    
        # self.dateTimeEdit.setAutoFillBackground(False)
        # self.dateTimeEdit.setStyleSheet("Color: #5ce1e6;")
        # self.dateTimeEdit.setAlignment(QtCore.Qt.AlignCenter)
        # self.dateTimeEdit.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        # self.dateTimeEdit.setDateTime(QtCore.QDateTime(QtCore.QDate(2024, 7, 22), QtCore.QTime(0, 0, 0)))
        # self.dateTimeEdit.setDisplayFormat("dd MMM yyyy - hh:mm AP")
        # self.dateTimeEdit.setTimeSpec(QtCore.Qt.LocalTime)
        # current_date_time = QtCore.QDateTime.currentDateTime()
        # self.dateTimeEdit.setDateTime(current_date_time)
        # self.dateTimeEdit.setObjectName("dateTimeEdit")

        self.Background = QtWidgets.QLabel(self.centralwidget)
        self.Background.setScaledContents(True)
        # self.Background.setGeometry(0, 0, QtWidgets.QDesktopWidget().screenGeometry().width(), QtWidgets.QDesktopWidget().screenGeometry().height())
        self.Background.setGeometry(0, 0, MainWindow.geometry().width(), MainWindow.geometry().height())
        self.Background.setText("")
        self.Background.setMovie(self.movie)
        self.Background.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
         # Load the GIF
        # self.Blink = QMovie("Assets/active1920.gif")
        self.Background.setMovie(self.movie)
        self.movie.start()
        # self.Blink.start()
        # self.Blink.setPaused(True)
        
        #-----------------------------------------------------
        # #win and lose label
        # self.label_win = QLabel(self.centralwidget)
        # self.label_lose = QLabel(self.centralwidget)
        # self.label_win.setGeometry(QtCore.QRect(450*self.scale, 567*self.scale, 900*self.scale, 300*self.scale))
        # self.label_lose.setGeometry(QtCore.QRect(450*self.scale, 567*self.scale, 450*self.scale, 250*self.scale))
        # # set pixmap

        # self.label_win.setPixmap(QPixmap("Assets/win.svg"))
        # self.label_win.setScaledContents(True)
        # self.label_win.hide()

        # self.label_lose.setPixmap(QPixmap("Assets/losingfinal.svg"))
        # self.label_lose.setScaledContents(True)
        # self.label_lose.hide()
        
        
        
        #-----------------------------------------------------
        # self.video=VideoCaptureWidget()
        # # self.video.setGeometry(QtCore.QRect(148, 214, 1130*self.scale, 556*self.scale))
        # self.widget = QtWidgets.QWidget(self.centralwidget)
        # self.widget.setGeometry(QtCore.QRect(148*self.scale, 214*self.scale, 1130*self.scale, 556*self.scale))
        # self.widget.setObjectName("widget")
        # self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.widget)
        # self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # sizePolicy.setHorizontalStretch(1)
        # sizePolicy.setVerticalStretch(1)
        # sizePolicy.setHeightForWidth(self.video.sizePolicy().hasHeightForWidth())
        # self.video.setSizePolicy(sizePolicy)
        # self.verticalLayout_3.addWidget(self.video)
        #-----------------------------------------------------
        self.label = QtWidgets.QLabel(self.centralwidget)
        # self.Label.setGeometry(QtCore.QRect(0, 0, 800, 1100))
        # self.Label.setGeometry(QtCore.QRect(1050, 900, 400, 800))
        self.label.setGeometry(QtCore.QRect(380*self.scale, 650*self.scale, 450*self.scale, 70*self.scale))
        self.label.setText(teamName)  # Ensure the number is converted to a string
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(42*self.scale)
        font.setFamily(self.font_family_good)
        self.label.setFont(font)
        self.label.setStyleSheet("color: rgb(92,255,230);")
        
        # self.label_Score = QtWidgets.QLabel(self.centralwidget)
        # # self.Label.setGeometry(QtCore.QRect(0, 0, 800, 1100))
        # # self.Label.setGeometry(QtCore.QRect(1050, 900, 400, 800))
        # self.label_Score.setGeometry(QtCore.QRect(1353*self.scale, 506*self.scale, 450*self.scale, 70*self.scale))
        # self.label_Score.setAlignment(QtCore.Qt.AlignCenter)
        # self.label_Score.setText("Score: "+str(0))
        # font = QtGui.QFont()
        # font.setPointSize(42*self.scale)
        # font.setFamily(self.font_family_good)
        # self.label_Score.setFont(font)
        # self.label_Score.setStyleSheet("color: rgb(92,255,230);")
       #-----------------------------------------------------
        self.widget_2 = QtWidgets.QWidget(self.centralwidget)
        self.widget_2.setGeometry(QtCore.QRect(335*self.scale, 365*self.scale, 445*self.scale, 169*self.scale))
        self.widget_2.setObjectName("widget_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetMaximumSize)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lcdNumber = QtWidgets.QLCDNumber(self.widget_2 )
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lcdNumber.sizePolicy().hasHeightForWidth())
        self.lcdNumber.setSizePolicy(sizePolicy)
        self.lcdNumber.setStyleSheet(" QLCDNumber {\n"
"            background-color: transparent; /* Deep blue background */\n"
"            color: #ff8b00; /* Bright Aqua color for digits */\n"
"            border: 2px solid #5ce1e6; /* Lighter blue border */\n"
"            border-radius: 8px; /* Rounded corners */\n"
"            padding: 5px; /* Padding inside the widget */\n"
"        }")
        self.lcdNumber.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.lcdNumber.setFrameShadow(QtWidgets.QFrame.Raised)
        self.lcdNumber.setLineWidth(0)
        self.lcdNumber.setDigitCount(1)
        self.lcdNumber.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.lcdNumber.setObjectName("lcdNumber")
        self.horizontalLayout.addWidget(self.lcdNumber)
        self.lcdNumber_2 = QtWidgets.QLCDNumber(self.widget_2 )
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lcdNumber_2.sizePolicy().hasHeightForWidth())
        self.lcdNumber_2.setSizePolicy(sizePolicy)
        self.lcdNumber_2.setStyleSheet(" QLCDNumber {\n"
"            background-color: transparent; /* Deep blue background */\n"
"            color: #ff8b00; /* Bright Aqua color for digits */\n"
"            border: 2px solid #5ce1e6; /* Lighter blue border */\n"
"            border-radius: 8px; /* Rounded corners */\n"
"            padding: 5px; /* Padding inside the widget */\n"
"        }")
        self.lcdNumber_2.setDigitCount(1)
        self.lcdNumber_2.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.lcdNumber_2.setObjectName("lcdNumber_2")
        self.horizontalLayout.addWidget(self.lcdNumber_2)
        self.label_3 = QtWidgets.QLabel(self.widget_2 )
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(100*self.scale)
        self.label_3.setFont(font)
        self.label_3.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_3.setStyleSheet(" color: #ff8b00;")
        self.label_3.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.label_3.setFrameShadow(QtWidgets.QFrame.Plain)
        self.label_3.setLineWidth(2)
        self.label_3.setText(":")
        self.label_3.setTextFormat(QtCore.Qt.PlainText)
        self.label_3.setScaledContents(True)
        self.label_3.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop)
        self.label_3.setWordWrap(True)
        self.label_3.setIndent(0)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout.addWidget(self.label_3)
        self.lcdNumber_3 = QtWidgets.QLCDNumber(self.widget_2 )
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lcdNumber_3.sizePolicy().hasHeightForWidth())
        self.lcdNumber_3.setSizePolicy(sizePolicy)
        self.lcdNumber_3.setStyleSheet(" QLCDNumber {\n"
"            background-color: transparent; /* Deep blue background */\n"
"            color: #ff8b00; /* Bright Aqua color for digits */\n"
"            border: 2px solid #5ce1e6; /* Lighter blue border */\n"
"            border-radius: 8px; /* Rounded corners */\n"
"            padding: 5px; /* Padding inside the widget */\n"
"        }")
        self.lcdNumber_3.setDigitCount(1)
        self.lcdNumber_3.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.lcdNumber_3.setObjectName("lcdNumber_3")
        self.horizontalLayout.addWidget(self.lcdNumber_3)
        self.lcdNumber_4 = QtWidgets.QLCDNumber(self.widget_2 )
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lcdNumber_4.sizePolicy().hasHeightForWidth())
        self.lcdNumber_4.setSizePolicy(sizePolicy)
        self.lcdNumber_4.setStyleSheet(" QLCDNumber {\n"
"            background-color: transparent; /* Deep blue background */\n"
"            color: #ff8b00; /* Bright Aqua color for digits */\n"
"            border: 2px solid #5ce1e6; /* Lighter blue border */\n"
"            border-radius: 8px; /* Rounded corners */\n"
"            padding: 5px; /* Padding inside the widget */\n"
"        }")
        self.lcdNumber_4.setDigitCount(1)
        self.lcdNumber_4.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.lcdNumber_4.setObjectName("lcdNumber_4")
        self.horizontalLayout.addWidget(self.lcdNumber_4)
        self.widget_2.setLayout(self.horizontalLayout)
        self.set_lcd(0)
        
        
        
        
        
        self.frame_2 = QtWidgets.QFrame(self.centralwidget)
        self.frame_2.setGeometry(QtCore.QRect(200*self.scale, 720*self.scale, 650*self.scale, 415*self.scale))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy)
        # self.frame_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        # self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.gridLayout = QtWidgets.QGridLayout(self.frame_2)
        self.gridLayout.setObjectName("gridLayout")
        self.tableWidget_2 = QtWidgets.QTableWidget(self.frame_2)
        # self.tableWidget_2.hide()
        
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(25*self.scale)
        font.setBold(False)
        font.setItalic(False)
        # font.setWeight(75)
        self.tableWidget_2.setFont(font)
        self.tableWidget_2.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.tableWidget_2.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tableWidget_2.setAutoFillBackground(False)
        self.tableWidget_2.setStyleSheet("")
        self.tableWidget_2.setLineWidth(0)
        self.tableWidget_2.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableWidget_2.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableWidget_2.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.tableWidget_2.setAutoScroll(False)
        self.tableWidget_2.setAutoScrollMargin(0)
        self.tableWidget_2.setProperty("showDropIndicator", False)
        self.tableWidget_2.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tableWidget_2.setTextElideMode(QtCore.Qt.ElideLeft)
        self.tableWidget_2.setShowGrid(False)
        self.tableWidget_2.setGridStyle(QtCore.Qt.NoPen)
        self.tableWidget_2.setWordWrap(True)
        self.tableWidget_2.setCornerButtonEnabled(True)
        self.tableWidget_2.setRowCount(5)
        self.tableWidget_2.setColumnCount(2)
        self.tableWidget_2.setObjectName("tableWidget_2")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setVerticalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(22*self.scale)
        item.setFont(font)
        self.tableWidget_2.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(22*self.scale)
        item.setFont(font)
        self.tableWidget_2.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsDropEnabled|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsTristate)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(0, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(0, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(1, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(1, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(2, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(2, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(3, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(3, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(4, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(4, 1, item)

        self.tableWidget_2.horizontalHeader().setVisible(True)
        self.tableWidget_2.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidget_2.horizontalHeader().setDefaultSectionSize(350*self.scale)
        self.tableWidget_2.horizontalHeader().setMinimumSectionSize(120*self.scale)
        self.tableWidget_2.horizontalHeader().setStretchLastSection(False)
        self.tableWidget_2.verticalHeader().setVisible(False)
        self.tableWidget_2.verticalHeader().setCascadingSectionResizes(True)
        self.tableWidget_2.verticalHeader().setDefaultSectionSize(65*self.scale)
        self.tableWidget_2.verticalHeader().setMinimumSectionSize(50*self.scale)
        self.tableWidget_2.verticalHeader().setStretchLastSection(False)
        self.gridLayout.addWidget(self.tableWidget_2, 0, 0, 1, 1)
        self.gridLayout_3 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_3.setObjectName("gridLayout_3")
       #-----------------------------------------------------
        self.TimerGame = QTimer(MainWindow)
        self.TimerGame.setSingleShot(True)
        self.TimerGame.setTimerType(QtCore.Qt.PreciseTimer)
        self.TimerGame.timeout.connect(self.stop_game)    
       
        self.timer = QtCore.QTimer(MainWindow)
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self.update_lcd)        
        self.countdown_time = 0  # Countdown from 5 minutes (300 seconds)
        self.UpdateTable()
        # Start the GIF
        self.Background.setObjectName("Background")
        self.Background.raise_()
        # self.LineWidgetV.raise_()
        # self.LineWidgetH.raise_()
        self.widget_2.raise_()
        self.frame_2.raise_()
        self.tableWidget_2.raise_()
        # self.video.raise_()
        # self.dateTimeEdit.raise_()
        # self.widget.raise_()
        self.label.raise_()
        global list_players_score   
        list_players_score = [0,0,0,0,0,0,0]
        # self.label_win.raise_()
        # self.label_lose.raise_()
        # self.label_Score.raise_()
        MainWindow.setCentralWidget(self.centralwidget)
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        item = self.tableWidget_2.horizontalHeaderItem(0)
        item.setText(_translate("Home", "Player"))
        item = self.tableWidget_2.horizontalHeaderItem(1)
        item.setText(_translate("Home", "Score"))
    def UpdateTable(self):
        # Initialize an empty dictionary to store team data
        self.list_team = {}
        global list_players_name
        global list_players_score
        self.list_team = dict(zip(list_players_name, list_players_score))
        # Sort the list_team dictionary by score in descending order
        self.sorted_data = dict(sorted(self.list_team.items(), key=lambda item: item[1], reverse=True))

        # # Clear the table before updating
       
        print(self.sorted_data)
        # Loop over the top 5 items in the sorted data
        for i, (player, score) in enumerate(self.sorted_data.items()):
            if i >= 5:  # Stop after the top 5
                break

            
            # Create and set the team name item
            team_item = QtWidgets.QTableWidgetItem(list_players_name[i])
            team_item.setTextAlignment(QtCore.Qt.AlignCenter)  # Center align the text
            self.tableWidget_2.setItem(i, 0, team_item)
            # list_players_name.append(player)
            # Create and set the score item
            score_item = QtWidgets.QTableWidgetItem(str(score))
            score_item.setTextAlignment(QtCore.Qt.AlignCenter)  # Center align the text
            self.tableWidget_2.setItem(i, 1, score_item)

    
    def set_lcd(self, value):
        # Set the LCD number to the given value
        
        minutes = value // 60
        seconds = value % 60
        # Update LCD numbers
        self.lcdNumber.display(minutes // 10)  # First minute digit
        self.lcdNumber_2.display(minutes % 10)  # Second minute digit
        self.lcdNumber_3.display(seconds // 10)  # First second digit
        self.lcdNumber_4.display(seconds % 10)  # Second second digit
        
    
    def update_lcd(self):
        # self.label_Score.setText("Sticks :"+ str(scored))

        # Decrease countdown time by 1 second
        
         # Calculate minutes and seconds
        minutes = self.countdown_time // 60
        seconds = self.countdown_time % 60
        self.countdown_time += 1

        # Update LCD numbers
        self.lcdNumber.display(minutes // 10)  # First minute digit
        self.lcdNumber_2.display(minutes % 10)  # Second minute digit
        self.lcdNumber_3.display(seconds // 10)  # First second digit
        self.lcdNumber_4.display(seconds % 10)  # Second second digit
        
        if self.countdown_time == TimerValue//1000:
            # global scored
            # scored = self.countdown_time//3
            self.timer.stop()  # Stop the timer when it reaches zero
            self.set_lcd(TimerValue//1000)
            # if scored > 2:
            #     self.label_lose.hide()  # Hide the lose label
            #     self.label_win.show()    # Show the win label
            # else:
            #     self.label_win.hide()    # Hide the win label
            #     self.label_lose.show()    # Show the lose label

            self.lcdNumber.setStyleSheet(" QLCDNumber {\n"
"            background-color: transparent; /* Deep blue background */\n"
"            color: #f41c17; /* Bright Aqua color for digits */\n"
"            border: 2px solid #f41c17; /* Lighter blue border */\n"
"            border-radius: 8px; /* Rounded corners */\n"
"            padding: 5px; /* Padding inside the widget */\n"
"        }")
            self.lcdNumber_2.setStyleSheet(" QLCDNumber {\n"
"            background-color: transparent; /* Deep blue background */\n"
"            color: #f41c17; /* Bright Aqua color for digits */\n"
"            border: 2px solid #f41c17; /* Lighter blue border */\n"
"            border-radius: 8px; /* Rounded corners */\n"
"            padding: 5px; /* Padding inside the widget */\n"
"        }")
            self.lcdNumber_3.setStyleSheet(" QLCDNumber {\n"
"            background-color: transparent; /* Deep blue background */\n"
"            color: #f41c17; /* Bright Aqua color for digits */\n"
"            border: 2px solid #f41c17; /* Lighter blue border */\n"
"            border-radius: 8px; /* Rounded corners */\n"
"            padding: 5px; /* Padding inside the widget */\n"
"        }")
            self.lcdNumber_4.setStyleSheet(" QLCDNumber {\n"
"            background-color: transparent; /* Deep blue background */\n"
"            color: #f41c17; /* Bright Aqua color for digits */\n"
"            border: 2px solid #f41c17; /* Lighter blue border */\n"
"            border-radius: 8px; /* Rounded corners */\n"
"            padding: 5px; /* Padding inside the widget */\n"
"        }")
            
            self.label_3.setStyleSheet("color: #f41c17;")
            
            # self.label_Score.setText("Sticks :"+ str(scored))
            return

    def cancel_game(self):
        self.TimerGame.stop()
        self.set_lcd(0)
        global list_players_score   
        list_players_score = [0,0,0,0,0,0,0]
        self.countdown_time =0
        self.close()  # This will close the current window
        
    @pyqtSlot()
    def start_game(self):
        # self.Blink.start()
        global list_players_score   
        list_players_score = [0,0,0,0,0,0,0]
        global TimerValue
        try:
            with open("file2.txt", "r") as file:  # Open the file in read mode
                lines = file.readlines()  # Read all lines
                if lines:  # Check if there are any lines in the file
                    TimerValue = int(lines[-1].strip())  # Get the last line and convert to int
        except FileNotFoundError:
            print("file2.txt not found. Using default timer value.")
            TimerValue = 30000  # Set a default value if the file does not exist

        
        self.mqtt_thread.client.publish("CatchTheStick/game/start",1)
        self.TimerGame.start(TimerValue)  # 5000 milliseconds = 5 seconds
        self.timer.start(1000)  # Update every second
        print("start")
        self.play_audio()
    @pyqtSlot()
    def stop_game(self):
        global finalscore
        global teamName

        global list_players_score
        for i in range(7):
            finalscore += (list_players_score[i])
        self.save_final_score_to_csv(teamName, finalscore)

        print("stoped score")
        print(list_players_score)
        print(finalscore)
        # self.Blink.setPaused(True)
        # self.label_Score.setText("Sticks :"+ str(scored))
        self.mqtt_thread.client.publish("CatchTheStick/game/stop",1)
        self.mqtt_thread.unsubscribe_from_data_topics()
        self.play_audio_2()
        self.TimerGame.stop()
        
        self.list_team = {}
        global list_players_name
        self.list_team = dict(zip(list_players_name, list_players_score))
        # Sort the list_team dictionary by score in descending order
        self.sorted_data = dict(sorted(self.list_team.items(), key=lambda item: item[1], reverse=True))

        # # Clear the table before updating
       
        print(self.sorted_data)
        # Loop over the top 5 items in the sorted data
        for i, (player, score) in enumerate(self.sorted_data.items()):
            if i >= 5:  # Stop after the top 5
                break
           
            # Create and set the team name item
            team_item = QtWidgets.QTableWidgetItem(list_players_name[i])
            team_item.setTextAlignment(QtCore.Qt.AlignCenter)  # Center align the text
            self.tableWidget_2.setItem(i, 0, team_item)
            # list_players_name.append(player)
            # Create and set the score item
            score_item = QtWidgets.QTableWidgetItem(str(score))
            score_item.setTextAlignment(QtCore.Qt.AlignCenter)  # Center align the text
            self.tableWidget_2.setItem(i, 1, score_item)
        
        
        
        # self.timer.stop()
        # self.video.stop()
        
        # client.publish( "CatchTheStick/game/Deactivate", "1")
        # timer  
        print("stop")
        QtCore.QTimer.singleShot(5000,self.deactivate)
    def save_final_score_to_csv(self, team_name, final_score):
        # Get the current date and time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Define the CSV file path
        csv_file_path = "Falcon_scores.csv"  # Change this to your desired file path
        print([team_name, final_score, current_time])
        # Append the data to the CSV file
        try:
            # Append the data to the CSV file
            with open(csv_file_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([team_name, final_score, current_time])  # Write team name, final score, and timestamp
            print("Score saved successfully.")  # Debug: Confirmation message

        except Exception as e:
            print(f"An error occurred while saving the score to CSV: {e}")  # Error handling
    @pyqtSlot()   
    def deactivate(self):
        self.mqtt_thread.client.publish("CatchTheStick/game/Deactivate",1)
        print("deactivate")
    @pyqtSlot(list)
    def ReceiveData(self, data):
        # put data in table
        print(data)
        # Example data format: ['CatchTheStick/camera/0', '1']
        
        # Extract the camera index from the topic
        topic_parts = data[0].split('/')
        if len(topic_parts) < 3 or topic_parts[1] != "camera":
            print("Invalid topic format")
            return

        index = int(topic_parts[2])  # Get the camera index
        print(f"Camera Index: {index}")
        global list_players_score
        # Get the score from the data
        score = data[1]
        list_players_score[index] = int(score)  # Update the score for the corresponding player
        print(list_players_score)

        # Check if tableWidget_2 is valid before using it
        if self.tableWidget_2 is None:
            print("Error: tableWidget_2 is None")
            return
        if not self.tableWidget_2.isVisible():
            print("Error: tableWidget_2 is not visible")
            return

        # Put the score in the table
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        item.setText(score) 
        self.tableWidget_2.setItem(index, 1, item)
    
    @pyqtSlot()
    def restart_game(self):
        # self.Blink.start()
        self.TimerGame.start(TimerValue)  # 5000 milliseconds = 5 seconds
        print("restart")
        
    def load_custom_font(self, font_path):
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            print(f"Failed to load font: {font_path}")
            return "Default"  # Return a default font name in case of failure
        font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            font_family = font_families[0]
            print(f"Font Family Loaded: {font_family}")  # Print to verify the font family name
            return font_family
        else:
            print(f"No font families found for: {font_path}")
            return "Default"
    
    
    def closeEvent(self, event):
            print("close in active screen")
            if hasattr(self, 'movie'):
                self.movie.stop()
                self.movie.setCacheMode(QMovie.CacheNone)
                self.movie = None
            
            # If you're using a QLabel to display the movie, clear it
            if hasattr(self, 'Background'):
                self.Background.clear()
            # close all widget and threads right
            # self.mqtt_thread.client.disconnect()
            self.timer.stop()
            # self.video.close()
            self.close()
            event.accept()
            super().closeEvent(event)
 
     
 
class Home_screen(QtWidgets.QMainWindow):
    def load_custom_font(self, font_path):
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            print(f"Failed to load font: {font_path}")
            return "Default"  # Return a default font name in case of failure
        font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            font_family = font_families[0]
            print(f"Font Family Loaded: {font_family}")  # Print to verify the font family name
            return font_family
        else:
            print(f"No font families found for: {font_path}")
            return "Default"
    
    def play_audio(self):
        """Load and play the audio file."""
        audio_file = "mp3/2066.wav"  # Change to your audio file path
        absolute_path = os.path.abspath(audio_file)
        print("Absolute path:", absolute_path)
        self.player.setMedia(QMediaContent(QtCore.QUrl.fromLocalFile(absolute_path)))
        self.player.setVolume(100)  # Set volume (0-100)
        self.player.play()  # Start playing the audio
        
        # Connect the mediaStatusChanged signal to stop playback when finished
        self.player.mediaStatusChanged.connect(self.check_media_status)
        
    def play_audio_2(self):
        """Load and play the audio file."""
        audio_file = "mp3/2066.wav"  # Change to your audio file path
        absolute_path = os.path.abspath(audio_file)
        print("Absolute path:", absolute_path)
        self.player.setMedia(QMediaContent(QtCore.QUrl.fromLocalFile(absolute_path)))
        self.player.setVolume(100)  # Set volume (0-100)
        self.player.play()  # Start playing the audio
        
        # Connect the mediaStatusChanged signal to stop playback when finished
        self.player.mediaStatusChanged.connect(self.check_media_status)
        

    def check_media_status(self, status):
        """Check media status and stop playback if finished."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.stop()  # Stop playback when audio finishes
        
    
    def setupUi(self, Home):
        Home.setObjectName("Home")
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        Home.setLayoutDirection(QtCore.Qt.LeftToRight)
        Home.setAutoFillBackground(False)
        self.player = QMediaPlayer()

        Home.setStyleSheet("/* Base Styling for Application */\n"
"* {\n"
"    color: #ffffff;  /* Default text color for dark theme */\n"
"}\n"
"\n"
"/* General Background */\n"
"QWidget {\n"
"    background-color: transparent;  /* Transparent background for all widgets */\n"
"}\n"
"\n"
"/* QPushButton Styling */\n"
"QPushButton {\n"
"    background-color: #2e4053;  /* Darker muted blue background */\n"
"    color: #ffffff;  /* White text color */\n"
"    border: 1px solid #3b5998;  /* Slightly lighter border */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 8px 16px;  /* Padding inside the button */\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #4c669f;  /* Medium muted blue on hover */\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #1c2833;  /* Even darker muted blue when pressed */\n"
"}\n"
"\n"
"/* QLabel Styling */\n"
"QLabel {\n"
"    color: #b3e5fc;  /* White text color */\n"
"}\n"
"\n"
"/* QLineEdit Styling */\n"
"QLineEdit {\n"
"    border: 1px solid #3b5998;  /* Border color */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 4px 8px;  /* Padding inside the line edit */\n"
"    background-color: #2e4053;  /* Darker muted blue background */\n"
"    color: #ffffff;  /* White text color */\n"
"}\n"
"\n"
"/* QTableWidget Styling */\n"
"QTableWidget {\n"
"    background-color: transparent;  /* Transparent background */\n"
"    color: #ffffff;  /* White text color */\n"
"    gridline-color: #3b5998;  /* Medium muted blue gridline color */\n"
"    selection-background-color: transparent;  /* Transparent selection background */\n"
"    selection-color: #ffffff;  /* White selection text color */\n"
"    border: 1px solid #3b5998;  /* Border around the table */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 4px;  /* Padding inside the table */\n"
"    margin: 8px;  /* Margin around the table */\n"
"}\n"
"\n"
"QHeaderView::section { \n"
"    background-color: #001f3f;  /* Dark blue background for header sections */\n"
"    color: #ffffff;  /* White text color for header sections */\n"
"    padding: 5px;  /* Padding for header sections */\n"
"    border: 1px solid #3b5998;  /* Border color to match table */\n"
"}\n"
"\n"
"QHeaderView {\n"
"    background-color: transparent;  /* Transparent background */\n"
"}\n"
"\n"
"QTableCornerButton::section {\n"
"    background-color: transparent;  /* Transparent background */\n"
"}\n"
"\n"
"QTableWidget::item {\n"
"    padding: 4px;  /* Padding for items */\n"
"    border: none;  /* No border for items */\n"
"}\n"
"\n"
"QTableWidget::item:selected {\n"
"    background-color: transparent;  /* Transparent background for selected items */\n"
"    color: #2e4053;  /* Blue text color for selected items */\n"
"}\n"
"\n"
"QTableWidget::item:hover {\n"
"    background-color: #001f3f;  /* Dark blue background on hover */\n"
"}\n"
"\n"
"/* QScrollBar Styling */\n"
"QScrollBar:vertical, QScrollBar:horizontal {\n"
"    background-color: #1c2833;  /* Deep muted blue background for scrollbar */\n"
"    border: 1px solid #3b5998;  /* Border color */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"}\n"
"\n"
"QScrollBar::handle:vertical, QScrollBar::handle:horizontal {\n"
"    background-color: #2e4053;  /* Darker muted blue handle */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"}\n"
"\n"
"QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {\n"
"    background-color: #4c669f;  /* Medium muted blue handle on hover */\n"
"}\n"
"\n"
"/* QTabWidget Styling */\n"
"QTabWidget::pane {\n"
"    border: 1px solid #3b5998;  /* Border around tabs */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"}\n"
"\n"
"QTabBar::tab {\n"
"    background-color: #2e4053;  /* Dark blue tab background */\n"
"    color: #ffffff;  /* White text color */\n"
"    border: 1px solid #3b5998;  /* Border color */\n"
"    border-radius: 4px;  /* Rounded corners */\n"
"    padding: 8px 16px;  /* Padding inside tabs */\n"
"}\n"
"\n"
"QTabBar::tab:selected {\n"
"    background-color: #4c669f;  /* Medium muted blue background for selected tab */\n"
"    color: #ffffff;  /* White text color for selected tab */\n"
"}\n"
"\n"
"/* Circular Countdown Timer Styling */\n"
".circular-countdown {\n"
"    border: 8px solid #1c2833;  /* Deep muted blue background for the circle */\n"
"    border-radius: 50%;  /* Makes the border circular */\n"
"    width: 100px;  /* Width of the countdown circle */\n"
"    height: 100px;  /* Height of the countdown circle */\n"
"    background-color: #1c2833;  /* Deep muted blue background */\n"
"    color: #ffffff;  /* White text color */\n"
"    display: flex;  /* Center the text inside */\n"
"    align-items: center;  /* Center vertically */\n"
"    justify-content: center;  /* Center horizontally */\n"
"    font-size: 24px;  /* Text size */\n"
"    position: relative;  /* For positioning overlay */\n"
"}\n"
"\n"
"/* Styling for Countdown Progress */\n"
".circular-countdown.progress {\n"
"    border-color: #3b5998;  /* Medium muted blue color during progress */\n"
"}\n"
"\n"
"/* Styling for Countdown Finished */\n"
".circular-countdown.finished {\n"
"    border-color: #32cd32;  /* Green color when finished */\n"
"}\n"
"\n"
"/* Optional: Styling for Overlay Background Widget */\n"
".circular-countdown-background {\n"
"    position: absolute;  /* Position it on top of the countdown */\n"
"    top: 0;\n"
"    left: 0;\n"
"    width: 100%;\n"
"    height: 100%;\n"
"    background-color: rgba(0, 0, 0, 0.5);  /* Semi-transparent dark overlay */\n"
"    border-radius: 50%;  /* Match the circular shape */\n"
"}\n"
"")
        self.centralwidget = QtWidgets.QWidget(Home)
        # print(QtWidgets.QDesktopWidget().screenGeometry())
        print(Home.geometry().width())
        self.font_family = self.load_custom_font("Assets/Fonts/GOTHIC.TTF")  # Update with the correct path
        self.font_family_good = self.load_custom_font("Assets/Fonts/good_times_rg.ttf")  # Update with the correct path
        
        # self.scaleFactor = 
        # if QtWidgets.QDesktopWidget().screenGeometry().width() > 1920:
        if Home.geometry().width() > 1080:
                self.movie= QMovie("Assets/1k/portrait/portrait_CatchTheStick_intro.gif")
                self.movie.setCacheMode(QMovie.CacheAll)    
                print("1")
                self.scale = 2
                global scaled
                scaled = 2
        else:
                self.movie= QMovie("Assets/1k/portrait/portrait_CatchTheStick_intro.gif")
                self.movie.setCacheMode(QMovie.CacheAll)    
                print("2")
                self.scale = 1  
                scaled =1 
        self.Background = QtWidgets.QLabel(self.centralwidget)
        self.Background.setScaledContents(True)
        # self.Background.setGeometry(0, 0, QtWidgets.QDesktopWidget().screenGeometry().width(), QtWidgets.QDesktopWidget().screenGeometry().height())
        self.Background.setGeometry(0, 0, Home.geometry().width(), Home.geometry().height())
        self.Background.setText("")
        self.Background.setMovie(self.movie)
        self.Background.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # Start the GIF
        self.frame_2 = QtWidgets.QFrame(self.centralwidget)
        self.frame_2.setGeometry(QtCore.QRect(200*self.scale, 565*self.scale, 650*self.scale, 415*self.scale))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy)
        # self.frame_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        # self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.gridLayout = QtWidgets.QGridLayout(self.frame_2)
        self.gridLayout.setObjectName("gridLayout")
        self.tableWidget_2 = QtWidgets.QTableWidget(self.frame_2)
        self.tableWidget_2.hide()
        
        
        
        
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        palette = QtGui.QPalette()

       

        self.centralwidget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.centralwidget.setAutoFillBackground(False)
        self.centralwidget.setStyleSheet("")
        self.centralwidget.setObjectName("centralwidget")
        
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableWidget_2.sizePolicy().hasHeightForWidth())
        self.tableWidget_2.setSizePolicy(sizePolicy)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(102, 171, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(65, 142, 235))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Midlight, brush)   
        brush = QtGui.QBrush(QtGui.QColor(14, 57, 108))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(19, 75, 144))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.HighlightedText, brush)
        brush = QtGui.QBrush(QtGui.QColor(141, 184, 235))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(102, 171, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(65, 142, 235))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(14, 57, 108))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(19, 75, 144))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.HighlightedText, brush)
        brush = QtGui.QBrush(QtGui.QColor(28, 113, 216))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.tableWidget_2.setPalette(palette)
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(25*self.scale)
        font.setBold(False)
        font.setItalic(False)
        # font.setWeight(75)
        self.tableWidget_2.setFont(font)
        self.tableWidget_2.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.tableWidget_2.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tableWidget_2.setAutoFillBackground(False)
        self.tableWidget_2.setStyleSheet("")
        self.tableWidget_2.setLineWidth(0)
        self.tableWidget_2.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableWidget_2.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableWidget_2.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.tableWidget_2.setAutoScroll(False)
        self.tableWidget_2.setAutoScrollMargin(0)
        self.tableWidget_2.setProperty("showDropIndicator", False)
        self.tableWidget_2.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tableWidget_2.setTextElideMode(QtCore.Qt.ElideLeft)
        self.tableWidget_2.setShowGrid(False)
        self.tableWidget_2.setGridStyle(QtCore.Qt.NoPen)
        self.tableWidget_2.setWordWrap(True)
        self.tableWidget_2.setCornerButtonEnabled(True)
        self.tableWidget_2.setRowCount(5)
        self.tableWidget_2.setColumnCount(2)
        self.tableWidget_2.setObjectName("tableWidget_2")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setVerticalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget_2.setVerticalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(22*self.scale)
        item.setFont(font)
        self.tableWidget_2.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(22*self.scale)
        item.setFont(font)
        self.tableWidget_2.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsDropEnabled|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsTristate)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(0, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(0, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(1, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(1, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(2, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(2, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(3, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(3, 1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(4, 0, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.tableWidget_2.setItem(4, 1, item)

        self.tableWidget_2.horizontalHeader().setVisible(True)
        self.tableWidget_2.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidget_2.horizontalHeader().setDefaultSectionSize(300*self.scale)
        self.tableWidget_2.horizontalHeader().setMinimumSectionSize(100*self.scale)
        self.tableWidget_2.horizontalHeader().setStretchLastSection(False)
        self.tableWidget_2.verticalHeader().setVisible(False)
        self.tableWidget_2.verticalHeader().setCascadingSectionResizes(True)
        self.tableWidget_2.verticalHeader().setDefaultSectionSize(65*self.scale)
        self.tableWidget_2.verticalHeader().setMinimumSectionSize(50*self.scale)
        self.tableWidget_2.verticalHeader().setStretchLastSection(False)
        self.gridLayout.addWidget(self.tableWidget_2, 0, 0, 1, 1)
        self.gridLayout_3 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_3.setObjectName("gridLayout_3")
        # self.dateTimeEdit = QtWidgets.QDateTimeEdit(self.centralwidget)
        # self.dateTimeEdit.setGeometry(QtCore.QRect(706*self.scale, 950*self.scale, 506*self.scale, 40*self.scale))
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        # sizePolicy.setHorizontalStretch(1)
        # sizePolicy.setVerticalStretch(1)
        # sizePolicy.setHeightForWidth(self.dateTimeEdit.sizePolicy().hasHeightForWidth())
        # self.dateTimeEdit.setSizePolicy(sizePolicy)
        # font = QtGui.QFont()
        # font.setPointSize(25*self.scale)
        # self.dateTimeEdit.setFont(font)
        # self.dateTimeEdit.setFocusPolicy(QtCore.Qt.NoFocus)    
        # self.dateTimeEdit.setAutoFillBackground(False)
        # self.dateTimeEdit.setStyleSheet("Color: #5ce1e6;")
        # self.dateTimeEdit.setAlignment(QtCore.Qt.AlignCenter)
        # self.dateTimeEdit.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        # self.dateTimeEdit.setDateTime(QtCore.QDateTime(QtCore.QDate(2024, 7, 22), QtCore.QTime(0, 0, 0)))
        # self.dateTimeEdit.setDisplayFormat("dd MMM yyyy - hh:mm AP")
        # self.dateTimeEdit.setTimeSpec(QtCore.Qt.LocalTime)
        # current_date_time = QtCore.QDateTime.currentDateTime()
        # self.dateTimeEdit.setDateTime(current_date_time)
        # self.dateTimeEdit.setObjectName("dateTimeEdit")
        Home.setCentralWidget(self.centralwidget)
        self.timer = QTimer(Home)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.showTable)
        self.timer.start(11000)
        self.movie.start()
        # self.player = QMediaPlayer()
        
        # self.player.setMedia(QMediaContent(QUrl.fromLocalFile("Assets/test.mp3")))
        # self.player.setVolume(100)  # Set volume to maximum
        # self.player.play()
        self.play_audio()
        self.timer2 = QTimer(Home)
        self.timer2.setTimerType(Qt.PreciseTimer)
        self.timer2.timeout.connect(self.Inactive)
        self.timer2.start(13000)
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(22*self.scale)
        font.setBold(True)
        font.setWeight(75)
        self.tableWidget_2.setFont(font)
        self.retranslateUi(Home)
        # self.UpdateTable()
        # raise()
        
        QtCore.QMetaObject.connectSlotsByName(Home)             
    def retranslateUi(self, Home):
        _translate = QtCore.QCoreApplication.translate
        Home.setWindowTitle(_translate("Home", "MainWindow"))
        self.tableWidget_2.setSortingEnabled(True)
        item = self.tableWidget_2.verticalHeaderItem(0)
        item.setText(_translate("Home", "Rank 1"))
        item = self.tableWidget_2.verticalHeaderItem(1)
        item.setText(_translate("Home", "Rank 2"))
        item = self.tableWidget_2.verticalHeaderItem(2)
        item.setText(_translate("Home", "Rank 3"))
        item = self.tableWidget_2.verticalHeaderItem(3)
        item.setText(_translate("Home", "Rank 4"))
        item = self.tableWidget_2.verticalHeaderItem(4)
        item.setText(_translate("Home", "Rank 5"))
        item = self.tableWidget_2.horizontalHeaderItem(0)
        item.setText(_translate("Home", "Team"))
        item = self.tableWidget_2.horizontalHeaderItem(1)
        item.setText(_translate("Home", "Score"))
        __sortingEnabled = self.tableWidget_2.isSortingEnabled()
        self.tableWidget_2.setSortingEnabled(False)
        item = self.tableWidget_2.item(0, 0)
        item.setText(_translate("Home", "Team 1"))
        item = self.tableWidget_2.item(0, 1)
        item.setText(_translate("Home", "5"))
        item = self.tableWidget_2.item(1, 0)
        item.setText(_translate("Home", "Team 2"))
        item = self.tableWidget_2.item(1, 1)
        item.setText(_translate("Home", "6"))
        item = self.tableWidget_2.item(2, 0)
        item.setText(_translate("Home", "Team 3"))
        item = self.tableWidget_2.item(2, 1)
        item.setText(_translate("Home", "548"))
        item = self.tableWidget_2.item(3, 0)
        item.setText(_translate("Home", "Team 5"))
        item = self.tableWidget_2.item(3, 1)
        item.setText(_translate("Home", "2"))
        item = self.tableWidget_2.item(4, 0)
        item.setText(_translate("Home", "Team 55"))
        item = self.tableWidget_2.item(4, 1)
        item.setText(_translate("Home", "55"))
        # self.label_4.setText(_translate("Home", "Designed By www.uxe.ai"))

    
    def showTable(self):
        self.tableWidget_2.show()
        self.UpdateTable()
        
    def hideTable(self):
        self.tableWidget_2.hide()
    def UpdateTable(self):
        # Initialize an empty dictionary to store team data
        global list_top5_CatchTheStick
        
        # Sort the list_team dictionary by score in descending order
        sorted_data = sorted(list_top5_CatchTheStick, key=lambda item: item[1], reverse=True)
        print(sorted_data)

        # # Clear the table before updating
        # self.tableWidget_2.clearContents()
        # self.tableWidget_2.setRowCount(0)  # Make sure to reset row count

        # Loop over the top 5 items in the sorted data
        for i, (team, score) in enumerate(sorted_data):
            if i >= 5:  # Stop after the top 5
                break

            # # Insert a new row
            # self.tableWidget_2.insertRow(i)

            # Create and set the team name item
            team_item = QtWidgets.QTableWidgetItem(team)
            team_item.setTextAlignment(QtCore.Qt.AlignCenter)  # Center align the text
            self.tableWidget_2.setItem(i, 0, team_item)

            # Create and set the score item
            score_item = QtWidgets.QTableWidgetItem(str(score))
            score_item.setTextAlignment(QtCore.Qt.AlignCenter)  # Center align the text
            self.tableWidget_2.setItem(i, 1, score_item)
 

    def Inactive(self):
        self.timer2.stop()
        if scaled == 1:
            self.movie =QMovie("Assets/1k/portrait/portrait_CatchTheStick_inActive.gif")
            self.movie.setCacheMode(QMovie.CacheAll)    
            
        else:
            self.movie =QMovie("Assets/1k/portrait/portrait_CatchTheStick_inActive.gif")
            self.movie.setCacheMode(QMovie.CacheAll)    
        self.Background.setMovie(self.movie)
        self.movie.start()
        self.showTable()
        global homeOpened
        homeOpened = True
    
    def closeEvent(self, event):
        if hasattr(self, 'movie'):
            self.movie.stop()
            self.movie.setCacheMode(QMovie.CacheNone)
            self.movie = None
        
        # If you're using a QLabel to display the movie, clear it
        if hasattr(self, 'Background') and isinstance(self.Background, QLabel):
            self.Background.clear()
        self.tableWidget_2.close()
        self.tableWidget_2.deleteLater()
        #close all widget
        self.close()       
        event.accept()
        super().closeEvent(event)   
class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize memory usage monitoring
        # self.process = psutil.Process(os.getpid())
        self.sized = QtWidgets.QDesktopWidget().screenGeometry()
        # self.sized = QSize(2160,3840)
        # Start by displaying the home screen
        # self.hang_game_id = "1f28aa60-beae-4302-af3c-74223c7201ab"
        self.hang_game_id = "878f6f84-7d65-4ecc-9450-872ca7e1a3f3"
        self.ui_final = Final_Screen()
        self.ui_home = Home_screen()  # Assuming you have a Ui_Tabel class for the tabel screen
        self.ui_active = Active_screen()
        self.mainWindow = QtWidgets.QMainWindow()

        #activate_signal
        # self.ui_active.mqtt_thread.activate_signal.connect(self.start_Active_screen)
        self.ui_active.mqtt_thread.deactivate_signal.connect(
            lambda :(
                setattr(self.game_manager, 'submit_score_flag', True)
            )
        )
        self.mainWindow = QtWidgets.QMainWindow()
        self.mainWindow.setObjectName("Home")
        # change its title
        self.mainWindow.setWindowTitle("HomeOBB")
        self.mainWindow.setFixedSize(self.sized.width(), self.sized.height())
        self.mainWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint)        
        
        
        email = "eaa25admin@gmail.com"
        password = "qhv#1kGI$"
        self.game_manager = GameManager(email,password, self.hang_game_id)   
        # token = self.game_manager.get_token(email, password)
        # print(token)
        self.game_manager.init_signal.connect(self.start_Active_screen)
        self.game_manager.start_signal.connect(lambda: (
            self.ui_active.mqtt_thread.subscribe_to_data_topics(),
            self.ui_active.start_game()
            )
        )
        self.game_manager.cancel_signal.connect(
            lambda: (
            self.ui_active.mqtt_thread.client.publish("CatchTheStick/game/stop",1),
            self.ui_active.mqtt_thread.unsubscribe_from_data_topics(),
            self.ui_active.cancel_game(),
            # self.ui_active.close(),
            self.start_Home_screen()
            )
        )
        self.game_manager.submit_signal.connect(
                                lambda :(
                                    self.start_final_screen()
                                ))
        self.start_Home_screen()
        QtCore.QTimer.singleShot(15000, lambda: (    
            # self.game_manager.init_game(self.hang_game_id)
            self.game_manager.start()
        ))
        self.mainWindow.showFullScreen()
                
    def start_Home_screen(self):
        global list_players_score
        global list_players_name
        global finalscore, homeOpened
        list_players_score = [0,0,0,0,0,0,0]
        # list_players_name.clear()
        
        finalscore = 0
        self.ui_home.setupUi(self.mainWindow)
        # run  init game after 2 second
       
        quit_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence('q'), self.mainWindow)
        quit_shortcut.activated.connect(self.close_application)

    def start_Active_screen(self):
        if hasattr(self, 'ui_home') and self.ui_home is not None and self.ui_home.isVisible():  # Check if ui_home exists and is visible
            self.ui_home.close()  # Close the ui_home window
        self.ui_active.setupUi(self.mainWindow)
        # self.game_manager.start_game(self.hang_game_id)
        # QtCore.QTimer.singleShot(5000, lambda: (
        #     self.ui_active.start_game(),
        #     self.ui_active.mqtt_thread.subscribe_to_data_topics()
        #     ))


        
        quit_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence('q'), self.mainWindow)
        quit_shortcut.activated.connect(self.close_application)

    def start_final_screen(self):
        if hasattr(self, 'ui_active') and self.ui_active is not None and self.ui_active.isVisible():  # Check if ui_active exists and is visible
            self.ui_active.close()  # Close the ui_active window
        self.ui_final.setupUi(self.mainWindow)
        
        try:
            with open("file.txt", "r") as file:  # Open the file in read mode
                lines = file.readlines()  # Read all lines
                if lines:  # Check if there are any lines in the file
                    final_screen_timer_idle = int(lines[-1].strip())  # Get the last line and convert to int
        except FileNotFoundError:
            print("file.txt not found. Using default timer value.")
            final_screen_timer_idle = 30000  # Set a default value if the file does not exist

        
        QtCore.QTimer.singleShot(final_screen_timer_idle, lambda: (
            (self.ui_final.close() if hasattr(self, 'ui_final') and self.ui_final is not None and self.ui_final.isVisible() else None),
            self.start_Home_screen() if hasattr(self, 'ui_final') and self.ui_final is not None and not self.ui_final.isVisible() else None
        ))
        # self.game_manager.submit_score_flag = False

        quit_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence('q'), self.mainWindow)
        quit_shortcut.activated.connect(self.close_application)



    def close_application(self):
        # Close all windows
        # for widget in [self.home_screen, getattr(self, 'tabel', None), getattr(self, 'main_window', None)]:
        #     if widget:
        #         widget.close()
        QtWidgets.QApplication.quit()
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PyQt5.QtCore import QThread, pyqtSignal
import time

class GameManager(QThread):
    init_signal = pyqtSignal()
    start_signal = pyqtSignal()
    cancel_signal = pyqtSignal()  # New signal for cancellation
    submit_signal = pyqtSignal()
    
    def __init__(self, email, password, game_id):
        super().__init__()
        self.base_url = "https://dev-eaa25-api-hpfyfcbshkabezeh.uaenorth-01.azurewebsites.net"
        self.email = "eaa25admin@gmail.com"
        self.password = "qhv#1kGI$"
        # self.game_id = "1f28aa60-beae-4302-af3c-74223c7201ab"
        self.game_id = "878f6f84-7d65-4ecc-9450-872ca7e1a3f3"
        self.token = None
        self.headers = {}
        self.game_result_id = None
        # self.polling_interval = 3  # seconds
        self.submit_score_flag = False
        self.playStatus = True
        self.started_flag = False
        self.cancel_flag = False
        self.game_done = True
        
        
    def run(self):
        while self.playStatus:
            if not self.get_token(self.email, self.password):
                continue
            if not self.init_game(self.game_id):
                return
            if not self.start_game(self.game_result_id):
                return
            print("cancelled")
            if self.cancel_flag == True:
                continue
            if not self.submit_score():
                continue

    def get_token(self, email, password):
        url = f"{self.base_url}/login2"
        data = {"email": email, "password": password}

        try:
            response = requests.post(url, json=data)
            response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        
            token_data = response.json()
            self.token = token_data.get('data').get('token')
            if self.token:
                self.headers = {"Authorization": f"Bearer {self.token}"}
                return True
        except ConnectionError:
            print("Error: Unable to connect to the internet. Please check your connection.")
        except Timeout:
            print("Error: The request timed out. Please try again later.")
        except RequestException as e:
            print(f"An error occurred while trying to get the token: {e}")  # Catch all other request-related exceptions
        except Exception as e:
            print(f"An unexpected error occurred: {e}")  # Catch any other exceptions

        return False  # Return False if the token could not be retrieved
       
    def closeEvent(self, event):
        # self.submit_score()
        event.accept()

    def closeEvent(self, event):
        # self.submit_score()
        event.accept()
        
    

    def init_game(self, game_id):
        url = f"{self.base_url}/game-result?status=initiated&load_participant=true&gameID={game_id}&limit=1"
        
        
        while True:
            try:
                print("Initializing game...")
                self.started_flag = False
                self.cancel_flag = False
                response = None
                response = requests.get(url, headers=self.headers,timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    print(data)
                    if data.get('data') and len(data.get('data')) > 0:
                        self.game_result_id = data.get('data')[0].get('id')
                        print(f"Game Result ID: {self.game_result_id}")
                        global teamName, list_players_name, list_players_id
                        teamName = data.get('data')[0].get('name')
                        # list_players_name = [player.get('name') for player in data.get('data')[0].get('nodeIDs')]
                        list_players_id = [player.get('userID') for player in data.get('data')[0].get('nodeIDs')]
                        print(f"Team Name: {teamName}, Players: {list_players_name}")
                        global homeOpened
                        if homeOpened :
                            homeOpened = False
                            self.init_signal.emit()
                            return True
                else:
                    print(f" Response Error: {response.status_code}")
                    print(f"{response.json()}")
                    pass
            except ConnectionError:
                print("Error: Unable to connect to the internet. Please check your connection.")
                if response is not None:
                    print(f"Response: {response.json()}")
            except Timeout:
                print("Error: The request timed out. Please try again later.")
                if response is not None:
                    print(f"Response: {response.json()}")
            except RequestException as e:
                print(f"An error occurred while getting playing status: {e}")  # Catch all other request-related exceptions
                if response is not None:
                    print(f"Response: {response.json()}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")  # Catch any other exceptions
                if response is not None:
                    print(f"Response: {response.json()}")
        return False

    def start_game(self, game_result_id):
        url = f"{self.base_url}/game-result/{game_result_id}"
        while True:
            try:
                response = None
                response = requests.get(url, headers=self.headers,timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    print(data)
                    if data.get('data') and len(data.get('data')) > 0:
                        status = data.get('data').get('status')
                        print(status)
                        if self.submit_score_flag == True :
                            return True
                        
                        elif status == "playing" and self.started_flag == False  :
                            self.start_signal.emit()  # Emit start signal if playing
                            self.started_flag = True 
                        elif status == "playing" and self.started_flag == True:
                            continue
                        elif status == "cancel":
                            print(" status cancel ")
                            self.cancel_flag = True
                            self.cancel_signal.emit()  # Emit cancel signal if canceled
                            return True   
                else:
                    print(f"Error: {response.status_code}")
                # time.sleep(self.polling_interval)  # Wait before the next poll
            except ConnectionError:
                print("Error: Unable to connect to the internet. Please check your connection.")
                if response is not None:
                    print(f"Response: {response.json()}")
            except Timeout:
                print("Error: The request timed out. Please try again later.")
                if response is not None:
                    print(f"Response: {response.json()}")
            except RequestException as e:
                print(f"An error occurred while getting playing status: {e}")  # Catch all other request-related exceptions
                if response is not None:
                    print(f"Response: {response.json()}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")  # Catch any other exceptions
                if response is not None:
                    print(f"Response: {response.json()}")
        return False

    def submit_score(self):
        score_submitted = False 
        while True:
            if self.submit_score_flag == False :
                continue
            if self.cancel_flag == True :
                return False
            
            if self.submit_score_flag and self.cancel_flag == False :
                url = f"{self.base_url}/game-result/scoring"
                global list_players_score, list_players_id, finalscore,list_top5_CatchTheStick
                individual_scores = [{"userID": list_players_id[i], "nodeID": i + 1, "score": list_players_score[i]} for i in range(len(list_players_id))]
                data = {"gameResultID": self.game_result_id, "individualScore": individual_scores}
                print(data)
                try:
                    response = None
                    response = requests.post(url, json=data, headers=self.headers,timeout=20)
                    if response.status_code == 200:
                        print("Scores submitted successfully.")
                        self.playStatus = True
                        score_submitted = True
                        list_top5_CatchTheStick.clear()
                        
                            
                       
                    else:
                        print(f"Failed to submit scores. Status Code: {response.status_code}")

                except ConnectionError:
                    print("Error: Unable to connect to the internet. Please check your connection.")
                    if response is not None:
                        print(f"Response: {response.json()}")
                except Timeout:
                    print("Error: The request timed out. Please try again later.")
                    if response is not None:
                        print(f"Response: {response.json()}")
                except RequestException as e:
                    print(f"An error occurred while getting submitting status: {e}")  # Catch all other request-related exceptions
                    if response is not None:
                        print(f"Response: {response.json()}")
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")  # Catch any other exceptions
                    if response is not None:
                        print(f"Response: {response.json()}")
        
                else:
                    print(f" EXception Error: {response.status_code}")
                    print(f"{response.json()}")
                    pass
                if score_submitted == True:
                    try :
                        base_url = "https://dev-eaa25-api-hpfyfcbshkabezeh.uaenorth-01.azurewebsites.net/leaderboard/dashboard/based"
                        params = {
                            "source": "game",
                            "nameGame": "Falcon's Grasp"
                        }
                        response = None
                        response = requests.get(base_url, params=params,timeout=12)
                        if response.status_code == 200:
                            data = response.json()
                            print(f"Leaderboard for Catch Stick:", data)

                            # Extract team names and scores into a list of tuples
                            if 'data' in data and len(data['data']) > 0:
                                teams = data['data'][0].get('list', [])
                                team_scores = [(team['name'][:10], team['total_score']) for team in teams]

                                # Fill the appropriate list based on the game name
                                list_top5_CatchTheStick.extend(team_scores[:5])  # Get top 5
                            self.submit_score_flag = False
                            self.submit_signal.emit()
                            return False
                        else:
                            print(f"Failed to retrieve leaderboard for Catch Stick. Status Code: {response.status_code}")
                            print(f"Response: {response.text}")
                            print(f"Response: {response.text}")
                    except ConnectionError:
                        print("Error: Unable to connect to the internet. Please check your connection.")
                        if response is not None:
                            print(f"Response: {response.json()}")
                    except Timeout:
                        print("Error: The request timed out. Please try again later.")
                        if response is not None:
                            print(f"Response: {response.json()}")
                    except RequestException as e:
                        print(f"An error occurred while getting leaderBoard status: {e}")  # Catch all other request-related exceptions
                        if response is not None:
                            print(f"Response: {response.json()}")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")  # Catch any other exceptions
                        if response is not None:
                            print(f"Response: {response.json()}")
            else :
                print("else submit")
                return False
            # time.sleep(self.polling_interval)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    
    
    base_url = "https://dev-eaa25-api-hpfyfcbshkabezeh.uaenorth-01.azurewebsites.net/leaderboard/dashboard/based"
    params = {
        "source": "game",
        "nameGame": "Falcon's Grasp"
    }
    
    while True :
        try:
            response = None
            response = requests.get(base_url, params=params,timeout=12)
            response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
            
            data = response.json()
            print(f"Leaderboard for Catch Stick:", data)

            # Extract team names and scores into a list of tuples
            if 'data' in data and len(data['data']) > 0:
                teams = data['data'][0].get('list', [])
                team_scores = [(team['name'][:13], team['total_score']) for team in teams]

                # Fill the appropriate list based on the game name
                list_top5_CatchTheStick.extend(team_scores[:5])  # Get top 5
                break

        except ConnectionError:
            print("Error: Unable to connect to the internet. Please check your connection.")
            if response is not None:
                print(f"Response: {response.json()}")
        except Timeout:
            print("Error: The request timed out. Please try again later.")
            if response is not None:
                print(f"Response: {response.json()}")
        except RequestException as e:
            print(f"An error occurred while getting leaderBoard status: {e}")  # Catch all other request-related exceptions
            if response is not None:
                print(f"Response: {response.json()}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")  # Catch any other exceptions
            if response is not None:
                print(f"Response: {response.json()}")
        
    main_app = MainApp()
   
    sys.exit(app.exec_())