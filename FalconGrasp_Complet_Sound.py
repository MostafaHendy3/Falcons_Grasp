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
import json

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


# import New Sound Service
from utils.audio_service import AudioPlayer
from utils.audio_service import AudioService
from utils.audio_service import AudioServiceThread

# # Try to import PyQt5 multimedia with error handling
# try:
#     from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
#     multimedia_available = True
# except Exception as e:
#     print(f"  PyQt5 multimedia not available: {e}")
#     multimedia_available = False
#     # Create dummy classes for compatibility
#     class QMediaPlayer:
#         def __init__(self, *args, **kwargs):
#             pass
#         def setMedia(self, *args, **kwargs):
#             pass
#         def play(self, *args, **kwargs):
#             pass
#         def stop(self, *args, **kwargs):
#             pass
#     class QMediaContent:
#         def __init__(self, *args, **kwargs):
#             pass

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
    logger.info("============================================================")
    logger.info(" STARTING FALCONGRASP GAME WITH COMPLETE UI AND NEW API")
    logger.info("============================================================")
    logger.info(f" Logs are being saved to: {log_file}")
    
    def trace_flags(location, game_manager=None):
        """Comprehensive flag tracing utility"""
        global gameStarted, gameRunning, homeOpened, list_players_id, list_players_score
        
        logger.info(f" FLAG TRACE [{location}]:")
        logger.info(f"    Global flags: gameStarted={gameStarted}, gameRunning={gameRunning}, homeOpened={homeOpened}")
        logger.info(f"    Players: count={len(list_players_id)}, scores={list_players_score[:4]}")
        logger.info(f"    Player IDs: {list_players_id[:4] if len(list_players_id) >= 4 else list_players_id}")
        
        if game_manager:
            logger.info(f"    GameManager: started_flag={game_manager.started_flag}, cancel_flag={game_manager.cancel_flag}")
            logger.info(f"    GameManager: submit_score_flag={game_manager.submit_score_flag}, game_result_id={game_manager.game_result_id}")
        
        # CRITICAL: Ensure we always have exactly 5 players
        if len(list_players_id) != 4:
            logger.warning(f"  PLAYER COUNT MISMATCH: Expected 4, got {len(list_players_id)}")
        if len(list_players_score) != 4:
            logger.warning(f"  SCORE COUNT MISMATCH: Expected 4, got {len(list_players_score)}")
        
        logger.info(f" END FLAG TRACE [{location}]")
except ImportError as e:
    # Fallback logging if our modules aren't available
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f" Failed to import game modules: {e}")
    logger.error(" Please ensure config.py, utils/, and api/ are available")
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
    "[4] Player4"   # Temporary name 4
]
list_players_id = []
list_top5_FalconGrasp = []
finalscore = 0
list_players_score = [0,0,0,0]
gameStarted = False
gameRunning = False

# Initialize leaderboard
try:
    api = GameAPI()
    if api.authenticate():
        logger.info(" API authentication successful")
        logger.info(" Loading initial leaderboard for 'Falcon's Grasp'...")
        leaderboard = api.get_leaderboard("Falcon's Grasp")
        list_top5_FalconGrasp.extend(leaderboard)
        logger.info(f" Initial leaderboard loaded: {len(leaderboard)} entries")
        if leaderboard:
            logger.info(" Top teams:")
            for i, (team_name, score) in enumerate(leaderboard[:5], 1):
                logger.info(f"   {i}. {team_name} - {score:,} points")
    else:
        logger.warning("  Failed to authenticate for initial leaderboard")
except Exception as e:
    logger.error(f" Error loading initial leaderboard: {e}")

