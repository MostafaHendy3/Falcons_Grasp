"""
FalconGrasp Game - Complete Stable Version
Professional Falcon's Grasp (CatchTheStick) game with comprehensive stability improvements,
professional UI styling, and robust API management system.
"""

import csv
from datetime import datetime
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.game_api import GameAPI
from PyQt5.QtGui import QMovie, QPainter, QColor, QFont, QFontDatabase, QImage, QPixmap, QPen, QPainterPath, QPolygonF
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, pyqtSlot, QThread, QTime, QSize, QRectF, QPointF, QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QFrame
import math
import csv
import requests
import time
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets
import paho.mqtt.client as mqtt
import numpy as np

# Try to import PyQt5 multimedia with error handling
try:
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
    multimedia_available = True
except Exception as e:
    print(f"⚠️  PyQt5 multimedia not available: {e}")
    multimedia_available = False
    # Create dummy classes for compatibility
    class QMediaPlayer:
        def __init__(self, *args, **kwargs):
            pass
        def setMedia(self, *args, **kwargs):
            pass
        def play(self, *args, **kwargs):
            pass
        def stop(self, *args, **kwargs):
            pass
    class QMediaContent:
        def __init__(self, *args, **kwargs):
            pass

# Import our modular components
try:
    from config import config
    from utils.logger import get_logger, setup_root_logger
    from api.game_api import GameAPI
    
    # Setup logging with file output
    import os
    from datetime import datetime
    log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/falcongrasp_{log_timestamp}.log"
    
    # Setup root logger for the entire application
    setup_root_logger(level="INFO", log_file=log_file)
    
    # Get main logger
    logger = get_logger(__name__)
    logger.info("🎮============================================================")
    logger.info("🎮 STARTING FALCONGRASP GAME WITH COMPLETE UI AND NEW API")
    logger.info("🎮============================================================")
    logger.info(f"📄 Logs are being saved to: {log_file}")
except ImportError as e:
    # Fallback logging if our modules aren't available
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Failed to import game modules: {e}")
    logger.error("🔧 Please ensure config.py, utils/, and api/ are available")
    sys.exit(1)

# Game configuration from settings
game_config = config.settings.game
ui_config = config.settings.ui
api_config = config.settings.api

# Global game variables
final_screen_timer_idle = game_config.final_screen_timer
TimerValue = game_config.timer_value
global scaled
scaled = ui_config.scale_factor if ui_config.scale_factor > 0 else 1
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
list_top5_FalconGrasp = []
finalscore = 0
list_players_score = [0,0,0,0,0,0,0]

# Initialize leaderboard
try:
    api = GameAPI()
    if api.authenticate():
        logger.info("✅ API authentication successful")
        logger.info("📊 Loading initial leaderboard for 'Falcon's Grasp'...")
        leaderboard = api.get_leaderboard("Falcon's Grasp")
        list_top5_FalconGrasp.extend(leaderboard)
        logger.info(f"📊 Initial leaderboard loaded: {len(leaderboard)} entries")
        if leaderboard:
            logger.info("🏆 Top teams:")
            for i, (team_name, score) in enumerate(leaderboard[:5], 1):
                logger.info(f"   {i}. {team_name} - {score:,} points")
    else:
        logger.warning("⚠️  Failed to authenticate for initial leaderboard")
except Exception as e:
    logger.error(f"❌ Error loading initial leaderboard: {e}")

# FalconGrasp uses MQTT-based detection instead of ML models
logger.info("✅ FalconGrasp detection system initialized (MQTT-based)")



# Global game state variables
global gameStarted
gameStarted = False
global gameRunning
gameRunning = False




class MqttThread(QThread):
    """Enhanced MQTT thread with comprehensive error handling and cleanup"""
    message_signal = pyqtSignal(list)
    start_signal = pyqtSignal()
    stop_signal = pyqtSignal()
    restart_signal = pyqtSignal()
    activate_signal = pyqtSignal()
    deactivate_signal = pyqtSignal()
    timer_signal = pyqtSignal(int)

    def __init__(self, broker='localhost', port=1883):
        super().__init__()
        mqtt_config = config.settings.mqtt
        self.data_topics = mqtt_config.data_topics
        self.control_topics = mqtt_config.control_topics
        self.broker = mqtt_config.broker
        self.port = mqtt_config.port
        # Fix MQTT deprecation warning by using callback_api_version
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.subscribed = False
        
        # Set up callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        logger.debug("🔌 MqttThread initialized")

    def on_connect(self, client, userdata, flags, rc, properties=None):
        for topic in self.control_topics:
            client.subscribe(topic)

    def on_message(self, client, userdata, msg, properties=None):
        try:
            topic = msg.topic
            message = msg.payload.decode()
            logger.debug(f"📨 MQTT message received: {topic} = {message}")
            
            if topic == "FalconGrasp/game/start":
                self.handle_start()
            elif topic == "FalconGrasp/game/Activate":
                self.handle_activate()
            elif topic == "FalconGrasp/game/Deactivate":
                self.deactivate_signal.emit()
            elif topic == "FalconGrasp/game/stop":
                if message == "0":
                    self.handle_stop()
                elif message == "1":
                    self.unsubscribe_from_data_topics()
            elif topic == "FalconGrasp/game/restart":
                self.handle_restart()
            elif topic == "FalconGrasp/game/timer":
                try:
                    global TimerValue
                    TimerValue = int(message) * 1000
                    self.timer_signal.emit(TimerValue)
                except ValueError:
                    logger.warning(f"⚠️  Invalid timer value: {message}")
            elif topic == "FalconGrasp/game/timerfinal":
                try:
                    global final_screen_timer_idle
                    final_screen_timer_idle = int(message) * 1000
                except ValueError:
                    logger.warning(f"⚠️  Invalid final timer value: {message}")
            else:
                # Handle data messages for camera topics
                if self.subscribed:
                    self.handle_data_message(msg)
        except Exception as e:
            logger.warning(f"⚠️  Error processing MQTT message: {e}")
    
    def handle_data_message(self, msg):
        """Handle data messages from camera topics"""
        try:
            if self.subscribed and msg.topic in self.data_topics:
                # Create list of topic and data
                list_data = [msg.topic, msg.payload.decode()]
                logger.debug(f"Emitting data: {list_data}")
                self.message_signal.emit(list_data)
            else:
                logger.debug(f"Received message from non-subscribed topic: {msg.topic}")
        except Exception as e:
            logger.warning(f"⚠️  Error handling data message: {e}")
    
    def handle_restart(self):
        logger.debug("Game restarted")
        self.restart_signal.emit()
    
    def handle_start(self):
        logger.debug("Game started")
        self.subscribe_to_data_topics()
        self.start_signal.emit()
    
    def handle_activate(self):
        logger.debug("Game activated")
        self.activate_signal.emit()
    
    def handle_stop(self):
        logger.debug("Game stopped")
        self.stop_signal.emit()

    def run(self):
        """MQTT thread main loop with error handling"""
        try:
            logger.debug("🔌 Starting MQTT connection...")
            self.client.connect(self.broker, self.port, 60)
            logger.debug("✅ MQTT connected successfully")
            self.client.loop_forever()
        except Exception as e:
            logger.error(f"❌ MQTT connection error: {e}")
        finally:
            logger.debug("🔄 MQTT thread run() method exiting")

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
    
    def stop(self):
        """Safely stop the MQTT thread and cleanup resources"""
        logger.debug("🔄 Stopping MqttThread...")
        
        try:
            # Unsubscribe from all topics first
            if hasattr(self, 'client') and self.client:
                try:
                    # Unsubscribe from data topics
                    if self.subscribed:
                        for topic in self.data_topics:
                            self.client.unsubscribe(topic)
                    
                    # Unsubscribe from control topics
                    for topic in self.control_topics:
                        self.client.unsubscribe(topic)
                    
                    self.subscribed = False
                    logger.debug("✅ MQTT topics unsubscribed")
                except Exception as e:
                    logger.warning(f"⚠️  Error unsubscribing MQTT topics: {e}")
                
                # Disconnect from broker
                try:
                    self.client.disconnect()
                    logger.debug("✅ MQTT client disconnected")
                except Exception as e:
                    logger.warning(f"⚠️  Error disconnecting MQTT client: {e}")
            
            # Stop the thread loop
            if self.isRunning():
                self.quit()
                if not self.wait(5000):  # Wait up to 5 seconds
                    logger.warning("⚠️  MqttThread did not finish gracefully")
                else:
                    logger.debug("✅ MqttThread stopped gracefully")
                    
        except Exception as e:
            logger.warning(f"⚠️  Error stopping MQTT thread: {e}")


class GameManager(QThread):
    """
    Updated GameManager that uses the new GameAPI for FalconGrasp
    Handles the complete game flow:
    1. Authentication with API
    2. Poll for game initialization 
    3. Poll for game start
    4. Submit final scores
    """
    init_signal = pyqtSignal()
    start_signal = pyqtSignal()
    cancel_signal = pyqtSignal()
    submit_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        logger.info("🎮 GameManager initializing...")
        
        # Initialize the GameAPI
        try:
            self.api = GameAPI()
            logger.info("✅ GameAPI initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GameAPI: {e}")
            raise
            
        # Game state
        self.game_result_id = None
        self.submit_score_flag = False
        self.playStatus = True
        self.started_flag = False
        self.cancel_flag = False
        self.game_done = True
        
        logger.info("✅ GameManager initialized successfully")
        
    def run(self):
        """Main game loop following the proper API flow"""
        logger.info("🚀 GameManager starting main loop...")
        
        while self.playStatus:
            try:
                # Step 1: Authenticate
                logger.info("🔐 Step 1: Authenticating...")
                if not self.api.authenticate():
                    logger.error("❌ Authentication failed, retrying in 5 seconds...")
                    time.sleep(5)
                    continue
                
                # Step 2: Poll for game initialization
                logger.info("🎯 Step 2: Polling for game initialization...")
                if not self._poll_initialization():
                    continue
                
                # Step 3: Poll for game start
                logger.info("🚀 Step 3: Polling for game start...")
                if not self._poll_game_start():
                    continue
                
                # Step 4: Wait for game completion and submit scores
                logger.info("📊 Step 4: Waiting for game completion...")
                if not self._wait_and_submit_scores():
                    continue
                    
            except Exception as e:
                logger.error(f"💥 Error in game loop: {e}")
                time.sleep(5)
                continue
    
    def _poll_initialization(self) -> bool:
        """Poll for game initialization"""
        while self.playStatus and not self.cancel_flag:
            try:
                response = self.api.poll_game_initialization()
                if response and response.get('success'):
                    self.game_result_id = response.get('game_result_id')
                    logger.info(f"✅ Game initialized with ID: {self.game_result_id}")
                    self.init_signal.emit()
                    return True
                
                time.sleep(3)  # Poll every 3 seconds
                
            except Exception as e:
                logger.error(f"❌ Error polling initialization: {e}")
                return False
        
        return False
    
    def _poll_game_start(self) -> bool:
        """Poll for game start"""
        if not self.game_result_id:
            logger.error("❌ No game result ID available")
            return False
            
        while self.playStatus and not self.cancel_flag:
            try:
                response = self.api.poll_game_start(self.game_result_id)
                if response and response.get('success'):
                    logger.info("✅ Game started!")
                    self.start_signal.emit()
                    self.started_flag = True
                    return True
                
                time.sleep(3)  # Poll every 3 seconds
                
            except Exception as e:
                logger.error(f"❌ Error polling game start: {e}")
                return False
        
        return False
    
    def _wait_and_submit_scores(self) -> bool:
        """Wait for game completion and submit scores"""
        while self.playStatus and not self.submit_score_flag:
            if self.cancel_flag:
                logger.info("🚫 Game cancelled")
                self.cancel_signal.emit()
                self._reset_game_state()
                return True
            
            time.sleep(1)  # Check every second
        
        # Submit scores when flag is set
        if self.submit_score_flag:
            return self._submit_final_scores()
        
        return False
    
    def _submit_final_scores(self) -> bool:
        """Submit final scores to API"""
        try:
            global scored, list_players_score, teamName
            
            # Prepare score data for API
            scores = [
                {"player_name": f"Player_{i+1}", "score": score} 
                for i, score in enumerate(list_players_score[:5])
                if score > 0
            ]
            
            if not scores:
                scores = [{"player_name": "Team", "score": scored}]
            
            logger.info(f"📊 Submitting scores: {scores}")
            
            response = self.api.submit_final_scores(self.game_result_id, scores)
            if response and response.get('success'):
                logger.info("✅ Scores submitted successfully!")
                self.submit_signal.emit()
                self._reset_game_state()
                return True
            else:
                logger.error("❌ Failed to submit scores")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error submitting scores: {e}")
            return False
    
    def _reset_game_state(self):
        """Reset game state for next round"""
        global scored, list_players_score, gameStarted, gameRunning
        
        self.game_result_id = None
        self.submit_score_flag = False
        self.started_flag = False
        self.cancel_flag = False
        self.game_done = True
        
        # Reset global game variables
        scored = 0
        list_players_score = [0,0,0,0,0,0,0]
        gameStarted = False
        gameRunning = False
        
        logger.debug("🔄 Game state reset")

    def trigger_score_submission(self):
        """Trigger score submission (called from MQTT deactivate signal)"""
        logger.info("🎯 Score submission triggered")
        self.submit_score_flag = True
    
    def stop_manager(self):
        """Stop the game manager with comprehensive cleanup"""
        logger.info("🛑 Stopping GameManager...")
        
        try:
            # Stop the game loop
            self.playStatus = False
            
            # Disconnect all signals
            try:
                self.init_signal.disconnect()
                self.start_signal.disconnect()
                self.cancel_signal.disconnect()
                self.submit_signal.disconnect()
                logger.debug("✅ GameManager signals disconnected")
            except Exception as e:
                logger.warning(f"⚠️  Error disconnecting signals: {e}")
            
            # Clean up API object
            if hasattr(self, 'api') and self.api:
                try:
                    # The GameAPI object doesn't have explicit cleanup,
                    # but we can clear the reference
                    self.api = None
                    logger.debug("✅ GameAPI reference cleared")
                except Exception as e:
                    logger.warning(f"⚠️  Error cleaning API: {e}")
            
            # Reset game state
            try:
                self._reset_game_state()
                logger.debug("✅ Game state reset")
            except Exception as e:
                logger.warning(f"⚠️  Error resetting game state: {e}")
        
        except Exception as e:
            logger.warning(f"⚠️  Error in GameManager cleanup: {e}")
        
        # Stop the thread gracefully
        try:
            self.quit()
            if not self.wait(5000):  # Wait up to 5 seconds
                logger.warning("⚠️  GameManager thread did not finish gracefully")
                # Don't use terminate() unless absolutely necessary
            logger.debug("✅ GameManager stopped successfully")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping GameManager thread: {e}")