# FalconGrasp uses MQTT-based detection instead of ML models
logger.info(" FalconGrasp detection system initialized (MQTT-based)")



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
        self.connected = False  # Track connection status
        
        # Set up callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        logger.debug(" MqttThread initialized")

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            logger.info(f" MQTT connected successfully to {self.broker}:{self.port}")
            
            # Subscribe to control topics immediately upon connection
            for topic in self.control_topics:
                client.subscribe(topic)
                logger.debug(f" Subscribed to control topic: {topic}")
            
            logger.info(f" Subscribed to {len(self.control_topics)} control topics")
        else:
            self.connected = False
            logger.error(f" MQTT connection failed with code: {rc}")

    def on_disconnect(self, client, userdata, rc, properties=None):
        self.connected = False
        self.subscribed = False
        logger.warning(f" MQTT disconnected (rc: {rc})")

    def on_message(self, client, userdata, msg, properties=None):
        try:
            topic = msg.topic
            message = msg.payload.decode()
            logger.debug(f" MQTT message received: {topic} = {message}")
            
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
                    logger.warning(f"  Invalid timer value: {message}")
            elif topic == "FalconGrasp/game/timerfinal":
                try:
                    global final_screen_timer_idle
                    final_screen_timer_idle = int(message) * 1000
                except ValueError:
                    logger.warning(f"  Invalid final timer value: {message}")
            else:
                # Handle data messages for camera topics
                if self.subscribed:
                    self.handle_data_message(msg)
        except Exception as e:
            logger.warning(f"  Error processing MQTT message: {e}")
    
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
            logger.warning(f"  Error handling data message: {e}")
    
    def handle_restart(self):
        logger.debug("Game restarted")
        self.restart_signal.emit()
    
    def handle_start(self):
        logger.debug("Game started")
        # Set global gameStarted to True when game starts via MQTT
        global gameStarted
        gameStarted = True
        logger.info("Game started via MQTT - gameStarted set to True")
        self.subscribe_to_data_topics()
        self.start_signal.emit()
    
    def handle_activate(self):
        logger.debug("Game activated")
        self.activate_signal.emit()
    
    def handle_stop(self):
        logger.debug("Game stopped")
        # Set global gameStarted to False so API polling will stop
        global gameStarted
        gameStarted = False
        logger.info(" Game stopped via MQTT - gameStarted set to False")
        self.stop_signal.emit()

    def run(self):
        """MQTT thread main loop with error handling"""
        try:
            logger.debug(" Starting MQTT connection...")
            self.client.connect(self.broker, self.port, 60)
            logger.debug(" MQTT connected successfully")
            self.client.loop_forever()
        except Exception as e:
            logger.error(f" MQTT connection error: {e}")
        finally:
            logger.debug(" MQTT thread run() method exiting")

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
        logger.debug(" Stopping MqttThread...")
        
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
                    self.connected = False
                    logger.debug(" MQTT topics unsubscribed")
                except Exception as e:
                    logger.warning(f"  Error unsubscribing MQTT topics: {e}")
                
                # Disconnect from broker
                try:
                    self.client.disconnect()
                    logger.debug(" MQTT client disconnected")
                except Exception as e:
                    logger.warning(f"  Error disconnecting MQTT client: {e}")
            
            # Stop the thread loop
            if self.isRunning():
                self.quit()
                if not self.wait(5000):  # Wait up to 5 seconds
                    logger.warning("  MqttThread did not finish gracefully")
                else:
                    logger.debug(" MqttThread stopped gracefully")
                    
        except Exception as e:
            logger.warning(f"  Error stopping MQTT thread: {e}")


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
        logger.info(" GameManager initializing...")
        
        # Initialize the GameAPI
        try:
            self.api = GameAPI()
            logger.info(" GameAPI initialized successfully")
        except Exception as e:
            logger.error(f" Failed to initialize GameAPI: {e}")
            raise
            
        # Game state
        self.game_result_id = None
        self.submit_score_flag = False
        self.playStatus = True
        self.started_flag = False
        self.cancel_flag = False
        self.game_done = True
        
        logger.info(" GameManager initialized successfully")
        
    def run(self):
        """Main game loop following the proper API flow"""
        logger.info("GameManager starting main loop...")
        
        while self.playStatus:
            try:
                # Manual reset of essential flags only for new game cycle
                logger.info(" Manual reset of essential flags for new game cycle...")
                logger.info(f" BEFORE reset - started_flag: {self.started_flag}")
                self.game_result_id = None
                self.submit_score_flag = False
                self.started_flag = False  # CRITICAL: Reset to False like CAGE_Game.py __init__
                self.cancel_flag = False
                
                # Double check that started_flag is False
                logger.info(f" AFTER reset - started_flag: {self.started_flag}")
                logger.info(f" All flags: game_result_id={self.game_result_id}, submit_score_flag={self.submit_score_flag}, started_flag={self.started_flag}, cancel_flag={self.cancel_flag}")
                
                trace_flags("GAME_CYCLE_START", self)
                
                # Step 1: Authenticate
                logger.info(" Step 1: Authenticating...")
                if not self.api.authenticate():
                    logger.error(" Authentication failed, retrying in 5 seconds...")
                    time.sleep(5)
                    continue
                
                # Step 2: Poll for game initialization
                logger.info(" Step 2: Polling for game initialization...")
                if not self._poll_initialization():
                    # If initialization fails, reset only essential flags
                    logger.info(" Initialization failed, resetting essential flags...")
                    self.game_result_id = None
                    self.cancel_flag = False
                    continue
                
                # Step 3: Poll for game start
                logger.info("Step 3: Polling for game start...")
                logger.info(f" started_flag before polling: {self.started_flag}")
                
                if not self._poll_game_start():
                    # If game start fails (e.g., cancellation), reset only essential flags
                    logger.info(" Game start failed/cancelled, resetting essential flags...")
                    self.game_result_id = None
                    self.started_flag = False
                    self.cancel_flag = False
                    continue
                
                # Step 4: Wait for game completion and submit scores
                logger.info(" Step 4: Waiting for game completion...")
                if not self._wait_and_submit_scores():
                    # If score submission fails, reset only essential flags
                    logger.info(" Score submission failed, resetting essential flags...")
                    self.submit_score_flag = False
                    self.started_flag = False
                    continue
                    
            except Exception as e:
                logger.error(f" Error in game loop: {e}")
                logger.info(" Exception occurred, resetting essential flags...")
                self.game_result_id = None
                self.submit_score_flag = False
                self.started_flag = False
                self.cancel_flag = False
                time.sleep(5)
                continue
    
    def _poll_initialization(self) -> bool:
        """Poll for game initialization"""
        while self.playStatus:
            try:
                game_data = self.api.poll_game_initialization()
                if game_data:
                    self.game_result_id = game_data.get('id')
                    
                    # Extract team and player information
                    global teamName, list_players_name, list_players_id
                    teamName = game_data.get('name', 'Unknown Team')
                    
                    # Extract player info from nodeIDs
                    node_ids = game_data.get('nodeIDs', [])
                    list_players_name = [player.get('name', f'Player {i+1}') for i, player in enumerate(node_ids)]
                    list_players_id = [player.get('userID', f'user_{i+1}') for i, player in enumerate(node_ids)]
                    
                    logger.info(f" Game initialized: {self.game_result_id}")
                    logger.info(f" Team: {teamName}")
                    logger.info(f" Players: {list_players_name}")
                    
                    # CRITICAL: Ensure exactly 4 players for FalconGrasp
                    if len(list_players_id) != 4:
                        logger.warning(f"  API returned {len(list_players_id)} players, FalconGrasp needs exactly 4!")
                        # Pad to 4 players
                        while len(list_players_id) < 4:
                            player_num = len(list_players_id) + 1
                            list_players_id.append(f'falcon_player_{player_num}')
                            list_players_name.append(f'Player {player_num}')
                        # Trim to 4 players if more than 4
                        list_players_id = list_players_id[:4]
                        list_players_name = list_players_name[:4]
                        logger.info(f" Fixed player count to 4: {list_players_id}")
                    
                    trace_flags("GAME_INITIALIZATION", self)
                    
                    # Check if home screen is ready
                    global homeOpened
                    if homeOpened:
                        logger.info(" Home screen ready, emitting init signal")
                        homeOpened = False
                        self.init_signal.emit()
                        return True
                    else:
                        logger.info(" Waiting for home screen to be ready...")
                
                time.sleep(3)  # Poll every 3 seconds
                
            except Exception as e:
                logger.error(f" Error polling initialization: {e}")
                time.sleep(5)
                
        return False
    
    def _poll_game_start(self) -> bool:
        """Poll for game start and continue monitoring during gameplay - Like CAGE_Game.py"""
        if not self.game_result_id:
            logger.error(" No game result ID available")
            return False
        
        logger.info(f" Starting polling with started_flag={self.started_flag}, cancel_flag={self.cancel_flag}")
        logger.info("Starting continuous polling for game start...")
        
        # Create a simple reference object to avoid lambda timing issues
        class FlagRef:
            def __init__(self, manager):
                self.manager = manager
            def __call__(self):
                return self.manager.started_flag
        
        flag_ref = FlagRef(self)
        
        try:
            # Phase 1: Wait for game to start
            game_data = self.api.poll_game_start_continuous(
                game_result_id=self.game_result_id,
                submit_score_flag_ref=lambda: self.submit_score_flag,
                started_flag_ref=flag_ref,
                cancel_flag_ref=lambda x: setattr(self, 'cancel_flag', x)
            )
            
            if game_data:
                status = game_data.get('status')
                logger.info(f" First polling phase completed with status: {status}")
                
                if status == 'playing':
                    # Game started! Emit start signal
                    logger.info("" + "=" * 50)
                    logger.info("GAME START SIGNAL RECEIVED - EMITTING START!")
                    logger.info(f" Previous started_flag value: {self.started_flag}")
                    logger.info("" + "=" * 50)
                    
                    # CRITICAL: Set started_flag to True BEFORE emitting signal
                    # This ensures subsequent 'playing' responses won't trigger another start
                    self.started_flag = True
                    logger.info(f" started_flag set to True BEFORE emitting signal: {self.started_flag}")
                    
                    trace_flags("GAME_START_SIGNAL_EMIT", self)
                    
                    # Emit the start signal
                    self.start_signal.emit()
                    
                    
                    logger.info(" Start signal emitted successfully!")
                    logger.info(" Now subsequent 'playing' responses will be ignored")
                    
                    # Phase 2: Continue monitoring during gameplay
                    logger.info(" Game started - continuing to monitor for cancellation...")
                    return self._monitor_during_gameplay()
                    
                elif status == 'cancel' or game_data.get('cancelled'):
                    logger.warning("  Game cancelled before starting")
                    self.cancel_flag = True
                    # CRITICAL: Reset started_flag IMMEDIATELY before emitting cancel
                    self.started_flag = False
                    logger.warning(f" started_flag reset to False before cancel: {self.started_flag}")
                    self.cancel_signal.emit()
                    # Manual reset of essential flags only
                    self.game_result_id = None
                    self.submit_score_flag = False
                    return False
                elif status == 'submit_triggered':
                    logger.info(" Score submission triggered before game start")
                    return True
                else:
                    logger.warning(f"  Unexpected status: {status}")
                    return False
            else:
                logger.warning("  No game data returned from continuous polling")
                return False
                
        except Exception as e:
            logger.error(f" Error in game start polling: {e}")
            return False
    
    def _monitor_during_gameplay(self) -> bool:
        """Continue monitoring for cancellation during active gameplay"""
        logger.info(" Monitoring for cancellation during gameplay...")
        
        try:
            # Create a callback to check if game has stopped
            def game_stopped_check():
                # Only check if game has stopped AFTER it has actually started
                # This prevents race condition where polling starts before UI sets gameStarted=True
                global gameStarted
                
                # First, give the UI thread time to process the start signal
                # Only check for stop if we're confident the game was actually running
                import time
                current_time = time.time()
                if not hasattr(game_stopped_check, 'start_time'):
                    game_stopped_check.start_time = current_time
                
                # Only start checking for game stop after 2 seconds of polling
                if current_time - game_stopped_check.start_time < 2.0:
                    return False
                
                # Now check if game has actually stopped (timers stopped)
                if not gameStarted:
                    logger.info(" Game timers stopped (gameStarted=False) - stopping API polling")
                    return True
                    
                return False
            
            # Continue continuous polling during gameplay with stop check
            game_data = self.api.poll_game_start_continuous(
                game_result_id=self.game_result_id,
                submit_score_flag_ref=lambda: self.submit_score_flag,
                started_flag_ref=lambda: self.started_flag,
                cancel_flag_ref=lambda x: setattr(self, 'cancel_flag', x),
                game_stopped_check=game_stopped_check
            )
            
            if game_data:
                status = game_data.get('status')
                logger.info(f" Gameplay monitoring completed with status: {status}")
                
                if status == 'cancel' or game_data.get('cancelled'):
                    logger.warning("  Game cancelled during gameplay")
                    self.cancel_flag = True
                    # CRITICAL: Reset started_flag IMMEDIATELY before emitting cancel
                    self.started_flag = False
                    logger.warning(f" started_flag reset to False during gameplay cancel: {self.started_flag}")
                    self.cancel_signal.emit()
                    # Manual reset of essential flags only
                    self.game_result_id = None
                    self.submit_score_flag = False
                    return False
                elif status == 'game_stopped':
                    logger.info(" Game stopped naturally - polling terminated successfully")
                    return True
                elif status == 'submit_triggered':
                    logger.info(" Score submission triggered during gameplay")
                    return True
                else:
                    logger.debug(f" Gameplay monitoring ended with status: {status}")
                    return True
            else:
                logger.warning("  No data from gameplay monitoring")
                return True
                
        except Exception as e:
            logger.error(f" Error in gameplay monitoring: {e}")
            return True
    
    def _wait_and_submit_scores(self) -> bool:
        """Wait for game completion and submit scores"""
        logger.info(" Waiting for score submission flag or cancellation...")
        logger.info(f" Current flags: submit_score_flag={self.submit_score_flag}, cancel_flag={self.cancel_flag}")
        
        while self.playStatus and not self.cancel_flag:
            if self.submit_score_flag:
                logger.info(" submit_score_flag detected! Processing score submission...")
                trace_flags("SCORE_SUBMISSION_START", self)
                try:
                    # Prepare individual scores for FalconGrasp
                    global scored, list_players_score, list_players_id
                    individual_scores = self._prepare_individual_scores(scored, list_players_score, list_players_id)
                    
                    #  SAVE PLAYER DATA TO CSV FIRST (before API submission)
                    logger.info(" Saving FalconGrasp player data to CSV before API submission...")
                    self._save_individual_players_csv(self.game_result_id, individual_scores, None)  # None = pre-submission
                    self._save_pre_submission_log(self.game_result_id, individual_scores)
                    logger.info(" FalconGrasp player data saved locally before submission")
                    
                    # Submit scores using original method (keep as main submitter)
                    logger.info("Now submitting FalconGrasp scores to API...")
                    success = self.api.submit_final_scores(self.game_result_id, individual_scores)
                    
                    # Save player CSV with final submission status (after API submission)
                    self._save_individual_players_csv(self.game_result_id, individual_scores, success)
                    
                    if success:
                        logger.info(" Scores submitted successfully")
                        # Get updated leaderboard
                        self._update_leaderboard()
                        self.submit_signal.emit()
                        # Manual reset of essential flags only
                        self.game_result_id = None
                        self.submit_score_flag = False
                        self.started_flag = False
                        return True
                    else:
                        logger.error(" Failed to submit scores")
                        time.sleep(5)
                        
                except Exception as e:
                    logger.error(f" Error submitting scores: {e}")
                    time.sleep(5)
            else:
                # Periodic debug logging every 10 seconds
                import time
                current_time = time.time()
                if not hasattr(self, '_last_wait_log') or current_time - self._last_wait_log > 10:
                    logger.info(f" Still waiting... submit_score_flag={self.submit_score_flag}, cancel_flag={self.cancel_flag}")
                    self._last_wait_log = current_time
                time.sleep(1)  # Check every second for score submission flag
                
        return False
    
    def _prepare_individual_scores(self, total_score: int, player_scores: list, player_ids: list) -> list:
        """Prepare individual scores in the required format for FalconGrasp - 4 players"""
        if not player_ids:
            logger.warning("  No player IDs available, using default")
            player_ids = ["default_user", "default_user", "default_user", "default_user"]
        print(f" Player IDs: {player_ids}")
        individual_scores = []
        
        # For FalconGrasp, use individual player scores if available
        if player_scores and len(player_scores) >= len(player_ids):
            for i, score in enumerate(player_scores[:len(player_ids)]):
                print(f" Score: {score}")
                user_id = player_ids[i] if i < len(player_ids) else f"user_{i+1}"
                individual_scores.append({
                    "userID": user_id,
                    "nodeID": i + 1,
                    "score": score
                })
        else:
            # Fallback: distribute total score among players
            base_score = total_score // len(player_ids)
            remainder = total_score % len(player_ids)
            
            for i, user_id in enumerate(player_ids):
                score = base_score + (remainder if i == 0 else 0)
                individual_scores.append({
                    "userID": user_id,
                    "nodeID": i + 1,
                    "score": score
                })
        
        logger.info(f" Prepared scores for {len(individual_scores)} players")
        return individual_scores
    
    def _save_individual_players_csv(self, game_result_id: str, individual_scores: list, success: bool):
        """Save individual player scores for database revision"""
        try:
            csv_filename = "Falcon_Individual_Players_Log.csv"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if file exists to determine if we need headers
            file_exists = os.path.exists(csv_filename)
            
            with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'timestamp', 'game_result_id', 'user_id', 'node_id', 
                    'individual_score', 'submission_success', 'status'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                    logger.info(f" Created new individual players log file: {csv_filename}")
                
                # Determine status based on success parameter
                if success is None:
                    status = "pre_submission"
                elif success:
                    status = "submitted_success"
                else:
                    status = "submitted_failed"
                
                # Write one row per player
                for score_data in individual_scores:
                    writer.writerow({
                        'timestamp': timestamp,
                        'game_result_id': game_result_id,
                        'user_id': score_data.get('userID', 'Unknown'),
                        'node_id': score_data.get('nodeID', 'N/A'),
                        'individual_score': score_data.get('score', 0),
                        'submission_success': success,
                        'status': status
                    })
                
            if success is None:
                logger.info(f" Player data saved to {csv_filename} BEFORE API submission")
            else:
                logger.info(f" Player data status updated in {csv_filename} AFTER API submission")
            
        except Exception as e:
            logger.error(f" Error saving individual players log to CSV: {e}")
            # Don't let CSV errors break the game flow
    
    def _save_pre_submission_log(self, game_result_id: str, individual_scores: list):
        """Save a pre-submission log entry for safety"""
        try:
            csv_filename = "Falcon_Pre_Submission_Backup.csv"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if file exists to determine if we need headers
            file_exists = os.path.exists(csv_filename)
            
            with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'timestamp', 'game_result_id', 'total_players', 'total_score', 
                    'player_ids', 'individual_scores_json', 'status'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                    logger.info(f" Created new pre-submission backup file: {csv_filename}")
                
                # Calculate totals
                total_players = len(individual_scores)
                total_score = sum(score_data.get('score', 0) for score_data in individual_scores)
                
                # Create player IDs list
                player_ids = [score_data.get('userID', 'Unknown') for score_data in individual_scores]
                player_ids_str = " | ".join(player_ids)
                
                # Convert individual scores to JSON string for complete backup
                individual_scores_json = json.dumps(individual_scores)
                
                writer.writerow({
                    'timestamp': timestamp,
                    'game_result_id': game_result_id,
                    'total_players': total_players,
                    'total_score': total_score,
                    'player_ids': player_ids_str,
                    'individual_scores_json': individual_scores_json,
                    'status': 'saved_before_submission'
                })
                
            logger.info(f" Pre-submission backup saved to {csv_filename}")
            logger.info(f"   Game ID: {game_result_id}")
            logger.info(f"    Players: {total_players}")
            logger.info(f"    Total Score: {total_score}")
            
        except Exception as e:
            logger.error(f" Error saving pre-submission backup: {e}")
            # Don't let CSV errors break the game flow
    
    def _update_leaderboard(self):
        """Update the leaderboard data"""
        try:
            global list_top5_FalconGrasp
            logger.info(" Fetching leaderboard for 'Falcon's Grasp'...")
            leaderboard = self.api.get_leaderboard("Falcon's Grasp")
            logger.info(f" Leaderboard received: {leaderboard}")
            
            list_top5_FalconGrasp.clear()
            list_top5_FalconGrasp.extend(leaderboard)
            
            logger.info(f" Leaderboard updated with {len(leaderboard)} entries")
            
            # Update the UI table if it exists
            if hasattr(self, 'UpdateTable'):
                self.UpdateTable()
                logger.info(" Leaderboard table UI updated")
                
        except Exception as e:
            logger.error(f" Error updating leaderboard: {e}")
    

    
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
        list_players_score = [0,0,0,0]
        gameStarted = False
        gameRunning = False
        
        logger.debug(" Game state reset")
        trace_flags("GAME_STATE_RESET", None)

    def trigger_score_submission(self):
        """Trigger score submission (called when game ends)"""
        logger.info("" + "=" * 50)
        logger.info(" SCORE SUBMISSION TRIGGERED!")
        logger.info("" + "=" * 50)
        logger.info(f" submit_score_flag before: {self.submit_score_flag}")
        self.submit_score_flag = True
        logger.info(f" submit_score_flag after: {self.submit_score_flag}")
        logger.info(" GameManager should now exit monitoring and submit scores")
        
        trace_flags("TRIGGER_SCORE_SUBMISSION", self)
    
    def stop_manager(self):
        """Stop the game manager with comprehensive cleanup"""
        logger.info(" Stopping GameManager...")
        
        try:
            # Stop the game loop
            self.playStatus = False
            
            # Disconnect all signals
            try:
                self.init_signal.disconnect()
                self.start_signal.disconnect()
                self.cancel_signal.disconnect()
                self.submit_signal.disconnect()
                logger.debug(" GameManager signals disconnected")
            except Exception as e:
                logger.warning(f"  Error disconnecting signals: {e}")
            
            # Clean up API object
            if hasattr(self, 'api') and self.api:
                try:
                    # The GameAPI object doesn't have explicit cleanup,
                    # but we can clear the reference
                    self.api = None
                    logger.debug(" GameAPI reference cleared")
                except Exception as e:
                    logger.warning(f"  Error cleaning API: {e}")
            
            # Reset essential flags only
            try:
                self.game_result_id = None
                self.submit_score_flag = False
                self.started_flag = False
                self.cancel_flag = False
                logger.debug(" Essential flags reset")
            except Exception as e:
                logger.warning(f"  Error resetting flags: {e}")
        
        except Exception as e:
            logger.warning(f"  Error in GameManager cleanup: {e}")
        
        # Stop the thread gracefully
        try:
            self.quit()
            if not self.wait(5000):  # Wait up to 5 seconds
                logger.warning("  GameManager thread did not finish gracefully")
                # Don't use terminate() unless absolutely necessary
            logger.debug(" GameManager stopped successfully")
        except Exception as e:
            logger.warning(f"  Error stopping GameManager thread: {e}")