class Final_Screen(QtWidgets.QMainWindow):
    """Complete Final Screen implementation with professional styling"""
    
    def __init__(self):
        super().__init__()
        self.movie = None
        self.timer = None
        self.timer2 = None
        self.LeaderBoardTable = None
        logger.debug("🏆 Final_Screen initialized")
    
    def load_custom_font(self, font_path):
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            logger.warning(f"Failed to load font: {font_path}")
            return "Arial"  # Better fallback
        font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            return font_families[0]
        return "Arial"  # Better fallback
    
    def showTable(self):
        
        self.ScoreLabel.show()
        self.LeaderBoardTable.show()
        
        # Refresh leaderboard data before showing table
        logger.info("📊 Final screen showing table - refreshing leaderboard data")
        self._update_leaderboard()
        
        # UpdateTable is called within _update_leaderboard, but call again as backup
        self.UpdateTable()
    
   
    
    def hideTable(self):
        if hasattr(self, 'ScoreLabel'):
            self.ScoreLabel.hide()
        if hasattr(self, 'LeaderBoardTable'):
            self.LeaderBoardTable.hide()

    def setupTimer(self):
        # Start the GIF
        if hasattr(self, 'movie'):
            self.movie.start()
        # Note: Timer logic from original CatchTheStick.py was commented out
        # Original behavior: show table immediately, which we now do in setupUi
    
    def setupUi(self, Home):
        Home.setObjectName("Home")
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        Home.setLayoutDirection(QtCore.Qt.LeftToRight)
        Home.setAutoFillBackground(False)
        
        # Get screen size for scaling (same logic as CatchTheStick.py)
        self.sized = QtWidgets.QDesktopWidget().screenGeometry()
        if Home.geometry().width() > 1080:
            self.scale = 2
        else:
            self.scale = 1
        
        # Load custom fonts with fallback
        self.font_family = self.load_custom_font("Assets/Fonts/GOTHIC.TTF")
        self.font_family_good = self.load_custom_font("Assets/Fonts/GOTHICB.TTF")
        if not self.font_family_good:
            self.font_family_good = "Arial"  # Fallback font
        
        # Create central widget
        self.centralwidget = QtWidgets.QWidget(Home)
        self.centralwidget.setObjectName("centralwidget")
        
        # Background setup
        self.Background = QtWidgets.QLabel(self.centralwidget)
        self.Background.setGeometry(QtCore.QRect(0, 0, int(self.sized.width()), int(self.sized.height())))
        
        # Setup GIF animation
        if scaled == 1:
            self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_final.gif")
        else:
            self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_final.gif")
        
        self.movie.setCacheMode(QMovie.CacheAll)
        self.Background.setMovie(self.movie)
        self.Background.setScaledContents(True)
        
        # Score label
        self.ScoreLabel = QtWidgets.QLabel(self.centralwidget)
        self.ScoreLabel.setGeometry(QtCore.QRect(350*self.scale, 400*self.scale, 400*self.scale, 150*self.scale))
        # self.ScoreLabel.setGeometry(QtCore.QRect(int(885*self.scale), int(380*self.scale), int(200*self.scale), int(120*self.scale)))
        self.ScoreLabel.setText(str(scored))
        self.ScoreLabel.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(int(35*self.scale))
        font.setFamily(self.font_family_good)
        self.ScoreLabel.setFont(font)
        self.ScoreLabel.setStyleSheet("color: rgb(255, 255, 255);")
        self.ScoreLabel.hide()
        self.ScoreLabel.raise_()
        
        # Create leaderboard table with professional styling (exact CatchTheStick.py positioning)
        self.frame_2 = QtWidgets.QFrame(self.centralwidget)
        self.frame_2.setGeometry(QtCore.QRect(200*self.scale, 750*self.scale, 650*self.scale, 415*self.scale))
        self.gridLayout = QtWidgets.QGridLayout(self.frame_2)
        self.LeaderBoardTable = QtWidgets.QTableWidget(self.frame_2)
        self.LeaderBoardTable.setRowCount(5)
        self.LeaderBoardTable.setColumnCount(2)
        
        # Set up table properties
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(int(22*self.scale))
        font.setBold(False)
        font.setItalic(False)
        self.LeaderBoardTable.setFont(font)
        self.LeaderBoardTable.setFocusPolicy(QtCore.Qt.NoFocus)
        self.LeaderBoardTable.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.LeaderBoardTable.setAutoFillBackground(False)
        self.LeaderBoardTable.setLineWidth(0)
        self.LeaderBoardTable.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.LeaderBoardTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.LeaderBoardTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.LeaderBoardTable.setAutoScroll(False)
        self.LeaderBoardTable.setAutoScrollMargin(0)
        self.LeaderBoardTable.setProperty("showDropIndicator", False)
        self.LeaderBoardTable.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.LeaderBoardTable.setTextElideMode(QtCore.Qt.ElideLeft)
        self.LeaderBoardTable.setShowGrid(False)
        self.LeaderBoardTable.setGridStyle(QtCore.Qt.NoPen)
        self.LeaderBoardTable.setWordWrap(True)
        self.LeaderBoardTable.setCornerButtonEnabled(True)
        self.LeaderBoardTable.setObjectName("LeaderBoardTable")
        
        # Professional table styling - original CatchTheStick
        self.LeaderBoardTable.setStyleSheet("""
            /* QTableWidget Styling */
            QTableWidget {
                background-color: transparent;  /* Transparent background */
                color: #ffffff;  /* White text color */
                gridline-color: #3b5998;  /* Medium muted blue gridline color */
                selection-background-color: transparent;  /* Transparent selection background */
                selection-color: #ffffff;  /* White selection text color */
                border: 1px solid #3b5998;  /* Border around the table */
                border-radius: 4px;  /* Rounded corners */
                padding: 4px;  /* Padding inside the table */
                margin: 8px;  /* Margin around the table */
            }

            QHeaderView::section { 
                background-color: #001f3f;  /* Dark blue background for header sections */
                color: #ffffff;  /* White text color for header sections */
                padding: 5px;  /* Padding for header sections */
                border: 1px solid #3b5998;  /* Border color to match table */
            }

            QHeaderView {
                background-color: transparent;  /* Transparent background */
            }

            QTableCornerButton::section {
                background-color: transparent;  /* Transparent background */
            }

            QTableWidget::item {
                padding: 4px;  /* Padding for items */
                border: none;  /* No border for items */
            }

            QTableWidget::item:selected {
                background-color: transparent;  /* Transparent background for selected items */
                color: #2e4053;  /* Blue text color for selected items */
            }

            QTableWidget::item:hover {
                background-color: #001f3f;  /* Dark blue background on hover */
            }
        """)
        
        # Create table items with enhanced properties
        for i in range(5):
            for j in range(2):
                item = QtWidgets.QTableWidgetItem()
                if j == 0:
                    item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                else:
                    item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
                self.LeaderBoardTable.setItem(i, j, item)
        
        # Apply original CatchTheStick palette configuration
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
        self.LeaderBoardTable.setPalette(palette)
        
        # Set horizontal headers with custom properties
        self.LeaderBoardTable.setHorizontalHeaderLabels(["Team", "Score"])
        self.LeaderBoardTable.horizontalHeader().setVisible(True)
        self.LeaderBoardTable.horizontalHeader().setCascadingSectionResizes(True)
        self.LeaderBoardTable.horizontalHeader().setDefaultSectionSize(300*self.scale)
        self.LeaderBoardTable.horizontalHeader().setMinimumSectionSize(100*self.scale)
        self.LeaderBoardTable.horizontalHeader().setStretchLastSection(False)
        self.LeaderBoardTable.verticalHeader().setVisible(False)
        self.LeaderBoardTable.verticalHeader().setCascadingSectionResizes(True)
        self.LeaderBoardTable.verticalHeader().setDefaultSectionSize(65*self.scale)
        self.LeaderBoardTable.verticalHeader().setMinimumSectionSize(50*self.scale)
        self.LeaderBoardTable.verticalHeader().setStretchLastSection(False)
        
        self.gridLayout.addWidget(self.LeaderBoardTable, 0, 0, 1, 1)
        
        Home.setCentralWidget(self.centralwidget)
        self.timer = QTimer(Home)
        self.timer2 = QTimer(Home)
        self.setupTimer()
        self.UpdateTable()
        self.showTable()  # Show table immediately like in original CatchTheStick.py
        
        # Apply font styling like in original CatchTheStick.py
        font = QtGui.QFont()
        font.setFamily(self.font_family_good)
        font.setPointSize(int(22*self.scale))
        font.setBold(True)
        font.setWeight(75)
        self.LeaderBoardTable.setFont(font)
        
        self.retranslateUi(Home)
        QtCore.QMetaObject.connectSlotsByName(Home)
    
    def retranslateUi(self, Home):
        _translate = QtCore.QCoreApplication.translate
        Home.setWindowTitle(_translate("Home", "FalconGrasp Final"))
        
        # Set table headers
        item = self.LeaderBoardTable.horizontalHeaderItem(0)
        if item:
            item.setText(_translate("Home", "Team"))
        item = self.LeaderBoardTable.horizontalHeaderItem(1)
        if item:
            item.setText(_translate("Home", "Score"))

    def UpdateTable(self):
        """Update the final screen leaderboard table with current data"""
        global list_top5_FalconGrasp
        try:
            logger.debug(f"📊 Final screen updating table with {len(list_top5_FalconGrasp)} entries")
            
            # Clear all rows first
            for i in range(5):
                self.LeaderBoardTable.setItem(i, 0, QtWidgets.QTableWidgetItem(""))
                self.LeaderBoardTable.setItem(i, 1, QtWidgets.QTableWidgetItem(""))
            
            # Sort data by score (descending)
            sorted_data = sorted(list_top5_FalconGrasp, key=lambda item: item[1], reverse=True)
            logger.debug(f"📊 Final screen sorted leaderboard data: {sorted_data}")
            
            # Populate table with data
            for i, (team, score) in enumerate(sorted_data):
                if i >= 5:  # Only show top 5
                    break

                team_item = QtWidgets.QTableWidgetItem(str(team))
                team_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.LeaderBoardTable.setItem(i, 0, team_item)
                
                score_item = QtWidgets.QTableWidgetItem(f"{score:,}")
                score_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.LeaderBoardTable.setItem(i, 1, score_item)
            
            # If no data, show placeholder
            if not list_top5_FalconGrasp:
                placeholder_item = QtWidgets.QTableWidgetItem("No teams yet")
                placeholder_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.LeaderBoardTable.setItem(0, 0, placeholder_item)
                
                placeholder_score = QtWidgets.QTableWidgetItem("0")
                placeholder_score.setTextAlignment(QtCore.Qt.AlignCenter)
                self.LeaderBoardTable.setItem(0, 1, placeholder_score)
                
            logger.debug("📊 Final screen leaderboard table updated successfully")
            
        except Exception as e:
            logger.error(f"❌ Error updating final screen leaderboard table: {e}")
    
    def _update_leaderboard(self):
        """Update the leaderboard data from API for final screen"""
        try:
            global list_top5_FalconGrasp
            logger.info("📊 Final screen fetching leaderboard for 'Falcon's Grasp'...")
            leaderboard = api.get_leaderboard("Falcon's Grasp")
            logger.info(f"📊 Final screen leaderboard received: {leaderboard}")
            
            list_top5_FalconGrasp.clear()
            list_top5_FalconGrasp.extend(leaderboard)
            
            logger.info(f"📊 Final screen leaderboard updated with {len(leaderboard)} entries")
            
            # Update the UI table if it exists
            if hasattr(self, 'UpdateTable'):
                self.UpdateTable()
                logger.info("📊 Final screen leaderboard table UI updated")
                
        except Exception as e:
            logger.error(f"❌ Error updating final screen leaderboard: {e}")
    
    def closeEvent(self, event):
        logger.info("🔄 Final screen closing...")
        
        # Safely stop movie
        if hasattr(self, 'movie') and self.movie:
            try:
                self.movie.stop()
                self.movie.setCacheMode(QMovie.CacheNone)
                self.movie = None
                logger.debug("✅ Movie cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error stopping movie: {e}")
        
        # Safely stop timers
        if hasattr(self, 'timer') and self.timer:
            try:
                self.timer.stop()
                # Disconnect signals
                try:
                    self.timer.timeout.disconnect()
                except:
                    pass
                self.timer = None
                logger.debug("✅ Timer cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error stopping timer: {e}")
        
        if hasattr(self, 'timer2') and self.timer2:
            try:
                self.timer2.stop()
                try:
                    self.timer2.timeout.disconnect()
                except:
                    pass
                self.timer2 = None
                logger.debug("✅ Timer2 cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error stopping timer2: {e}")
        
        # Safely clear background
        if hasattr(self, 'Background') and self.Background:
            try:
                self.Background.clear()
                logger.debug("✅ Background cleared")
            except Exception as e:
                logger.warning(f"⚠️  Error clearing background: {e}")
        
        # Clean up table widget
        if hasattr(self, 'LeaderBoardTable') and self.LeaderBoardTable:
            try:
                self.LeaderBoardTable.hide()
                self.LeaderBoardTable.clear()
                self.LeaderBoardTable.close()
                self.LeaderBoardTable.deleteLater()
                self.LeaderBoardTable = None
                logger.debug("✅ Table widget cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error cleaning table widget: {e}")
        
        # Close main widget
        try:
            if hasattr(self, 'centralwidget'):
                self.centralwidget.close()
                self.centralwidget.deleteLater()
            self.close()
            logger.debug("✅ Final screen closed successfully")
        except Exception as e:
            logger.warning(f"⚠️  Error closing final screen: {e}")
        
        event.accept()
        super().closeEvent(event)