class Final_Screen(QtWidgets.QMainWindow):
    """Complete Final Screen implementation with professional styling"""
    
    def __init__(self):
        super().__init__()
        self.movie = None
        self.timer = None
        self.timer2 = None
        self.LeaderBoardTable = None
        logger.debug(" Final_Screen initialized")
    
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
        logger.info(" Final screen showing table - refreshing leaderboard data")
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
        self.font_family_good = self.load_custom_font("Assets/Fonts/GOTHICB.ttf")
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
            self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_final_OLD.gif")
        else:
            self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_final_OLD.gif")
        
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

            /* QScrollBar Styling */
            QScrollBar:vertical, QScrollBar:horizontal {
                background-color: #1c2833;  /* Deep muted blue background for scrollbar */
                border: 1px solid #3b5998;  /* Border color */
                border-radius: 4px;  /* Rounded corners */
            }

            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background-color: #2e4053;  /* Darker muted blue handle */
                border-radius: 4px;  /* Rounded corners */
            }

            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background-color: #4c669f;  /* Medium muted blue handle on hover */
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
        self.LeaderBoardTable.verticalHeader().setCascadingSectionResizes(False)
        
        # Calculate flexible row heights for the table height (415px)
        # Total available height: 415px minus header and padding
        available_height = int(415 * self.scale - 80)  # Account for header and padding
        row_height = int(available_height / 5)  # Distribute equally among 5 rows
        
        for i in range(5):
            self.LeaderBoardTable.verticalHeader().resizeSection(i, row_height)
        # self.LeaderBoardTable.verticalHeader().setStretchLastSection(True)
        
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
            logger.debug(f" Final screen updating table with {len(list_top5_FalconGrasp)} entries")
            
            # Clear all rows first
            for i in range(5):
                self.LeaderBoardTable.setItem(i, 0, QtWidgets.QTableWidgetItem(""))
                self.LeaderBoardTable.setItem(i, 1, QtWidgets.QTableWidgetItem(""))
            
            # Sort data by score (descending)
            sorted_data = sorted(list_top5_FalconGrasp, key=lambda item: item[1], reverse=True)
            logger.debug(f" Final screen sorted leaderboard data: {sorted_data}")
            
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
                
            logger.debug(" Final screen leaderboard table updated successfully")
            
        except Exception as e:
            logger.error(f" Error updating final screen leaderboard table: {e}")
    
    def _update_leaderboard(self):
        """Update the leaderboard data from API for final screen"""
        try:
            global list_top5_FalconGrasp
            logger.info(" Final screen fetching leaderboard for 'Falcon's Grasp'...")
            leaderboard = api.get_leaderboard("Falcon's Grasp")
            logger.info(f" Final screen leaderboard received: {leaderboard}")
            
            list_top5_FalconGrasp.clear()
            list_top5_FalconGrasp.extend(leaderboard)
            
            logger.info(f" Final screen leaderboard updated with {len(leaderboard)} entries")
            
            # Update the UI table if it exists
            if hasattr(self, 'UpdateTable'):
                self.UpdateTable()
                logger.info(" Final screen leaderboard table UI updated")
                
        except Exception as e:
            logger.error(f" Error updating final screen leaderboard: {e}")
    
    def closeEvent(self, event):
        logger.info(" Final screen closing...")
        
        # Safely stop movie
        if hasattr(self, 'movie') and self.movie:
            try:
                self.movie.stop()
                self.movie.setCacheMode(QMovie.CacheNone)
                self.movie = None
                logger.debug(" Movie cleaned up")
            except Exception as e:
                logger.warning(f"  Error stopping movie: {e}")
        
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
                logger.debug(" Timer cleaned up")
            except Exception as e:
                logger.warning(f"  Error stopping timer: {e}")
        
        if hasattr(self, 'timer2') and self.timer2:
            try:
                self.timer2.stop()
                try:
                    self.timer2.timeout.disconnect()
                except:
                    pass
                self.timer2 = None
                logger.debug(" Timer2 cleaned up")
            except Exception as e:
                logger.warning(f"  Error stopping timer2: {e}")
        
        # Safely clear background
        if hasattr(self, 'Background') and self.Background:
            try:
                self.Background.clear()
                logger.debug(" Background cleared")
            except Exception as e:
                logger.warning(f"  Error clearing background: {e}")
        
        # Clean up table widget safely
        if hasattr(self, 'LeaderBoardTable') and self.LeaderBoardTable:
            try:
                # Check if table widget is still valid before attempting cleanup
                try:
                    self.LeaderBoardTable.objectName()  # Test if object is still valid
                    self.LeaderBoardTable.hide()
                    self.LeaderBoardTable.clear()
                    self.LeaderBoardTable.close()
                    # Don't call deleteLater() - let Qt handle it automatically
                    self.LeaderBoardTable = None
                    logger.debug(" Table widget cleaned up")
                except RuntimeError:
                    # Table widget already deleted by Qt
                    self.LeaderBoardTable = None
                    logger.debug(" Table widget was already deleted by Qt")
            except Exception as e:
                logger.warning(f"  Error cleaning table widget: {e}")
                self.LeaderBoardTable = None
        
        # Don't manually clean up child widgets - let Qt handle cleanup automatically
        if hasattr(self, 'centralwidget'):
            self.centralwidget = None
            logger.debug(" Central widget reference cleared")
        
        try:
            logger.debug(" Final screen closed successfully")
        except Exception as e:
            logger.warning(f"  Error closing final screen: {e}")
        
        event.accept()
        super().closeEvent(event)