# Full screen implementations with comprehensive safety improvements

class Home_screen(QtWidgets.QMainWindow):
    """Enhanced Home_screen with comprehensive safety and professional styling"""
    
    def __init__(self):
        super().__init__()
        self.player = None
        self.movie = None
        self.LeaderboardTable = None
        if multimedia_available:
            self.player = QMediaPlayer()
        logger.debug("🏠 Home_screen initialized")
    
    def load_custom_font(self, font_path):
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            logger.warning(f"Failed to load font: {font_path}")
            return "Arial"  # Better fallback
        font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            return font_families[0]
        return "Arial"  # Better fallback
    
    def setupUi(self, Home):
        """Setup UI with professional styling"""
        try:
            Home.setObjectName("Home")
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
            
            # Get screen size for scaling (same logic as CatchTheStick.py)
            self.sized = QtWidgets.QDesktopWidget().screenGeometry()
            if Home.geometry().width() > 1080:
                self.scale = 2
            else:
                self.scale = 1
            
            # Load fonts with fallback
            self.font_family = self.load_custom_font("Assets/Fonts/GOTHIC.TTF")
            self.font_family_good = self.load_custom_font("Assets/Fonts/GOTHICB.ttf")
            if not self.font_family_good:
                self.font_family_good = "Arial"  # Fallback font
            
            # Central widget
            self.centralwidget = QtWidgets.QWidget(Home)
            self.centralwidget.setObjectName("centralwidget")
            
            # Background
            self.Background = QtWidgets.QLabel(self.centralwidget)
            self.Background.setGeometry(QtCore.QRect(0, 0, int(self.sized.width()), int(self.sized.height())))
            
            # Setup GIF
            if self.sized.width() > 1080:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_intro.gif")
            else:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_intro.gif")
            
            self.movie.setCacheMode(QMovie.CacheAll)
            self.Background.setMovie(self.movie)
            self.Background.setScaledContents(True)
            self.movie.start()
            
            # Leaderboard table setup (exact CatchTheStick.py positioning for Home_screen)
            self.frame_2 = QtWidgets.QFrame(self.centralwidget)
            self.frame_2.setGeometry(QtCore.QRect(200*self.scale, 565*self.scale, 650*self.scale, 415*self.scale))
            self.gridLayout = QtWidgets.QGridLayout(self.frame_2)
            self.LeaderboardTable = QtWidgets.QTableWidget(self.frame_2)
            self.LeaderboardTable.setRowCount(5)
            self.LeaderboardTable.setColumnCount(2)
            
            
            # Apply original CatchTheStick table styling
            self.LeaderboardTable.setStyleSheet("""
                /* QTableWidget Styling */
                QTableWidget {
                    background-color: transparent;  /* Transparent background */
                    color: #ffffff;  /* White text color */
                    gridline-color: #3b5998;  /* Medium muted blue gridline color */
                    selection-background-color: transparent;  /* Transparent selection background */
                    selection-color: #ffffff;  /* White selection text color */
                    border: 1px solid #3b5998;  /* Border around the table */
                    border-radius: 4px;  /* Rounded corners */
                    padding: 4px;  /* Padding inside the table */
                    margin: 8px;  /* Margin around the table */
                }

                QHeaderView::section { 
                    background-color: #001f3f;  /* Dark blue background for header sections */
                    color: #ffffff;  /* White text color for header sections */
                    padding: 5px;  /* Padding for header sections */
                    border: 1px solid #3b5998;  /* Border color to match table */
                }

                QHeaderView {
                    background-color: transparent;  /* Transparent background */
                }

                QTableCornerButton::section {
                    background-color: transparent;  /* Transparent background */
                }

                QTableWidget::item {
                    padding: 4px;  /* Padding for items */
                    border: none;  /* No border for items */
                }

                QTableWidget::item:selected {
                    background-color: transparent;  /* Transparent background for selected items */
                    color: #2e4053;  /* Blue text color for selected items */
                }

                QTableWidget::item:hover {
                    background-color: #001f3f;  /* Dark blue background on hover */
                }
            """)
            
            # Set headers and items
            self.LeaderboardTable.setHorizontalHeaderLabels(["Team", "Score"])
            for i in range(5):
                for j in range(2):
                    item = QtWidgets.QTableWidgetItem()
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    self.LeaderboardTable.setItem(i, j, item)
            
            # Apply original CatchTheStick palette configuration
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
            self.LeaderboardTable.setPalette(palette)
            
            self.LeaderboardTable.horizontalHeader().setVisible(True)
            self.LeaderboardTable.horizontalHeader().setCascadingSectionResizes(True)
            self.LeaderboardTable.horizontalHeader().setDefaultSectionSize(300*self.scale)
            self.LeaderboardTable.horizontalHeader().setMinimumSectionSize(100*self.scale)
            self.LeaderboardTable.horizontalHeader().setStretchLastSection(False)
            self.LeaderboardTable.verticalHeader().setVisible(False)
            self.LeaderboardTable.verticalHeader().setCascadingSectionResizes(True)
            self.LeaderboardTable.verticalHeader().setDefaultSectionSize(65*self.scale)
            self.LeaderboardTable.verticalHeader().setMinimumSectionSize(50*self.scale)
            self.LeaderboardTable.verticalHeader().setStretchLastSection(False)
            # Professional table styling
            font = QtGui.QFont()
            font.setFamily(self.font_family_good)
            font.setPointSize(int(22*self.scale))
            self.LeaderboardTable.setFont(font)
            self.LeaderboardTable.setFocusPolicy(QtCore.Qt.NoFocus)
            
            self.gridLayout.addWidget(self.LeaderboardTable, 0, 0, 1, 1)
            Home.setCentralWidget(self.centralwidget)
            
            # Setup timer2 to call Inactive() after 13 seconds (same as CatchTheStick.py)
            self.timer2 = QTimer(Home)
            self.timer2.setTimerType(Qt.PreciseTimer)
            self.timer2.timeout.connect(self.Inactive)
            self.timer2.start(11000)  # 11 seconds like CatchTheStick.py
            logger.info("⏰ Home screen timer2 set for 11 seconds to switch to Inactive state")
            
            self.UpdateTable()
            # Initially hide table - it will be shown by Inactive() after 13 seconds
            self.LeaderboardTable.hide()
            logger.debug("✅ Home_screen setup completed")
            
        except Exception as e:
            logger.error(f"❌ Error setting up Home_screen: {e}")
    
    def UpdateTable(self):
        """Update the leaderboard table with current data"""
        try:
            global list_top5_FalconGrasp
            logger.debug(f"📊 Updating table with {len(list_top5_FalconGrasp)} entries")
            
            # Clear all rows first
            for i in range(5):
                self.LeaderboardTable.setItem(i, 0, QtWidgets.QTableWidgetItem(""))
                self.LeaderboardTable.setItem(i, 1, QtWidgets.QTableWidgetItem(""))
            
            # Sort data by score (descending)
            sorted_data = sorted(list_top5_FalconGrasp, key=lambda item: item[1], reverse=True)
            logger.debug(f"📊 Sorted leaderboard data: {sorted_data}")
            
            # Populate table with data
            for i, (team, score) in enumerate(sorted_data):
                if i >= 5:  # Only show top 5
                    break

                team_item = QtWidgets.QTableWidgetItem(str(team))
                team_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.LeaderboardTable.setItem(i, 0, team_item)
                
                score_item = QtWidgets.QTableWidgetItem(f"{score:,}")
                score_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.LeaderboardTable.setItem(i, 1, score_item)
            
            # If no data, show placeholder
            if not list_top5_FalconGrasp:
                placeholder_item = QtWidgets.QTableWidgetItem("No teams yet")
                placeholder_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.LeaderboardTable.setItem(0, 0, placeholder_item)
                
                placeholder_score = QtWidgets.QTableWidgetItem("0")
                placeholder_score.setTextAlignment(QtCore.Qt.AlignCenter)
                self.LeaderboardTable.setItem(0, 1, placeholder_score)
                
        except Exception as e:
            logger.error(f"❌ Error updating leaderboard table: {e}")
    
    def _update_leaderboard(self):
        """Update the leaderboard data from API"""
        try:
            global list_top5_FalconGrasp
            logger.info("📊 Fetching leaderboard for 'Falcon's Grasp'...")
            leaderboard = api.get_leaderboard("Falcon's Grasp")
            logger.info(f"📊 Leaderboard received: {leaderboard}")
            
            list_top5_FalconGrasp.clear()
            list_top5_FalconGrasp.extend(leaderboard)
            
            logger.info(f"📊 Leaderboard updated with {len(leaderboard)} entries")
            
            # Update the UI table if it exists
            if hasattr(self, 'UpdateTable'):
                self.UpdateTable()
                logger.info("📊 Leaderboard table UI updated")
                
        except Exception as e:
            logger.error(f"❌ Error updating leaderboard: {e}")
    
    def Inactive(self):
        """Switch to inactive state with inActive GIF and show table (same as CatchTheStick.py)"""
        try:
            logger.info("🔄 Home screen switching to Inactive state")
            
            # Stop the timer2 if it exists
            if hasattr(self, 'timer2') and self.timer2:
                self.timer2.stop()
            
            # Load the inactive GIF based on screen size (same logic as CatchTheStick.py)
            global scaled
            if scaled == 1:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_inActive.gif")
                self.movie.setCacheMode(QMovie.CacheAll)
            else:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_inActive.gif")
                self.movie.setCacheMode(QMovie.CacheAll)
            
            # Set the new movie and start it
            self.Background.setMovie(self.movie)
            self.movie.start()
            
            # Show the table (same as CatchTheStick.py)
            self.LeaderboardTable.show()
            
            # Set global homeOpened flag (same as CatchTheStick.py)
            global homeOpened
            homeOpened = True
            
            logger.info("✅ Home screen switched to Inactive state successfully")
            
        except Exception as e:
            logger.error(f"❌ Error switching to Inactive state: {e}")
    
    def closeEvent(self, event):
        logger.info("🔄 Home screen closing...")
        
        # Stop timer2 if it exists
        if hasattr(self, 'timer2') and self.timer2:
            try:
                self.timer2.stop()
                try:
                    self.timer2.timeout.disconnect()
                except:
                    pass
                self.timer2 = None
                logger.debug("✅ Timer2 cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error stopping timer2: {e}")
        
        if hasattr(self, 'movie') and self.movie:
            try:
                self.movie.stop()
                self.movie = None
            except Exception as e:
                logger.warning(f"⚠️  Error stopping movie: {e}")
        if hasattr(self, 'player') and self.player:
            try:
                self.player.stop()
                self.player = None
            except Exception as e:
                logger.warning(f"⚠️  Error stopping player: {e}")
        event.accept()
        super().closeEvent(event)