class TeamMember_screen(QtWidgets.QMainWindow):
    """Enhanced Home_screen with comprehensive safety and professional styling"""
    
    def __init__(self):
        super().__init__()
        self.player = None
        self.movie = None
        self.LeaderboardTable = None
        # if multimedia_available:
        #     self.player = QMediaPlayer()
        logger.debug(" Home_screen initialized")
    
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
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_inActive_OLD.gif")
            else:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_inActive_OLD.gif")
            
            self.movie.setCacheMode(QMovie.CacheAll)
            self.Background.setMovie(self.movie)
            self.Background.setScaledContents(True)
            self.movie.start()
            
            # Leaderboard table setup (exact CatchTheStick.py positioning for Home_screen)
            self.frame_2 = QtWidgets.QFrame(self.centralwidget)
            self.frame_2.setGeometry(QtCore.QRect(200*self.scale, 565*self.scale, 650*self.scale, 415*self.scale))
            self.gridLayout = QtWidgets.QGridLayout(self.frame_2)
            self.LeaderboardTable = QtWidgets.QTableWidget(self.frame_2)
            self.LeaderboardTable.setRowCount(4)
            self.LeaderboardTable.setColumnCount(1)
            
            
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

                /* QScrollBar Styling */
                QScrollBar:vertical, QScrollBar:horizontal {
                    background-color: #1c2833;  /* Deep muted blue background for scrollbar */
                    border: 1px solid #3b5998;  /* Border color */
                    border-radius: 4px;  /* Rounded corners */
                }

                QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                    background-color: #2e4053;  /* Darker muted blue handle */
                    border-radius: 4px;  /* Rounded corners */
                }

                QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                    background-color: #4c669f;  /* Medium muted blue handle on hover */
                }
            """)
            
            # Set headers and items
            self.LeaderboardTable.setHorizontalHeaderLabels(["Team", "Score"])
            for i in range(4):
                for j in range(1):
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
            self.LeaderboardTable.horizontalHeader().setDefaultSectionSize(600*self.scale)
            self.LeaderboardTable.horizontalHeader().setMinimumSectionSize(100*self.scale)
            self.LeaderboardTable.horizontalHeader().setStretchLastSection(False)
            self.LeaderboardTable.verticalHeader().setVisible(False)
            self.LeaderboardTable.verticalHeader().setCascadingSectionResizes(False)
            
            # Calculate flexible row heights for the table height (415px)
            # Total available height: 415px minus header and padding
            available_height = int(415 * self.scale - 80)  # Account for header and padding
            row_height = int(available_height / 4)  # Distribute equally among 4 rows
            
            for i in range(4):
                self.LeaderboardTable.verticalHeader().resizeSection(i, row_height)
            # self.LeaderboardTable.verticalHeader().setStretchLastSection(True)
            # Professional table styling
            font = QtGui.QFont()
            font.setFamily(self.font_family_good)
            font.setPointSize(int(22*self.scale))
            self.LeaderboardTable.setFont(font)
            self.LeaderboardTable.setFocusPolicy(QtCore.Qt.NoFocus)
            
            self.gridLayout.addWidget(self.LeaderboardTable, 0, 0, 1, 1)
            Home.setCentralWidget(self.centralwidget)
            
            # # Setup timer2 to call Inactive() after 13 seconds (same as CatchTheStick.py)
            # self.timer2 = QTimer(Home)
            # self.timer2.setTimerType(Qt.PreciseTimer)
            # self.timer2.timeout.connect(self.Inactive)
            # self.timer2.start(11000)  # 11 seconds like CatchTheStick.py
            # logger.info("⏰ Home screen timer2 set for 11 seconds to switch to Inactive state")
            
            self.UpdateTable()
            # Initially hide table - it will be shown by Inactive() after 13 seconds
            # self.LeaderboardTable.hide()
            logger.debug(" Home_screen setup completed")
            
        except Exception as e:
            logger.error(f" Error setting up Home_screen: {e}")
    
    def UpdateTable(self):
        """Update the leaderboard table with current data"""
        try:
            global list_players_name
            logger.debug(f" Updating table with {len(list_players_name)} entries")
            
            # Clear all rows first
            for i in range(4):
                self.LeaderboardTable.setItem(i, 0, QtWidgets.QTableWidgetItem(""))
            
            # Sort data by score (descending)
            sorted_data = sorted(list_players_name, key=lambda item: item[1], reverse=True)
            logger.debug(f" Sorted leaderboard data: {sorted_data}")
            
            # Populate table with data
            for i, (player_name) in enumerate(sorted_data):
                if i >= 4:  # Only show top 5
                    break

                player_name_item = QtWidgets.QTableWidgetItem(str(player_name))
                player_name_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.LeaderboardTable.setItem(i, 0, player_name_item)
                
                # score_item = QtWidgets.QTableWidgetItem(f"{score:,}")
                # score_item.setTextAlignment(QtCore.Qt.AlignCenter)
                # self.LeaderboardTable.setItem(i, 1, score_item)
            
            # If no data, show placeholder
            if not list_players_name:
                placeholder_item = QtWidgets.QTableWidgetItem("No teams yet")
                placeholder_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.LeaderboardTable.setItem(0, 0, placeholder_item)
                
                # placeholder_score = QtWidgets.QTableWidgetItem("0")
                # placeholder_score.setTextAlignment(QtCore.Qt.AlignCenter)
                # self.LeaderboardTable.setItem(0, 1, placeholder_score)
                
        except Exception as e:
            logger.error(f" Error updating leaderboard table: {e}")
    
    
    
    def Inactive(self):
        """Switch to inactive state with inActive GIF and show table (same as CatchTheStick.py)"""
        try:
            logger.info(" Home screen switching to Inactive state")
            
            # Stop the timer2 if it exists
            if hasattr(self, 'timer2') and self.timer2 is not None:
                self.timer2.stop()
            
            # Load the inactive GIF based on screen size (same logic as CatchTheStick.py)
            global scaled
            if scaled == 1:
                if hasattr(self, 'movie') and self.movie is not None:
                    self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_inActive_OLD.gif")
                    self.movie.setCacheMode(QMovie.CacheAll)
            else:
                if hasattr(self, 'movie') and self.movie is not None:
                    self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_inActive_OLD.gif")
                    self.movie.setCacheMode(QMovie.CacheAll)
            
            # Set the new movie and start it
            if hasattr(self, 'Background') and self.Background is not None: 
                self.Background.setMovie(self.movie)
            if hasattr(self, 'movie') and self.movie:
                self.movie.start()
            
            # Show the table (same as CatchTheStick.py)
            if hasattr(self, 'LeaderboardTable') and self.LeaderboardTable is not None:
                self.LeaderboardTable.show()
            
            # Set global homeOpened flag (same as CatchTheStick.py)
            global homeOpened
            homeOpened = True
            
            logger.info(" Home screen switched to Inactive state successfully")
            
        except Exception as e:
            logger.error(f" Error switching to Inactive state 2: {e}")
    
    def closeEvent(self, event):
        logger.info(" Home screen closing...")
        
        # Stop timer2 if it exists
        if hasattr(self, 'timer2') and self.timer2:
            try:
                self.timer2.stop()
                try:
                    self.timer2.timeout.disconnect()
                except:
                    pass
                self.timer2 = None
                logger.debug(" Timer2 cleaned up")
            except Exception as e:
                logger.warning(f"  Error stopping timer2: {e}")
        
        if hasattr(self, 'movie') and self.movie:
            try:
                self.movie.stop()
                self.movie = None
            except Exception as e:
                logger.warning(f"  Error stopping movie: {e}")
        if hasattr(self, 'player') and self.player:
            try:
                self.player.stop()
                self.player = None
            except Exception as e:
                logger.warning(f"  Error stopping player: {e}")
        event.accept()
        super().closeEvent(event)



class Home_screen(QtWidgets.QMainWindow):
    """Enhanced Home_screen with comprehensive safety and professional styling"""
    
    def __init__(self):
        super().__init__()
        self.player = None
        self.movie = None
        self.LeaderboardTable = None
        # if multimedia_available:
        #     self.player = QMediaPlayer()
        logger.debug(" Home_screen initialized")
    
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
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_intro_OLD.gif")
            else:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_intro_OLD.gif")
            
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

                /* QScrollBar Styling */
                QScrollBar:vertical, QScrollBar:horizontal {
                    background-color: #1c2833;  /* Deep muted blue background for scrollbar */
                    border: 1px solid #3b5998;  /* Border color */
                    border-radius: 4px;  /* Rounded corners */
                }

                QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                    background-color: #2e4053;  /* Darker muted blue handle */
                    border-radius: 4px;  /* Rounded corners */
                }

                QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                    background-color: #4c669f;  /* Medium muted blue handle on hover */
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
            self.LeaderboardTable.verticalHeader().setCascadingSectionResizes(False)
            
            # Calculate flexible row heights for the table height (415px)
            # Total available height: 415px minus header and padding
            available_height = int(415 * self.scale-80 )  # Account for header and padding
            row_height = int(available_height / 5)  # Distribute equally among 4 rows
            
            for i in range(5):
                self.LeaderboardTable.verticalHeader().resizeSection(i, row_height)
            # self.LeaderboardTable.verticalHeader().setStretchLastSection(True)
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


            self.timer3 = QTimer(Home)
            self.timer3.setTimerType(Qt.PreciseTimer)
            self.timer3.timeout.connect(self.looping)
            
            logger.info("⏰ Home screen timer3 set for 1 second to switch to Inactive state")
            
            self.UpdateTable()
            # Initially hide table - it will be shown by Inactive() after 13 seconds
            self.LeaderboardTable.hide()
            logger.debug(" Home_screen setup completed")
            
        except Exception as e:
            logger.error(f" Error setting up Home_screen: {e}")
    
    def Inactive(self):
        """Switch to inactive state with inActive GIF and show table (same as CatchTheStick.py)"""
        try:
            logger.info(" Home screen switching to Inactive state")
            # check if self is deleted
             # Set global homeOpened flag (same as CatchTheStick.py)
            global homeOpened
            homeOpened = True
            
            if self.destroyed == True:
                return
            # Stop the timer2 if it exists
            if hasattr(self, 'timer2') and self.timer2:
                self.timer2.stop()
            
            # Load the inactive GIF based on screen size (same logic as CatchTheStick.py)
            global scaled
            if scaled == 1:
                if hasattr(self, 'movie') and self.movie is not None:
                    self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_inActive_OLD.gif")
                    self.movie.setCacheMode(QMovie.CacheAll)
            else:
                if hasattr(self, 'movie') and self.movie is not None:
                    self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_inActive_OLD.gif")
                    self.movie.setCacheMode(QMovie.CacheAll)
                
            # Set the new movie and start it
            if hasattr(self, 'Background') and self.Background is not None:
                self.Background.setMovie(self.movie)
            if hasattr(self, 'movie') and self.movie:
                self.movie.start()
            
            # Show the table (same as CatchTheStick.py)
            if hasattr(self, 'LeaderboardTable') and self.LeaderboardTable is not None:
                self.LeaderboardTable.show()
            

            
            
            logger.info(" Home screen switched to Inactive state successfully")

            if hasattr(self, 'timer3') and self.timer3 is not None:
                self.timer3.start(9000)
                logger.info("⏰ Home screen timer3 set for 9 second to switch to Inactive state")
            
        except Exception as e:
            logger.error(f" Error switching to Inactive state: {e}")
    
    def looping(self):
        # Safe timer stop
        try:
            if hasattr(self, 'timer3') and self.timer3 is not None:
                self.timer3.stop()
        except (RuntimeError, AttributeError):
            pass
            
        # Safe table hide - check if widget still exists    
        try:
            if hasattr(self, 'LeaderboardTable') and self.LeaderboardTable is not None:
                self.LeaderboardTable.hide()
        except (RuntimeError, AttributeError):
            logger.debug("LeaderboardTable already deleted, skipping hide()")
            
        if scaled == 1:
            if hasattr(self, 'movie') and self.movie is not None:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_intro_OLD.gif")
                self.movie.setCacheMode(QMovie.CacheAll)
        else:
            if hasattr(self, 'movie') and self.movie is not None:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_intro_OLD.gif")
                self.movie.setCacheMode(QMovie.CacheAll)
            
        # Safe background and movie operations
        try:
            if hasattr(self, 'Background') and self.Background is not None:
                self.Background.setMovie(self.movie)
                self.movie.start()
        except (RuntimeError, AttributeError):
            logger.debug("Background widget already deleted, skipping movie operations")
            
        # Safe timer start
        try:
            if hasattr(self, 'timer2') and self.timer2 is not None:
                self.timer2.start(11000)
        except (RuntimeError, AttributeError):
            logger.debug("Timer already deleted, skipping start()")



    def UpdateTable(self):
        """Update the leaderboard table with current data"""
        try:
            global list_top5_FalconGrasp
            logger.debug(f" Updating table with {len(list_top5_FalconGrasp)} entries")
            
            # Clear all rows first
            for i in range(5):
                if hasattr(self, 'LeaderboardTable') and self.LeaderboardTable is not None:
                    self.LeaderboardTable.setItem(i, 0, QtWidgets.QTableWidgetItem(""))
                    self.LeaderboardTable.setItem(i, 1, QtWidgets.QTableWidgetItem(""))
            
            # Sort data by score (descending)
            sorted_data = sorted(list_top5_FalconGrasp, key=lambda item: item[1], reverse=True)
            logger.debug(f" Sorted leaderboard data: {sorted_data}")
            
            # Populate table with data
            for i, (team, score) in enumerate(sorted_data):
                if i >= 5:  # Only show top 5
                    break

                team_item = QtWidgets.QTableWidgetItem(str(team))
                team_item.setTextAlignment(QtCore.Qt.AlignCenter)
                if hasattr(self, 'LeaderboardTable') and self.LeaderboardTable is not None:
                    self.LeaderboardTable.setItem(i, 0, team_item)
                
                score_item = QtWidgets.QTableWidgetItem(f"{score:,}")
                score_item.setTextAlignment(QtCore.Qt.AlignCenter)
                if hasattr(self, 'LeaderboardTable') and self.LeaderboardTable is not None:
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
            logger.error(f" Error updating leaderboard table: {e}")
    
    def _update_leaderboard(self):
        """Update the leaderboard data from API"""
        try:
            global list_top5_FalconGrasp
            logger.info(" Fetching leaderboard for 'Falcon's Grasp'...")
            leaderboard = api.get_leaderboard("Falcon's Grasp")
            logger.info(f" Leaderboard received: {leaderboard}")
            
            list_top5_FalconGrasp.clear()
            list_top5_FalconGrasp.extend(leaderboard)
            
            logger.info(f" Leaderboard updated with {len(leaderboard)} entries")
            
            # Update the UI table if it exists
            if hasattr(self, 'UpdateTable'):
                self.UpdateTable()
                logger.info(" Leaderboard table UI updated")
                
        except Exception as e:
            logger.error(f" Error updating leaderboard: {e}")
    
    
    def closeEvent(self, event):
        logger.info(" Home screen closing...")
        
        # Stop timer2 if it exists
        if hasattr(self, 'timer2') and self.timer2:
            try:
                self.timer2.stop()
                try:
                    self.timer2.timeout.disconnect()
                except:
                    pass
                self.timer2 = None
                logger.debug(" Timer2 cleaned up")
            except Exception as e:
                logger.warning(f"  Error stopping timer2: {e}")
        
        if hasattr(self, 'movie') and self.movie:
            try:
                self.movie.stop()
                self.movie = None
            except Exception as e:
                logger.warning(f"  Error stopping movie: {e}")
        if hasattr(self, 'Background') and self.Background:
            try:
                self.Background.setMovie(None)
            except Exception as e:
                logger.warning(f"  Error stopping Background: {e}")
        if hasattr(self, 'player') and self.player:
            try:
                self.player.stop()
                self.player = None
            except Exception as e:
                logger.warning(f"  Error stopping player: {e}")
        event.accept()
        super().closeEvent(event)


class Active_screen(QWidget):
    """Enhanced Active_screen with FalconGrasp detection logic and safety improvements"""
    
    def __init__(self):
        super().__init__()
        logger.info(" Initializing Active_screen with MQTT thread...")
        
        self.mqtt_thread = MqttThread('localhost')
        # self.mqtt_thread.start_signal.connect(self.start_game)
        # self.mqtt_thread.stop_signal.connect(self.stop_game)
        # self.mqtt_thread.restart_signal.connect(self.restart_game)
        # self.mqtt_thread.activate_signal.connect(lambda: logger.info(" Game activated"))
        self.mqtt_thread.deactivate_signal.connect(self.deactivate)
        self.mqtt_thread.message_signal.connect(lambda data: self.ReceiveData(data))
        self.mqtt_thread.start()
        
        # Simple check without complex retry logic
        mqtt_ready = self._ensure_mqtt_ready()
        if mqtt_ready:
            logger.info(" Active_screen MQTT thread initialized successfully")
        else:
            logger.info("ℹ  MQTT thread will connect when needed")
        
        # self.player = QMediaPlayer() if multimedia_available else None
        self.TimerGame = None
        self.remaining_time = 0
        
    def _ensure_mqtt_ready(self):
        """Check if MQTT thread is ready without aggressive waiting"""
        try:
            if hasattr(self, 'mqtt_thread') and self.mqtt_thread:
                # Quick check - don't wait too long
                import time
                max_wait = 1.0  # Reduced wait time to 1 second
                wait_interval = 0.1
                waited = 0
                
                while waited < max_wait:
                    # Check if client is available and connected
                    if (hasattr(self.mqtt_thread, 'client') and 
                        self.mqtt_thread.client and 
                        hasattr(self.mqtt_thread, 'connected') and 
                        self.mqtt_thread.connected):
                        logger.debug(" MQTT thread ready and connected")
                        return True
                    
                    time.sleep(wait_interval)
                    waited += wait_interval
                
                # Not connected yet, but that's okay - it will connect later
                logger.debug("ℹ️  MQTT thread not connected yet (will connect when needed)")
                return False
            else:
                logger.debug("ℹ️  MQTT thread not available")
                return False
        except Exception as e:
            logger.debug(f"ℹ️  MQTT readiness check failed: {e}")
            return False
    
    def load_custom_font(self, font_path):
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            return "Arial"  # Better fallback
        font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
        return font_families[0] if font_families else "Arial"  # Better fallback
    
    # def play_audio(self):
    #     """Load and play the audio file."""
    #     try:
    #         # Check if player is available
    #         if not multimedia_available or not hasattr(self, 'player') or not self.player:
    #             logger.warning("  Media player not available, skipping audio playback")
    #             return
                
    #         audio_file = "Assets/mp3/2066.wav"
    #         absolute_path = os.path.abspath(audio_file)
    #         logger.debug(f" Playing audio: {absolute_path}")
            
    #         # Safely set media and play
    #         self.player.setMedia(QMediaContent(QtCore.QUrl.fromLocalFile(absolute_path)))
    #         self.player.setVolume(100)
    #         self.player.play()
            
    #         # Connect signal only if not already connected
    #         try:
    #             self.player.mediaStatusChanged.connect(self.check_media_status)
    #         except TypeError:
    #             # Signal already connected, ignore
    #             pass
                
    #     except Exception as e:
    #         logger.error(f" Error playing audio: {e}")
    #         # Don't let audio errors crash the game
    
    # def check_media_status(self, status):
    #     """Check media status and stop playback if finished."""
    #     try:
    #         if multimedia_available and hasattr(QMediaPlayer, 'MediaStatus'):
    #             if status == QMediaPlayer.MediaStatus.EndOfMedia:
    #                 if hasattr(self, 'player') and self.player:
    #                     self.player.stop()
    #                 else:
    #                     logger.debug("  Player not available during media status check")
    #     except Exception as e:
    #         logger.warning(f"  Error in media status check: {e}")
    
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
                                
                            logger.debug(f" Updated Player {index+1} score: {score}")
                        else:
                            logger.warning(f"  Invalid player index: {index}")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"  Error parsing camera topic {topic}: {e}")
            
            # Handle team name topic
            elif topic.endswith("/TeamName/Pub"):
                global teamName
                teamName = message
                logger.debug(f" Team name updated: {teamName}")
                
                # Update team name label if it exists
                if hasattr(self, 'label') and self.label:
                    self.label.setText(teamName)
            
            # Handle total score topic
            elif topic.endswith("/score/Pub"):
                try:
                    global scored
                    scored = int(message)
                    logger.debug(f" Total score updated: {scored}")
                except ValueError as e:
                    logger.warning(f"  Invalid total score format: {message} - {e}")
            
            else:
                logger.debug(f" Ignoring unhandled topic: {topic}")
                
        except Exception as e:
            logger.warning(f"  Error processing data: {e}")
    
    def restart_game(self):
        """Restart game with timer management"""
        global gameRunning
        try:
            logger.debug(" Restarting FalconGrasp game...")
            
            gameRunning = False  # Reset flag to allow restart
            
            # Call start_game to properly restart
            self.start_game()
            
            logger.debug(" Game restarted successfully")
        except Exception as e:
            logger.warning(f"  Error restarting game: {e}")
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
            logger.warning(f"  Error starting game timer: {e}")
    
    def update_timer_display(self):
        """Update timer display every second"""
        global gameRunning
        try:
            if self.remaining_time > 0:
                self.remaining_time -= 1
                self.set_lcd(self.remaining_time)
            else:
                # Timer finished - trigger proper game stop sequence
                logger.info("⏰ Game timer finished - triggering game stop sequence")
                gameRunning = False  # Reset flag when timer finishes
                
                if hasattr(self, 'TimerGame') and self.TimerGame:
                    self.TimerGame.stop()
                self.set_lcd(0)
                
                # CRITICAL: Call stop_game() to trigger the complete stop sequence
                # This will calculate final score, save to CSV, play audio, and trigger deactivation
                self.stop_game()
                
                logger.info(" Game timer finished - stop sequence completed")
        except Exception as e:
            logger.warning(f"  Error updating timer: {e}")
            gameRunning = False  # Reset flag on error
    
    @pyqtSlot()
    def start_game(self):
        """Start game with timer and audio (same logic as CatchTheStick.py)"""
        global gameStarted, gameRunning, list_players_score
        
        # Check if UI is properly initialized
        if not hasattr(self, 'TimerGame'):
            logger.warning("  Game UI not yet initialized, cannot start game")
            return
        
        # Prevent recursive calls
        if gameRunning:
            logger.debug(" Game is already running, skipping start_game call")
            return
            
        gameStarted = True
        gameRunning = True
        
        try:
            logger.info("Starting FalconGrasp game...")
            
            # Publish MQTT game start message
            self._safe_mqtt_publish("FalconGrasp/game/start", "start")
            logger.info(" Published MQTT game start message")
            
            # Reset player scores
            list_players_score = [0,0,0,0]
            
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
            
            logger.info(" Game timers started successfully")
            print("start")
            # self.play_audio()
            
        except Exception as e:
            logger.error(f" Error starting game timers: {e}")
            gameRunning = False  # Reset flag on error
    
    @pyqtSlot()
    def stop_game(self):
        """Stop game and calculate final score (same logic as CatchTheStick.py)"""
        global teamName, scored, gameStarted, gameRunning
        
        # Check if UI is properly initialized
        if not hasattr(self, 'TimerGame'):
            logger.warning("  Game UI not yet initialized, cannot stop game")
            return
            
        try:
            # Calculate final score from player scores
            global list_players_score
            scored = sum(list_players_score[:4])  # Sum of all player scores
            
            # Publish MQTT game stop message
            self._safe_mqtt_publish("FalconGrasp/game/stop", "stop")
            logger.info(" Published MQTT game stop message")
            
            # Stop timers
            if hasattr(self, 'TimerGame') and self.TimerGame:
                self.TimerGame.stop()
            
            logger.info(" Game timers stopped successfully")
            
            # Unsubscribe from data topics when game stops (same as CageGame)
            if hasattr(self, 'mqtt_thread') and self.mqtt_thread:
                if hasattr(self.mqtt_thread, 'unsubscribe_from_data_topics'):
                    self.mqtt_thread.unsubscribe_from_data_topics()
                    logger.info(" Unsubscribed from data topics - no more sensor data")
                else:
                    logger.debug("ℹ️  MQTT unsubscribe method not available")
            else:
                logger.debug("ℹ️  MQTT thread not available for unsubscription")
            
            self.save_final_score_to_csv(teamName, scored)
        except Exception as e:
            logger.error(f" Error stopping game: {e}")

        # self.play_audio()
        gameStarted = False
        gameRunning = False
        
        # Deactivate after 5 seconds - single clean trigger like CageGame
        QtCore.QTimer.singleShot(5000, lambda: (
            # Safely publish MQTT deactivate message (this will trigger the GameManager)
            self._safe_mqtt_publish("FalconGrasp/game/Deactivate", 1),
            print("deactivate")
        ))
        
        print("stop")
    
    def _safe_mqtt_publish(self, topic, message):
        """Safely publish MQTT message with proper error handling"""
        try:
            if hasattr(self, 'mqtt_thread') and self.mqtt_thread:
                if (hasattr(self.mqtt_thread, 'client') and 
                    self.mqtt_thread.client and 
                    hasattr(self.mqtt_thread, 'connected') and 
                    self.mqtt_thread.connected):
                    self.mqtt_thread.client.publish(topic, message)
                    logger.debug(f" MQTT message published: {topic} = {message}")
                else:
                    logger.warning(f"  MQTT client not connected, cannot publish: {topic}")
            else:
                logger.warning(f"  MQTT thread not available, cannot publish: {topic}")
        except Exception as e:
            logger.error(f" Error publishing MQTT message {topic}: {e}")




    
    @pyqtSlot()
    def cancel_game(self):
        """Cancel game and stop timers (same logic as CatchTheStick.py)"""
        global gameRunning
        try:
            logger.info(" Cancelling FalconGrasp game...")
            
            # Publish MQTT game stop message for cancellation
            self._safe_mqtt_publish("FalconGrasp/game/stop", "stop")
            logger.info(" Published MQTT game stop message for cancellation")
            
            gameRunning = False  # Reset game running flag
            
            if hasattr(self, 'TimerGame') and self.TimerGame:
                self.TimerGame.stop()
            
            # Unsubscribe from data topics when game is cancelled (same as CageGame)
            if hasattr(self, 'mqtt_thread') and self.mqtt_thread:
                if hasattr(self.mqtt_thread, 'unsubscribe_from_data_topics'):
                    self.mqtt_thread.unsubscribe_from_data_topics()
                    logger.info(" Unsubscribed from data topics after cancellation")
                else:
                    logger.debug("ℹ️  MQTT unsubscribe method not available")
            else:
                logger.debug("ℹ️  MQTT thread not available for unsubscription")
            
            logger.info(" FalconGrasp game cancelled successfully")
            
        except Exception as e:
            logger.error(f" Error cancelling game: {e}")
            gameRunning = False  # Reset flag on error
    
    @pyqtSlot()
    def deactivate(self):
        """Handle deactivate signal - trigger score submission only once like CageGame"""
        global gameRunning
        try:
            logger.info(" Deactivating FalconGrasp game...")
            
            gameRunning = False  # Reset game running flag
            
            # Directly trigger score submission via stored GameManager reference
            # This prevents MQTT loop and ensures single submission like CageGame
            if hasattr(self, 'game_manager_ref') and self.game_manager_ref:
                if not self.game_manager_ref.submit_score_flag:
                    logger.info(" Triggering score submission via deactivate (single trigger)")
                    self.game_manager_ref.trigger_score_submission()
                    logger.info(" FalconGrasp deactivate signal sent")
                else:
                    logger.info("ℹ️  Score submission already triggered, skipping duplicate")
            else:
                logger.warning("  No GameManager reference for deactivation")
            
        except Exception as e:
            logger.error(f" Error in deactivate: {e}")
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
                
            logger.info(f" Score saved to CSV: {team_name} - {final_score}")
            
        except Exception as e:
            logger.error(f" Error saving score to CSV: {e}")
    
    def setupUi(self, MainWindow):
        """Setup Active screen UI with FalconGrasp styling"""
        try:
            MainWindow.setObjectName("MainWindow")
            
            # Scaling setup (exact CatchTheStick.py logic)
            if MainWindow.geometry().width() > 1080:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_Active_OLD.gif")
                self.movie.setCacheMode(QMovie.CacheAll)
                self.scale = 2
            else:
                self.movie = QMovie("Assets/1k/portrait/portrait_CatchTheStick_Active_OLD.gif")
                self.movie.setCacheMode(QMovie.CacheAll)
                self.scale = 1
            
            # Central widget setup
            self.centralwidget = QtWidgets.QWidget(MainWindow)
            self.centralwidget.setObjectName("centralwidget")
            
            # Load fonts with fallback
            self.font_family = self.load_custom_font("Assets/Fonts/GOTHIC.TTF")
            self.font_family_good = self.load_custom_font("Assets/Fonts/GOTHICB.ttf")
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
            self.tableWidget_2.setRowCount(4)
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

                /* QScrollBar Styling */
                QScrollBar:vertical, QScrollBar:horizontal {
                    background-color: #1c2833;  /* Deep muted blue background for scrollbar */
                    border: 1px solid #3b5998;  /* Border color */
                    border-radius: 4px;  /* Rounded corners */
                }

                QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                    background-color: #2e4053;  /* Darker muted blue handle */
                    border-radius: 4px;  /* Rounded corners */
                }

                QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                    background-color: #4c669f;  /* Medium muted blue handle on hover */
                }
            """)
            
            # Set headers
            self.tableWidget_2.setHorizontalHeaderLabels(["Player", "Score"])
            for i in range(4):
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
            self.tableWidget_2.verticalHeader().setCascadingSectionResizes(False)
            
            # Calculate flexible row heights for the table height (415px)
            # Total available height: 415px minus header and padding
            available_height = int(415 * self.scale - 80)  # Account for header and padding
            row_height = int(available_height / 4)  # Distribute equally among 4 rows
            
            for i in range(4):
                self.tableWidget_2.verticalHeader().resizeSection(i, row_height)
            # self.tableWidget_2.verticalHeader().setStretchLastSection(True)
            # hide scrollbar
            self.tableWidget_2.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.tableWidget_2.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            # set font of table
            self.tableWidget_2.setFont(font)
            self.tableWidget_2.setFocusPolicy(QtCore.Qt.NoFocus)
            self.gridLayout.addWidget(self.tableWidget_2, 0, 0, 1, 1)
            MainWindow.setCentralWidget(self.centralwidget)
            
            logger.debug(" Active_screen setup completed")
            
        except Exception as e:
            logger.error(f" Error setting up Active_screen: {e}")
    
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
            logger.warning(f"  Error setting LCD: {e}")
    
    def closeEvent(self, event):
        # Prevent double cleanup
        if hasattr(self, '_is_closing') and self._is_closing:
            event.accept()
            return
        self._is_closing = True
        
        print("close in active screen")
        logger.info(" Active screen closing...")
        
        # # Stop MediaPlayer but keep it available for reuse (like MQTT thread)
        # if hasattr(self, 'player') and self.player:
        #     try:
        #         self.player.stop()
        #         if multimedia_available:
        #             self.player.setMedia(QMediaContent())  # Clear media
        #         logger.debug(" MediaPlayer stopped and cleared (kept for reuse)")
        #     except Exception as e:
        #         logger.warning(f"  Error stopping media player: {e}")
        
        # Safely stop movie
        if hasattr(self, 'movie') and self.movie:
            try:
                self.movie.stop()
                self.movie.setCacheMode(QMovie.CacheNone)
                self.movie = None
                logger.debug(" Movie cleaned up")
            except Exception as e:
                logger.warning(f"  Error stopping movie: {e}")
        
        # Stop MQTT thread but keep it available for reuse
        if hasattr(self, 'mqtt_thread') and self.mqtt_thread:
            try:
                # Just unsubscribe from data topics, but keep the connection
                if hasattr(self.mqtt_thread, 'unsubscribe_from_data_topics'):
                    self.mqtt_thread.unsubscribe_from_data_topics()
                    logger.debug(" MQTT unsubscribed from data topics")
                else:
                    logger.debug("ℹ️  MQTT thread will remain connected for reuse")
            except Exception as e:
                logger.warning(f"  Error unsubscribing MQTT: {e}")
        
        # Reset global game state
        global gameStarted
        gameStarted = False
        
        # Safely stop timers
        if hasattr(self, 'TimerGame') and self.TimerGame:
            try:
                self.TimerGame.stop()
                self.TimerGame = None
                logger.debug(" Game timer cleaned up")
            except Exception as e:
                logger.warning(f"  Error stopping game timer: {e}")
        
        # Clean up table widget safely
        if hasattr(self, 'tableWidget_2') and self.tableWidget_2:
            try:
                # Check if table widget is still valid before attempting cleanup
                try:
                    self.tableWidget_2.objectName()  # Test if object is still valid
                    self.tableWidget_2.hide()
                    self.tableWidget_2.clear()
                    self.tableWidget_2.close()
                    # Don't call deleteLater() - let Qt handle it automatically
                    self.tableWidget_2 = None
                    logger.debug(" Table widget cleaned up")
                except RuntimeError:
                    # Table widget already deleted by Qt
                    self.tableWidget_2 = None
                    logger.debug(" Table widget was already deleted by Qt")
            except Exception as e:
                logger.warning(f"  Error cleaning table widget: {e}")
                self.tableWidget_2 = None
        
        # Safely clear UI widgets
        if hasattr(self, 'Background') and self.Background:
            try:
                # Check if Background widget is still valid
                try:
                    self.Background.objectName()  # Test if object is still valid
                    self.Background.clear()
                    self.Background = None
                    logger.debug(" Background cleared")
                except RuntimeError:
                    # Background already deleted by Qt
                    self.Background = None
                    logger.debug(" Background was already deleted by Qt")
            except Exception as e:
                logger.warning(f"  Error clearing background: {e}")
        
        # Don't manually clean up child widgets - let Qt handle cleanup automatically
        if hasattr(self, 'centralwidget'):
            self.centralwidget = None
            logger.debug(" Central widget reference cleared")
        
        event.accept()
        logger.info(" Active screen closed successfully with complete cleanup")
        super().closeEvent(event)