class Active_screen(QWidget):
    """Enhanced Active_screen with FalconGrasp detection logic and safety improvements"""
    
    def __init__(self):
        super().__init__()
        self.mqtt_thread = None
        self.player = None
        self.TimerGame = None
        self.remaining_time = 0
        if multimedia_available:
            self.player = QMediaPlayer()
        logger.debug("🎮 Active_screen initialized")
        
        # Initialize MQTT thread with enhanced error handling
        try:
            self.mqtt_thread = MqttThread('localhost')
            self.mqtt_thread.restart_signal.connect(self.restart_game)
            self.mqtt_thread.start_signal.connect(self.start_game)
            self.mqtt_thread.stop_signal.connect(self.stop_game)
            self.mqtt_thread.activate_signal.connect(lambda: logger.info("🔋 Game activated"))
            self.mqtt_thread.deactivate_signal.connect(self.deactivate)
            self.mqtt_thread.message_signal.connect(lambda data: self.ReceiveData(data))
            self.mqtt_thread.start()
        except Exception as e:
            logger.warning(f"⚠️  MQTT initialization failed: {e}")
    
    def load_custom_font(self, font_path):
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            return "Arial"  # Better fallback
        font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
        return font_families[0] if font_families else "Arial"  # Better fallback
    
    def play_audio(self):
        if not multimedia_available or not self.player:
            return
        try:
            audio_file = "mp3/2066.wav"
            absolute_path = os.path.abspath(audio_file)
            self.player.setMedia(QMediaContent(QtCore.QUrl.fromLocalFile(absolute_path)))
            self.player.setVolume(100)
            self.player.play()
        except Exception as e:
            logger.warning(f"⚠️  Audio error: {e}")
    
    def ReceiveData(self, data):
        """Process FalconGrasp detection data from MQTT"""
        try:
            logger.debug(f"Received data: {data}")
            topic = data[0]
            message = data[1]
            
            # Handle camera topics (individual player scores)
            if "/camera/" in topic:
                topic_parts = topic.split('/')
                if len(topic_parts) >= 3:
                    try:
                        index = int(topic_parts[2])
                        score = int(message)
                        
                        if 0 <= index < 5:  # Valid player index (0-4)
                            global list_players_score
                            list_players_score[index] = score
                            
                            if hasattr(self, 'tableWidget_2') and self.tableWidget_2 and self.tableWidget_2.isVisible():
                                item = QtWidgets.QTableWidgetItem()
                                item.setTextAlignment(QtCore.Qt.AlignCenter)
                                item.setText(str(score))
                                self.tableWidget_2.setItem(index, 1, item)
                                
                            logger.debug(f"📊 Updated Player {index+1} score: {score}")
                        else:
                            logger.warning(f"⚠️  Invalid player index: {index}")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"⚠️  Error parsing camera topic {topic}: {e}")
            
            # Handle team name topic
            elif topic.endswith("/TeamName/Pub"):
                global teamName
                teamName = message
                logger.debug(f"📝 Team name updated: {teamName}")
                
                # Update team name label if it exists
                if hasattr(self, 'label') and self.label:
                    self.label.setText(teamName)
            
            # Handle total score topic
            elif topic.endswith("/score/Pub"):
                try:
                    global scored
                    scored = int(message)
                    logger.debug(f"📊 Total score updated: {scored}")
                except ValueError as e:
                    logger.warning(f"⚠️  Invalid total score format: {message} - {e}")
            
            else:
                logger.debug(f"🔍 Ignoring unhandled topic: {topic}")
                
        except Exception as e:
            logger.warning(f"⚠️  Error processing data: {e}")
    
    def restart_game(self):
        """Restart game with timer management"""
        global gameRunning
        try:
            logger.debug("🔄 Restarting FalconGrasp game...")
            
            gameRunning = False  # Reset flag to allow restart
            
            # Call start_game to properly restart
            self.start_game()
            
            logger.debug("✅ Game restarted successfully")
        except Exception as e:
            logger.warning(f"⚠️  Error restarting game: {e}")
            gameRunning = False  # Reset flag on error
    
    def start_game_timer(self, duration_ms):
        """Start or update game timer"""
        try:
            if not hasattr(self, 'TimerGame') or not self.TimerGame:
                self.TimerGame = QtCore.QTimer(self)
                self.TimerGame.timeout.connect(self.update_timer_display)
            
            # Calculate initial timer display
            self.remaining_time = duration_ms // 1000  # Convert to seconds
            self.set_lcd(self.remaining_time)
            
            # Start timer (update every second)
            self.TimerGame.start(1000)
            logger.debug(f"⏰ Game timer started: {duration_ms}ms")
            
        except Exception as e:
            logger.warning(f"⚠️  Error starting game timer: {e}")
    
    def update_timer_display(self):
        """Update timer display every second"""
        global gameRunning
        try:
            if self.remaining_time > 0:
                self.remaining_time -= 1
                self.set_lcd(self.remaining_time)
            else:
                # Timer finished
                gameRunning = False  # Reset flag when timer finishes
                
                if hasattr(self, 'TimerGame') and self.TimerGame:
                    self.TimerGame.stop()
                self.set_lcd(0)
                logger.debug("⏰ Game timer finished - game can be started again")
        except Exception as e:
            logger.warning(f"⚠️  Error updating timer: {e}")
            gameRunning = False  # Reset flag on error
    
    @pyqtSlot()
    def start_game(self):
        """Start game with timer and audio (same logic as CatchTheStick.py)"""
        global gameRunning
        try:
            # Prevent recursive calls
            if gameRunning:
                logger.debug("🔄 Game is already running, skipping start_game call")
                return
                
            gameRunning = True
            logger.info("🚀 Starting FalconGrasp game...")
            
            # Reset player scores
            global list_players_score
            list_players_score = [0,0,0,0,0]
            
            # Get timer value from config or file
            global TimerValue
            try:
                with open("file2.txt", "r") as file:
                    lines = file.readlines()
                    if lines:
                        TimerValue = int(lines[-1].strip())
            except FileNotFoundError:
                logger.info("file2.txt not found. Using default timer value.")
                TimerValue = game_config.timer_value  # Use config default
            
            # Start game timer
            if hasattr(self, 'TimerGame') and self.TimerGame:
                self.TimerGame.start(TimerValue)
            
            # Start display timer
            self.start_game_timer(TimerValue)
            
            # Play audio
            self.play_audio()
            
            logger.info("✅ FalconGrasp game started successfully")
            
        except Exception as e:
            logger.error(f"❌ Error starting game: {e}")
            gameRunning = False  # Reset flag on error
    
    @pyqtSlot()
    def stop_game(self):
        """Stop game and calculate final score (same logic as CatchTheStick.py)"""
        try:
            logger.info("🛑 Stopping FalconGrasp game...")
            
            global finalscore, teamName, list_players_score, gameRunning
            
            # Reset game running flag
            gameRunning = False
            
            # Calculate final score
            finalscore = 0
            for i in range(5):
                finalscore += list_players_score[i]
            
            # Save score to CSV (if needed)
            self.save_final_score_to_csv(teamName, finalscore)
            
            logger.info(f"📊 Game stopped - Final score: {finalscore}")
            logger.info(f"📊 Player scores: {list_players_score}")
            
            # Stop MQTT and timers
            if hasattr(self, 'mqtt_thread') and self.mqtt_thread:
                self.mqtt_thread.client.publish("FalconGrasp/game/stop", 1)
                self.mqtt_thread.unsubscribe_from_data_topics()
            
            # Stop timers
            if hasattr(self, 'TimerGame') and self.TimerGame:
                self.TimerGame.stop()
            
            # Play audio
            self.play_audio()
            
            logger.info("✅ FalconGrasp game stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ Error stopping game: {e}")
            gameRunning = False  # Reset flag on error
    
    @pyqtSlot()
    def cancel_game(self):
        """Cancel game and stop timers (same logic as CatchTheStick.py)"""
        global gameRunning
        try:
            logger.info("🚫 Cancelling FalconGrasp game...")
            
            gameRunning = False  # Reset game running flag
            
            if hasattr(self, 'TimerGame') and self.TimerGame:
                self.TimerGame.stop()
            
            logger.info("✅ FalconGrasp game cancelled successfully")
            
        except Exception as e:
            logger.error(f"❌ Error cancelling game: {e}")
            gameRunning = False  # Reset flag on error
    
    @pyqtSlot()
    def deactivate(self):
        """Send deactivate signal via MQTT (same logic as CatchTheStick.py)"""
        global gameRunning
        try:
            logger.info("🔄 Deactivating FalconGrasp game...")
            
            gameRunning = False  # Reset game running flag
            
            if hasattr(self, 'mqtt_thread') and self.mqtt_thread:
                self.mqtt_thread.client.publish("FalconGrasp/game/Deactivate", 1)
            
            logger.info("✅ FalconGrasp deactivate signal sent")
            
        except Exception as e:
            logger.error(f"❌ Error sending deactivate signal: {e}")
            gameRunning = False  # Reset flag on error
    
    def save_final_score_to_csv(self, team_name, final_score):
        """Save final score to CSV file (same logic as CatchTheStick.py)"""
        try:
            # Get the current date and time
            current_datetime = datetime.now()
            date_str = current_datetime.strftime("%Y-%m-%d")
            time_str = current_datetime.strftime("%H:%M:%S")
            
            # Create a list representing a row of data
            row_data = [team_name, final_score, date_str, time_str]
            
            # Write the row to the CSV file
            with open('Falcon_scores.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(row_data)
                
            logger.info(f"📝 Score saved to CSV: {team_name} - {final_score}")
            
        except Exception as e:
            logger.error(f"❌ Error saving score to CSV: {e}")
    
    def setupUi(self, MainWindow):
        """Setup Active screen UI with FalconGrasp styling"""
        try:
            MainWindow.setObjectName("MainWindow")
            
            # Scaling setup (exact CatchTheStick.py logic)
            if MainWindow.geometry().width() > 1080:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_Active.gif")
                self.movie.setCacheMode(QMovie.CacheAll)
                self.scale = 2
            else:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_Active.gif")
                self.movie.setCacheMode(QMovie.CacheAll)
                self.scale = 1
            
            # Central widget setup
            self.centralwidget = QtWidgets.QWidget(MainWindow)
            self.centralwidget.setObjectName("centralwidget")
            
            # Load fonts with fallback
            self.font_family = self.load_custom_font("Assets/Fonts/GOTHIC.TTF")
            self.font_family_good = self.load_custom_font("Assets/Fonts/GOTHICB.TTF")
            if not self.font_family_good:
                self.font_family_good = "Arial"  # Fallback font
            
            # Background
            self.Background = QtWidgets.QLabel(self.centralwidget)
            self.Background.setGeometry(QtCore.QRect(0, 0, int(MainWindow.geometry().width()), int(MainWindow.geometry().height())))
            self.Background.setMovie(self.movie)
            self.Background.setScaledContents(True)
            self.movie.start()
            
            # Team name label
            self.label = QtWidgets.QLabel(self.centralwidget)
            self.label.setGeometry(QtCore.QRect(int(380*self.scale), int(650*self.scale), int(450*self.scale), int(70*self.scale)))
            self.label.setText(teamName)
            self.label.setAlignment(QtCore.Qt.AlignCenter)
            font = QtGui.QFont()
            font.setPointSize(int(42*self.scale))
            font.setFamily(self.font_family_good)
            self.label.setFont(font)
            self.label.setStyleSheet("color: rgb(92,255,230);")
            
            # Timer display setup
            self.widget_2 = QtWidgets.QWidget(self.centralwidget)
            self.widget_2.setGeometry(QtCore.QRect(int(335*self.scale), int(365*self.scale), int(445*self.scale), int(169*self.scale)))
            self.horizontalLayout = QtWidgets.QHBoxLayout()
            
            # LCD Numbers for timer
            self.lcdNumber = QtWidgets.QLCDNumber(self.widget_2)
            self.lcdNumber.setStyleSheet("""
                QLCDNumber {
                    background-color: transparent;
                    color: #ff8b00;
                    border: 2px solid #5ce1e6;
                    border-radius: 8px;
                    padding: 5px;
                }
            """)
            self.lcdNumber.setDigitCount(1)
            self.horizontalLayout.addWidget(self.lcdNumber)
            
            self.lcdNumber_2 = QtWidgets.QLCDNumber(self.widget_2)
            self.lcdNumber_2.setStyleSheet("""
                QLCDNumber {
                    background-color: transparent;
                    color: #ff8b00;
                    border: 2px solid #5ce1e6;
                    border-radius: 8px;
                    padding: 5px;
                }
            """)
            self.lcdNumber_2.setDigitCount(1)
            self.horizontalLayout.addWidget(self.lcdNumber_2)
            
            # Separator
            self.label_3 = QtWidgets.QLabel(self.widget_2)
            font = QtGui.QFont()
            font.setPointSize(int(100*self.scale))
            self.label_3.setFont(font)
            self.label_3.setStyleSheet("color: #ff8b00;")
            self.label_3.setText(":")
            self.label_3.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop)
            self.horizontalLayout.addWidget(self.label_3)
            
            self.lcdNumber_3 = QtWidgets.QLCDNumber(self.widget_2)
            self.lcdNumber_3.setStyleSheet("""
                QLCDNumber {
                    background-color: transparent;
                    color: #ff8b00;
                    border: 2px solid #5ce1e6;
                    border-radius: 8px;
                    padding: 5px;
                }
            """)
            self.lcdNumber_3.setDigitCount(1)
            self.horizontalLayout.addWidget(self.lcdNumber_3)
            
            self.lcdNumber_4 = QtWidgets.QLCDNumber(self.widget_2)
            self.lcdNumber_4.setStyleSheet("""
                QLCDNumber {
                    background-color: transparent;
                    color: #ff8b00;
                    border: 2px solid #5ce1e6;
                    border-radius: 8px;
                    padding: 5px;
                }
            """)
            self.lcdNumber_4.setDigitCount(1)
            self.horizontalLayout.addWidget(self.lcdNumber_4)
            
            self.widget_2.setLayout(self.horizontalLayout)
            self.set_lcd(0)
            
            # Leaderboard table (exact CatchTheStick.py positioning for Active_screen)
            self.frame_2 = QtWidgets.QFrame(self.centralwidget)
            self.frame_2.setGeometry(QtCore.QRect(200*self.scale, 720*self.scale, 650*self.scale, 415*self.scale))
            self.gridLayout = QtWidgets.QGridLayout(self.frame_2)
            self.tableWidget_2 = QtWidgets.QTableWidget(self.frame_2)
            self.tableWidget_2.setRowCount(5)
            self.tableWidget_2.setColumnCount(2)
            
            # Table styling - original CatchTheStick
            font = QtGui.QFont()
            font.setFamily(self.font_family_good)
            font.setPointSize(int(25*self.scale))
            self.tableWidget_2.setFont(font)
            self.tableWidget_2.setStyleSheet("""
                /* QTableWidget Styling */
                QTableWidget {
                    background-color: transparent;  /* Transparent background */
                    color: #ffffff;  /* White text color */
                    gridline-color: #3b5998;  /* Medium muted blue gridline color */
                    selection-background-color: transparent;  /* Transparent selection background */
                    selection-color: #ffffff;  /* White selection text color */
                    border: 1px solid #3b5998;  /* Border around the table */
                    border-radius: 4px;  /* Rounded corners */
                    padding: 4px;  /* Padding inside the table */
                    margin: 8px;  /* Margin around the table */
                }

                QHeaderView::section { 
                    background-color: #001f3f;  /* Dark blue background for header sections */
                    color: #ffffff;  /* White text color for header sections */
                    padding: 5px;  /* Padding for header sections */
                    border: 1px solid #3b5998;  /* Border color to match table */
                }

                QHeaderView {
                    background-color: transparent;  /* Transparent background */
                }

                QTableCornerButton::section {
                    background-color: transparent;  /* Transparent background */
                }

                QTableWidget::item {
                    padding: 4px;  /* Padding for items */
                    border: none;  /* No border for items */
                }

                QTableWidget::item:selected {
                    background-color: transparent;  /* Transparent background for selected items */
                    color: #2e4053;  /* Blue text color for selected items */
                }

                QTableWidget::item:hover {
                    background-color: #001f3f;  /* Dark blue background on hover */
                }
            """)
            
            # Set headers
            self.tableWidget_2.setHorizontalHeaderLabels(["Player", "Score"])
            for i in range(5):
                for j in range(2):
                    item = QtWidgets.QTableWidgetItem()
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    self.tableWidget_2.setItem(i, j, item)
                # Set player names
                player_item = QtWidgets.QTableWidgetItem(f"Player {i+1}")
                player_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.tableWidget_2.setItem(i, 0, player_item)
                score_item = QtWidgets.QTableWidgetItem("0")
                score_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.tableWidget_2.setItem(i, 1, score_item)
            
            # Apply original CatchTheStick palette configuration
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
            self.tableWidget_2.setPalette(palette)
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
            # hide scrollbar
            self.tableWidget_2.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.tableWidget_2.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            # set font of table
            self.tableWidget_2.setFont(font)
            self.tableWidget_2.setFocusPolicy(QtCore.Qt.NoFocus)
            self.gridLayout.addWidget(self.tableWidget_2, 0, 0, 1, 1)
            MainWindow.setCentralWidget(self.centralwidget)
            
            logger.debug("✅ Active_screen setup completed")
            
        except Exception as e:
            logger.error(f"❌ Error setting up Active_screen: {e}")
    
    def set_lcd(self, value):
        """Set LCD display values"""
        try:
            minutes = value // 60
            seconds = value % 60
            min_tens = minutes // 10
            min_ones = minutes % 10
            sec_tens = seconds // 10
            sec_ones = seconds % 10
            
            if hasattr(self, 'lcdNumber'):
                self.lcdNumber.display(min_tens)
            if hasattr(self, 'lcdNumber_2'):
                self.lcdNumber_2.display(min_ones)
            if hasattr(self, 'lcdNumber_3'):
                self.lcdNumber_3.display(sec_tens)
            if hasattr(self, 'lcdNumber_4'):
                self.lcdNumber_4.display(sec_ones)
        except Exception as e:
            logger.warning(f"⚠️  Error setting LCD: {e}")
    
    def closeEvent(self, event):
        logger.info("🔄 Active screen closing...")
        
        # Stop game timer
        if hasattr(self, 'TimerGame') and self.TimerGame:
            try:
                self.TimerGame.stop()
                try:
                    self.TimerGame.timeout.disconnect()
                except:
                    pass
                self.TimerGame = None
                logger.debug("✅ Game timer cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error stopping timer: {e}")
        
        # Stop MQTT thread
        if hasattr(self, 'mqtt_thread') and self.mqtt_thread:
            try:
                self.mqtt_thread.stop()
                self.mqtt_thread = None
                logger.debug("✅ MQTT thread cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error stopping MQTT: {e}")
        
        # Stop movie
        if hasattr(self, 'movie') and self.movie:
            try:
                self.movie.stop()
                self.movie.setCacheMode(QMovie.CacheNone)
                self.movie = None
                logger.debug("✅ Movie cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error stopping movie: {e}")
        
        # Stop media player
        if hasattr(self, 'player') and self.player:
            try:
                self.player.stop()
                try:
                    self.player.mediaStatusChanged.disconnect()
                except:
                    pass
                self.player = None
                logger.debug("✅ Media player cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error stopping player: {e}")
        
        # Clear background
        if hasattr(self, 'Background') and self.Background:
            try:
                self.Background.clear()
                logger.debug("✅ Background cleared")
            except Exception as e:
                logger.warning(f"⚠️  Error clearing background: {e}")
        
        # Clean up table widget
        if hasattr(self, 'tableWidget_2') and self.tableWidget_2:
            try:
                self.tableWidget_2.hide()
                self.tableWidget_2.clear()
                self.tableWidget_2.close()
                self.tableWidget_2.deleteLater()
                self.tableWidget_2 = None
                logger.debug("✅ Table widget cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Error cleaning table widget: {e}")
        
        # Close main widget
        try:
            if hasattr(self, 'centralwidget'):
                self.centralwidget.close()
                self.centralwidget.deleteLater()
            self.close()
            logger.debug("✅ Active screen closed successfully")
        except Exception as e:
            logger.warning(f"⚠️  Error closing active screen: {e}")
        
        event.accept()
        super().closeEvent(event)


class MainApp(QtWidgets.QMainWindow):
    """Complete Main Application with all screens and new API integration for FalconGrasp"""
    
    def __init__(self):
        super().__init__()
        logger.info("🚀 MainApp initializing with complete UI and new API...")
        
        # Setup window
        self.sized = QtWidgets.QDesktopWidget().screenGeometry()
        self.ui_final = Final_Screen()
        self.ui_home = Home_screen()
        self.ui_active = Active_screen()

        # Setup mainWindow
        self.mainWindow = QtWidgets.QMainWindow()
        self.mainWindow.setObjectName("Home")
        self.mainWindow.setWindowTitle("FalconGrasp - Complete")
        self.mainWindow.setFixedSize(1080, 1920)
        # self.mainWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint )
        
        # Initialize GameManager with new API
        try:
            self.game_manager = GameManager()
            logger.info("✅ GameManager initialized with new API")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GameManager: {e}")
            raise
            
        # Connection signals for the game manager Documentation
        # 1. init_signal: Triggered when the game manager is initialized
        self.game_manager.init_signal.connect(self.start_Active_screen)
        # 2. start_signal: Triggered when the game manager starts
        self.game_manager.start_signal.connect(lambda: (
            self.ui_active.mqtt_thread.subscribe_to_data_topics() if hasattr(self.ui_active, 'mqtt_thread') else None,
            self.ui_active.start_game() if hasattr(self.ui_active, 'start_game') else None,
            logger.info("🚀 Game started signal received")
        ))
        # 3. cancel_signal: Triggered when the game manager is cancelled
        self.game_manager.cancel_signal.connect(lambda: (
            self.ui_active.mqtt_thread.unsubscribe_from_data_topics() if hasattr(self.ui_active, 'mqtt_thread') else None,
            logger.info("🚫 Game cancelled signal received"),
            self.start_Home_screen()
        ))
        # 4. submit_signal: Triggered when the game manager is submitted
        self.game_manager.submit_signal.connect(self.start_final_screen)
        
        # 5. deactivate_signal: Triggered when the game manager is deactivated
        if hasattr(self.ui_active, 'mqtt_thread'):
            self.ui_active.mqtt_thread.deactivate_signal.connect(
                lambda: setattr(self.game_manager, 'submit_score_flag', True) if hasattr(self.game_manager, 'submit_score_flag') else None
            )
        
        # Start with home screen
        self.start_Home_screen()
        """
        @comment: keep this for testing the game manager
        """
        # ------------------------------
        # self.start_Active_screen()
        # self.ui_active.mqtt_thread.subscribe_to_data_topics()
        # self.ui_active.start_game()
        # ------------------------------
        # self.start_final_screen()

        # Start game manager after delay 
        # Start game manager after delay
        QtCore.QTimer.singleShot(15000, self.game_manager.start)
        
        logger.info("✅ MainApp initialization complete")
        logger.info("🎉 FalconGrasp application started successfully!")

    def start_Home_screen(self):
        """Start Home Screen with comprehensive error handling"""
        logger.info("🏠 Starting Home Screen")
        try:
            # Close any current screens safely
            self._close_current_screen()
            
            # Setup and show home screen
            self.ui_home.setupUi(self.mainWindow)
            self.mainWindow.show()
            logger.debug("✅ Home screen started successfully")
        except Exception as e:
            logger.error(f"❌ Error starting home screen: {e}")
    
    def start_Active_screen(self):
        """Start Active Screen with comprehensive error handling"""
        logger.info("🎮 Starting Active Screen")
        try:
            # Close any current screens safely
            self._close_current_screen()
            
            # Setup and show active screen
            self.ui_active.setupUi(self.mainWindow)
            self.mainWindow.show()
            logger.debug("✅ Active screen started successfully")
        except Exception as e:
            logger.error(f"❌ Error starting active screen: {e}")
    
    def start_final_screen(self):
        """Start Final Screen with comprehensive error handling"""
        logger.info("🏆 Starting Final Screen")
        try:
            # Close any current screens safely
            self._close_current_screen()
            
            # Setup and show final screen
            self.ui_final.setupUi(self.mainWindow)
            self.mainWindow.show()
            logger.debug("✅ Final screen started successfully")
            
            # Set up automatic transition back to home screen after final_screen_timer_idle
            logger.info(f"⏰ Setting final screen auto-transition timer: {final_screen_timer_idle}ms")
            QtCore.QTimer.singleShot(final_screen_timer_idle, lambda: (
                self.ui_final.close() if hasattr(self, 'ui_final') and self.ui_final is not None and self.ui_final.isVisible() else None,
                self.start_Home_screen() if hasattr(self, 'ui_final') and self.ui_final is not None and not self.ui_final.isVisible() else None
            ))
            
        except Exception as e:
            logger.error(f"❌ Error starting final screen: {e}")
    
    def _close_current_screen(self):
        """Safely close any currently active screen"""
        try:
            # Clear central widget content
            central_widget = self.mainWindow.centralWidget()
            if central_widget:
                central_widget.hide()
                central_widget.close()
                central_widget.deleteLater()
        except Exception as e:
            logger.warning(f"⚠️  Error closing current screen: {e}")
    
    def _cleanup_all_screens(self):
        """Comprehensive cleanup of all UI screens"""
        logger.debug("🔄 Cleaning up all screens...")
        
        # Close all UI screens
        for screen_name in ['ui_final', 'ui_home', 'ui_active']:
            if hasattr(self, screen_name):
                try:
                    screen = getattr(self, screen_name)
                    if screen:
                        screen.close()
                        screen.deleteLater()
                    logger.debug(f"✅ {screen_name} closed")
                except Exception as e:
                    logger.warning(f"⚠️  Error closing {screen_name}: {e}")
        
        logger.debug("✅ All screens cleaned up")

    def close_application(self):
        """Comprehensive application cleanup and shutdown"""
        logger.info("🛑 Closing FalconGrasp application with comprehensive cleanup...")
        
        try:
            # Stop GameManager thread first
            if hasattr(self, 'game_manager') and self.game_manager:
                try:
                    self.game_manager.stop_manager()
                    logger.debug("✅ GameManager stopped")
                except Exception as e:
                    logger.warning(f"⚠️  Error stopping GameManager: {e}")
            
            # Close main window
            if hasattr(self, 'mainWindow') and self.mainWindow:
                try:
                    self.mainWindow.close()
                    logger.debug("✅ Main window closed")
                except Exception as e:
                    logger.warning(f"⚠️  Error closing main window: {e}")
            
            # Close all UI screens
            for screen_name in ['ui_final', 'ui_home', 'ui_active']:
                if hasattr(self, screen_name):
                    try:
                        screen = getattr(self, screen_name)
                        if screen:
                            screen.close()
                            screen.deleteLater()
                        logger.debug(f"✅ {screen_name} closed")
                    except Exception as e:
                        logger.warning(f"⚠️  Error closing {screen_name}: {e}")
            
            # Quit application
            logger.info("✅ FalconGrasp application cleanup completed")
            QtWidgets.QApplication.quit()
            
        except Exception as e:
            logger.error(f"❌ Error during application cleanup: {e}")
            QtWidgets.QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        main_app = MainApp()
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"❌ Fatal error in FalconGrasp application: {e}")
        sys.exit(1)