class MainApp(QtWidgets.QMainWindow):
    """Complete Main Application with all screens and new API integration for FalconGrasp"""
    
    def __init__(self):
        super().__init__()
        logger.info("MainApp initializing with complete UI and new API...")
        
        # Setup window
        self.sized = QtWidgets.QDesktopWidget().screenGeometry()
        self.ui_final = Final_Screen()
        self.ui_home = Home_screen()
        self.ui_active = Active_screen()
        self.ui_team_member = TeamMember_screen()

        # Setup mainWindow
        self.mainWindow = QtWidgets.QMainWindow()
        self.mainWindow.setObjectName("Home")
        self.mainWindow.setWindowTitle("FalconGrasp - Complete")
        self.mainWindow.setFixedSize(1080, 1920)
        # self.mainWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint )
        
        # Initialize GameManager with new API
        try:
            self.game_manager = GameManager()
            logger.info(" GameManager initialized with new API")
            
            # CRITICAL: Store reference to game_manager in Active_screen for backup score submission (like CageGame)
            if hasattr(self, 'ui_active') and self.ui_active:
                self.ui_active.game_manager_ref = self.game_manager
                logger.debug(" GameManager reference stored in Active_screen")
                
        except Exception as e:
            logger.error(f" Failed to initialize GameManager: {e}")
            raise
            
        # Connection signals for the game manager Documentation
        # 1. init_signal: Triggered when the game manager is initialized
        self.game_manager.init_signal.connect(self.start_TeamMember_screen)
        # 2. start_signal: Triggered when the game manager starts
        self.game_manager.start_signal.connect(lambda: (
            self.start_Active_screen(),
            self._safe_mqtt_subscribe(),
            self.ui_active.start_game()
        ))
        # 3. cancel_signal: Triggered when the game manager is cancelled
        self.game_manager.cancel_signal.connect(self._handle_game_cancellation)
        # 4. submit_signal: Triggered when the game manager is submitted
        self.game_manager.submit_signal.connect(self.start_final_screen)
        
        # 5. deactivate_signal: Triggered when the game manager is deactivated
        if hasattr(self.ui_active, 'mqtt_thread') and hasattr(self.ui_active.mqtt_thread, 'deactivate_signal'):
            self.ui_active.mqtt_thread.deactivate_signal.connect(
                self.game_manager.trigger_score_submission
            )
        else:
            logger.warning("  MQTT thread not properly initialized for deactivate signal")
        
        audio_files = {
            'continuous': 'Assets/mp3/2066.wav',
            'inactive_game': 'Assets/mp3/game-music-loop-inactive.mp3',
            'active_game': 'Assets/mp3/game-music-loop-active.mp3'
        }
        
        self.audio_thread = AudioServiceThread(audio_files)
        
        # Connect signals
        self.audio_thread.service_ready.connect(lambda: print("Audio service ready!"))
        self.audio_thread.service_error.connect(lambda error: print(f"Audio service error: {error}"))
        self.audio_thread.player_state_changed.connect(
            lambda name, state: print(f"Player {name} state: {state}")
        )
        self.start_Home_screen()

         # Create audio service thread
        
        
        # Start the thread
        self.audio_thread.start()
        
        # Wait for service to be ready
        # audio_thread.service_ready.wait()
        
        # Test the service
        print("Testing audio service...")
        
        # Test continuous sound
        self.audio_thread.play_inactive_game_sound()
        
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
        
        self.mainWindow.showFullScreen()
        logger.info(" MainApp initialization complete")
        logger.info(" FalconGrasp application started successfully!")

    def start_TeamMember_screen(self):
        self._cleanup_previous_screens()
        self.audio_thread.stop_continuous_sound()
        self.audio_thread.stop_active_game_sound()
        self.audio_thread.play_inactive_game_sound()

        logger.info(" Starting Team Member Screen")
        self.ui_team_member.setupUi(self.mainWindow)
        logger.info(" Team Member screen initialized successfully")

    def _cleanup_previous_screens(self):
        """Safely cleanup any previous screen resources"""
        logger.info(" Cleaning up previous screens...")
        
        # Clean up active screen
        if hasattr(self, 'ui_active') and self.ui_active:
            try:
                # Stop any running timers
                if hasattr(self.ui_active, 'timer') and self.ui_active.timer:
                    self.ui_active.timer.stop()
                if hasattr(self.ui_active, 'TimerGame') and self.ui_active.TimerGame:
                    self.ui_active.TimerGame.stop()
                # Don't close video here as it might be needed
            except Exception as e:
                logger.warning(f"  Error cleaning up active screen: {e}")
        
        # Clean up final screen
        if hasattr(self, 'ui_final') and self.ui_final:
            try:
                if hasattr(self.ui_final, 'timer') and self.ui_final.timer:
                    self.ui_final.timer.stop()
                if hasattr(self.ui_final, 'timer2') and self.ui_final.timer2:
                    self.ui_final.timer2.stop()
            except Exception as e:
                logger.warning(f"  Error cleaning up final screen: {e}")
        
        # Clean up home screen
        if hasattr(self, 'ui_home') and self.ui_home:
            try:
                if hasattr(self.ui_home, 'timer') and self.ui_home.timer:
                    self.ui_home.timer.stop()
                if hasattr(self.ui_home, 'timer2') and self.ui_home.timer2:
                    self.ui_home.timer2.stop()
            except Exception as e:
                logger.warning(f"  Error cleaning up home screen: {e}")
        
        logger.info(" Previous screens cleaned up")

    def _safe_mqtt_publish(self, topic, message):
        """Safely publish MQTT message with proper error handling"""
        try:
            if hasattr(self, 'ui_active') and self.ui_active:
                if hasattr(self.ui_active, 'mqtt_thread') and self.ui_active.mqtt_thread:
                    if (hasattr(self.ui_active.mqtt_thread, 'client') and 
                        self.ui_active.mqtt_thread.client and 
                        hasattr(self.ui_active.mqtt_thread, 'connected') and 
                        self.ui_active.mqtt_thread.connected):
                        self.ui_active.mqtt_thread.client.publish(topic, message)
                        logger.debug(f" MQTT message published: {topic} = {message}")
                    else:
                        logger.warning(f"  MQTT client not connected, cannot publish: {topic}")
                else:
                    logger.warning(f"  MQTT thread not available, cannot publish: {topic}")
            else:
                logger.warning(f"  Active screen not available, cannot publish: {topic}")
        except Exception as e:
            logger.error(f" Error publishing MQTT message {topic}: {e}")

    def _handle_game_cancellation(self):
        """Robust handler for game cancellation that works regardless of current screen state"""
        logger.warning("" + "=" * 50)
        logger.warning(" GAME CANCELLATION DETECTED")
        logger.warning("" + "=" * 50)
        
        # Publish MQTT game stop message for cancellation
        try:
            self._safe_mqtt_publish("FalconGrasp/game/stop", "stop")
            logger.info(" Published MQTT game stop message for cancellation")
        except Exception as e:
            logger.warning(f"  Error publishing MQTT stop message: {e}")
        
        try:
            # Safely cleanup active screen components
            if hasattr(self, 'ui_active') and self.ui_active:
                try:
                    if hasattr(self.ui_active, 'TimerGame') and self.ui_active.TimerGame:
                        self.ui_active.TimerGame.stop()
                        logger.debug(" TimerGame stopped")
                except Exception as e:
                    logger.warning(f"  Error stopping TimerGame: {e}")
                
                try:
                    if hasattr(self.ui_active, 'mqtt_thread') and self.ui_active.mqtt_thread:
                        self.ui_active.mqtt_thread.unsubscribe_from_data_topics()
                        logger.debug(" MQTT unsubscribed")
                except Exception as e:
                    logger.warning(f"  Error unsubscribing MQTT: {e}")
                
                try:
                    # Check if ui_active is still valid before closing
                    try:
                        self.ui_active.objectName()  # Test if object is still valid
                        self.ui_active.close()
                        logger.debug(" Active screen closed")
                    except RuntimeError:
                        logger.debug(" Active screen was already deleted by Qt")
                except Exception as e:
                    logger.warning(f"  Error closing active screen: {e}")
                
                # CRITICAL: Reset the Active_screen state instead of recreating it
                try:
                    logger.info(" Resetting Active_screen state after cancellation...")
                    self._reset_active_screen_state()
                    logger.info(" Active_screen state reset successfully")
                    
                except Exception as e:
                    logger.error(f" Error resetting Active_screen: {e}")
            
            # Force manual reset of essential flags only
            if hasattr(self, 'game_manager') and self.game_manager:
                self.game_manager.game_result_id = None
                self.game_manager.submit_score_flag = False
                self.game_manager.started_flag = False  # CRITICAL: Reset like CAGE_Game.py
                self.game_manager.cancel_flag = False
                logger.debug(f" GameManager flags reset: started_flag={self.game_manager.started_flag}")
            
        except Exception as e:
            logger.error(f" Error during cancellation cleanup: {e}")
        
        # Always try to go to home screen, regardless of cleanup errors
        try:
            logger.info(" Moving to home screen after cancellation...")
            self.start_Home_screen()
            logger.info(" Successfully moved to home screen after cancellation")
        except Exception as e:
            logger.error(f" Error moving to home screen after cancellation: {e}")
            # Last resort - try basic home screen setup
            try:
                global homeOpened
                homeOpened = True
                logger.info(" Set homeOpened flag as fallback")
            except Exception as e2:
                logger.error(f" Fallback failed: {e2}")

    def _reset_active_screen_state(self):
        """Reset Active_screen state without recreating objects to avoid resource conflicts"""
        try:
            if not hasattr(self, 'ui_active') or not self.ui_active:
                logger.warning("  ui_active not available for state reset")
                return
            
            logger.info(" Resetting Active_screen state without object recreation...")
            
            # Reset game state variables
            global gameStarted, gameRunning, scored, list_players_score
            
            gameStarted = False
            gameRunning = False
            scored = 0
            list_players_score = [0,0,0,0]
            
            logger.debug(" Global game state variables reset")
            
            # Reset MediaPlayer state (reuse existing player)
            # if hasattr(self.ui_active, 'player') and self.ui_active.player:
            #     try:
            #         self.ui_active.player.stop()
            #         if multimedia_available:
            #             self.ui_active.player.setMedia(QMediaContent())  # Clear any loaded media
            #         logger.debug(" MediaPlayer state reset (reused existing player)")
            #     except Exception as e:
            #         logger.warning(f"  Error resetting MediaPlayer: {e}")
            
            # Reset MQTT thread state (reuse existing connection if available)
            if hasattr(self.ui_active, 'mqtt_thread') and self.ui_active.mqtt_thread:
                try:
                    # Check if MQTT is still connected
                    if (hasattr(self.ui_active.mqtt_thread, 'connected') and 
                        self.ui_active.mqtt_thread.connected and
                        hasattr(self.ui_active.mqtt_thread, 'client') and
                        self.ui_active.mqtt_thread.client):
                        logger.debug(" MQTT thread still connected, reusing existing connection")
                    else:
                        logger.debug(" MQTT thread disconnected, will reconnect on next game start")
                except Exception as e:
                    logger.warning(f"  Error checking MQTT state: {e}")
            
            logger.info(" Active_screen state reset completed without object recreation")
            
        except Exception as e:
            logger.error(f" Error in _reset_active_screen_state: {e}")

    def _safe_mqtt_subscribe(self):
        """Safely subscribe to MQTT data topics with proper error handling"""
        try:
            logger.info(" Subscribing to MQTT data topics...")
            if (hasattr(self.ui_active, 'mqtt_thread') and 
                self.ui_active.mqtt_thread and 
                hasattr(self.ui_active.mqtt_thread, 'subscribe_to_data_topics')):
                
                # Ensure MQTT is ready before subscribing
                if (hasattr(self.ui_active.mqtt_thread, 'connected') and 
                    self.ui_active.mqtt_thread.connected):
                    self.ui_active.mqtt_thread.subscribe_to_data_topics()
                    logger.debug(" Successfully subscribed to MQTT data topics")
                else:
                    logger.warning("  MQTT not connected, cannot subscribe to data topics")
                    # Try to ensure MQTT is ready and retry once
                    if hasattr(self.ui_active, '_ensure_mqtt_ready'):
                        if self.ui_active._ensure_mqtt_ready():
                            self.ui_active.mqtt_thread.subscribe_to_data_topics()
                            logger.info(" MQTT reconnected and subscribed to data topics")
                        else:
                            logger.warning("  MQTT reconnection failed")
            else:
                logger.warning("  MQTT thread not available for subscription")
            logger.info(" Successfully subscribed to MQTT data topics")

            logger.info(" Successfully subscribed to MQTT control topics")
        except Exception as e:
            logger.error(f" Error subscribing to MQTT data topics: {e}")

    def start_Home_screen(self):
        """Start Home Screen with comprehensive error handling"""
        logger.info(" Starting Home Screen")
        try:
            # Close any current screens safely
            self._close_current_screen()

            self.audio_thread.stop_continuous_sound()
            self.audio_thread.stop_active_game_sound()
            self.audio_thread.play_inactive_game_sound()
            
            
            # Setup and show home screen
            self.ui_home.setupUi(self.mainWindow)
            self.mainWindow.show()
            logger.debug(" Home screen started successfully")
        except Exception as e:
            logger.error(f" Error starting home screen: {e}")
    
    def start_Active_screen(self):
        """Start Active Screen with comprehensive error handling"""
        logger.info(" Starting Active Screen")
        try:
            # Close any current screens safely
            self._close_current_screen()

            self.audio_thread.stop_continuous_sound()
            self.audio_thread.play_active_game_sound()
            self.audio_thread.stop_inactive_game_sound()
            
            # Setup and show active screen
            self.ui_active.setupUi(self.mainWindow)
            self.mainWindow.show()
            logger.debug(" Active screen started successfully")
        except Exception as e:
            logger.error(f" Error starting active screen: {e}")
    
    def start_final_screen(self):
        """Start Final Screen with comprehensive error handling"""
        logger.info(" Starting Final Screen")
        try:
            # Close any current screens safely
            self._close_current_screen()

            self.audio_thread.stop_continuous_sound()
            self.audio_thread.stop_active_game_sound()
            self.audio_thread.stop_inactive_game_sound()
            
            # Setup and show final screen
            self.ui_final.setupUi(self.mainWindow)
            self.mainWindow.show()
            logger.debug(" Final screen started successfully")
            
            # Set up automatic transition back to home screen after final_screen_timer_idle
            logger.info(f"⏰ Setting final screen auto-transition timer: {final_screen_timer_idle}ms")
            QtCore.QTimer.singleShot(final_screen_timer_idle, lambda: (
                self.ui_final.close() if hasattr(self, 'ui_final') and self.ui_final is not None and self.ui_final.isVisible() else None,
                self.start_Home_screen() if hasattr(self, 'ui_final') and self.ui_final is not None and not self.ui_final.isVisible() else None
            ))
            
        except Exception as e:
            logger.error(f" Error starting final screen: {e}")
    
    def _close_current_screen(self):
        """Safely close any currently active screen"""
        try:
            # Clear central widget content
            central_widget = self.mainWindow.centralWidget()
            if central_widget:
                # Check if central widget is still valid before attempting operations
                try:
                    central_widget.objectName()  # Test if object is still valid
                    central_widget.hide()
                    central_widget.close()
                    # Don't call deleteLater() - let Qt handle it automatically
                    logger.debug(" Current screen closed safely")
                except RuntimeError:
                    # Widget already deleted by Qt
                    logger.debug(" Current screen was already deleted by Qt")
        except Exception as e:
            logger.warning(f"  Error closing current screen: {e}")
    
    def _cleanup_all_screens(self):
        """Comprehensive cleanup of all UI screens"""
        logger.debug(" Cleaning up all screens...")
        
        # Close all UI screens safely
        for screen_name in ['ui_final', 'ui_home', 'ui_active']:
            if hasattr(self, screen_name):
                try:
                    screen = getattr(self, screen_name)
                    if screen:
                        # Check if screen is still valid before attempting operations
                        try:
                            screen.objectName()  # Test if object is still valid
                            screen.close()
                            # Don't call deleteLater() - let Qt handle it automatically
                            logger.debug(f" {screen_name} closed")
                        except RuntimeError:
                            # Screen already deleted by Qt
                            logger.debug(f" {screen_name} was already deleted by Qt")
                except Exception as e:
                    logger.warning(f"  Error closing {screen_name}: {e}")
        
        logger.debug(" All screens cleaned up")

    def close_application(self):
        """Comprehensive application cleanup and shutdown"""
        logger.info(" Closing FalconGrasp application with comprehensive cleanup...")
        
        try:
            # Stop GameManager thread first
            if hasattr(self, 'game_manager') and self.game_manager:
                try:
                    self.game_manager.stop_manager()
                    logger.debug(" GameManager stopped")
                except Exception as e:
                    logger.warning(f"  Error stopping GameManager: {e}")
            
            # Close main window
            if hasattr(self, 'mainWindow') and self.mainWindow:
                try:
                    self.mainWindow.close()
                    logger.debug(" Main window closed")
                except Exception as e:
                    logger.warning(f"  Error closing main window: {e}")
            
            # Close all UI screens safely
            for screen_name in ['ui_final', 'ui_home', 'ui_active']:
                if hasattr(self, screen_name):
                    try:
                        screen = getattr(self, screen_name)
                        if screen:
                            # Check if screen is still valid before attempting operations
                            try:
                                screen.objectName()  # Test if object is still valid
                                screen.close()
                                # Don't call deleteLater() - let Qt handle it automatically
                                logger.debug(f" {screen_name} closed")
                            except RuntimeError:
                                # Screen already deleted by Qt
                                logger.debug(f" {screen_name} was already deleted by Qt")
                    except Exception as e:
                        logger.warning(f"  Error closing {screen_name}: {e}")
            
            # Quit application
            logger.info(" FalconGrasp application cleanup completed")
            QtWidgets.QApplication.quit()
            
        except Exception as e:
            logger.error(f" Error during application cleanup: {e}")
            QtWidgets.QApplication.quit()

    def closeEvent(self, event):
        """Handle application close event with comprehensive cleanup"""
        logger.info(" MainApp closeEvent triggered - starting comprehensive shutdown...")
        
        try:
            # Force stop all timers first to prevent new activities
            self._force_stop_all_timers()
            
            # Cleanup all screen resources
            self._cleanup_all_screens()
            
            # Stop GameManager
            if hasattr(self, 'game_manager') and self.game_manager:
                try:
                    self.game_manager.stop_manager()
                    logger.debug(" GameManager stopped")
                except Exception as e:
                    logger.warning(f"  Error stopping GameManager in closeEvent: {e}")
            
            logger.info(" FalconGrasp MainApp closeEvent cleanup completed")
            event.accept()  # Allow the close event to proceed
            
        except Exception as e:
            logger.error(f" Error during MainApp closeEvent: {e}")
            event.accept()  # Still allow close even if cleanup fails

    def _force_stop_all_timers(self):
        """Force stop all timers across all screens for safe shutdown"""
        logger.debug(" Force stopping all timers...")
        
        try:
            # Stop Active screen timers
            if hasattr(self, 'ui_active') and self.ui_active:
                try:
                    if hasattr(self.ui_active, 'timer') and self.ui_active.timer:
                        self.ui_active.timer.stop()
                        logger.debug(" Active screen timer stopped")
                    if hasattr(self.ui_active, 'TimerGame') and self.ui_active.TimerGame:
                        self.ui_active.TimerGame.stop()
                        logger.debug(" Active screen TimerGame stopped")
                except Exception as e:
                    logger.warning(f"  Error stopping active screen timers: {e}")
            
            # Stop Home screen timers
            if hasattr(self, 'ui_home') and self.ui_home:
                try:
                    if hasattr(self.ui_home, 'timer') and self.ui_home.timer:
                        self.ui_home.timer.stop()
                        logger.debug(" Home screen timer stopped")
                    if hasattr(self.ui_home, 'timer2') and self.ui_home.timer2:
                        self.ui_home.timer2.stop()
                        logger.debug(" Home screen timer2 stopped")
                except Exception as e:
                    logger.warning(f"  Error stopping home screen timers: {e}")
            
            # Stop Team Member screen timers
            if hasattr(self, 'ui_team_member') and self.ui_team_member:
                try:
                    if hasattr(self.ui_team_member, 'timer') and self.ui_team_member.timer:
                        self.ui_team_member.timer.stop()
                        logger.debug(" Team member screen timer stopped")
                    if hasattr(self.ui_team_member, 'timer2') and self.ui_team_member.timer2:
                        self.ui_team_member.timer2.stop()
                        logger.debug(" Team member screen timer2 stopped")
                except Exception as e:
                    logger.warning(f"  Error stopping team member screen timers: {e}")
            
            # Stop Final screen timers if any
            if hasattr(self, 'ui_final') and self.ui_final:
                try:
                    if hasattr(self.ui_final, 'timer') and self.ui_final.timer:
                        self.ui_final.timer.stop()
                        logger.debug(" Final screen timer stopped")
                except Exception as e:
                    logger.warning(f"  Error stopping final screen timers: {e}")
                    
            logger.debug(" All timers force stopped")
            
        except Exception as e:
            logger.error(f" Error in _force_stop_all_timers: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        # Trace initial state at application startup
        trace_flags("APPLICATION_STARTUP", None)
        
        main_app = MainApp()
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f" Fatal error in FalconGrasp application: {e}")
        sys.exit(1)
