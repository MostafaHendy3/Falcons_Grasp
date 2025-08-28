"""
Configuration Management for FalconGrasp Game
Handles all configuration settings for the game application
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class APIConfig:
    """API configuration settings"""
    base_url: str = "https://dev-eaa25-api-hpfyfcbshkabezeh.uaenorth-01.azurewebsites.net/"
    email: str = "eaa25admin@gmail.com"
    password: str = "qhv#1kGI$"
    # game_id: str = "f0f98661-2b50-4b75-8a0a-63714e321b9e"  # Falcon's Grasp
    game_id: str = "878f6f84-7d65-4ecc-9450-872ca7e1a3f3"  # Falcon's Grasp
    game_name: str = "FalconGrasp"
    
    
    # Timeout settings (in seconds)
    auth_timeout: int = 30
    game_status_timeout: int = 8
    submit_score_timeout: int = 20
    leaderboard_timeout: int = 12


@dataclass
class GameConfig:
    """Game configuration settings"""
    timer_value: int = 15000  # Default timer value in milliseconds (same as CatchTheStick)
    final_screen_timer: int = 30000  # Final screen display time (30 seconds like CatchTheStick)
      
    
    # Bonus scores
    win_bonus: int = 500
    time_bonus_multiplier: int = 10


@dataclass
class UIConfig:
    """UI configuration settings"""
    scale_factor: int = 1  # Will be set based on screen resolution
    fonts_path: str = "Assets/Fonts/"
    assets_path: str = "Assets/"
    audio_path: str = "Assets/mp3/"


@dataclass
class MQTTConfig:
    """MQTT configuration settings"""
    broker: str = "localhost"
    port: int = 1883
    data_topics: list = None
    control_topics: list = None
    
    def __post_init__(self):
        if self.data_topics is None:
            self.data_topics = [
                "FalconGrasp/TeamName/Pub",
                "FalconGrasp/score/Pub", 
                "FalconGrasp/camera/0",
                "FalconGrasp/camera/1",
                "FalconGrasp/camera/2", 
                "FalconGrasp/camera/3"
            ]
        
        if self.control_topics is None:
            self.control_topics = [
                "FalconGrasp/game/start",
                "FalconGrasp/game/stop", 
                "FalconGrasp/game/restart",
                "FalconGrasp/game/timer",
                "FalconGrasp/game/Activate",
                "FalconGrasp/game/Deactivate",
                "FalconGrasp/game/timerfinal"
            ]


@dataclass
class Settings:
    """Main settings container"""
    api: APIConfig
    game: GameConfig
    ui: UIConfig
    mqtt: MQTTConfig
    
    @classmethod
    def load(cls, config_file: Optional[str] = None) -> 'Settings':
        """Load settings from environment variables or config file"""
        
        # Load API settings from environment or defaults
        api_config = APIConfig(
            base_url=os.getenv('FALCON_API_BASE_URL', APIConfig.base_url),
            email=os.getenv('FALCON_API_EMAIL', APIConfig.email),
            password=os.getenv('FALCON_API_PASSWORD', APIConfig.password),
            game_id=os.getenv('FALCON_GAME_ID', APIConfig.game_id),
            game_name=os.getenv('FALCON_GAME_NAME', APIConfig.game_name),
        )
        
        # Load game settings
        game_config = GameConfig(
            timer_value=int(os.getenv('FALCON_TIMER_VALUE', GameConfig.timer_value)),
            final_screen_timer=int(os.getenv('FALCON_FINAL_TIMER', GameConfig.final_screen_timer)),
        )
        
        # Load UI settings
        ui_config = UIConfig(
            fonts_path=os.getenv('FALCON_FONTS_PATH', UIConfig.fonts_path),
            assets_path=os.getenv('FALCON_ASSETS_PATH', UIConfig.assets_path),
            audio_path=os.getenv('FALCON_AUDIO_PATH', UIConfig.audio_path),
        )
        
        # Load MQTT settings
        mqtt_config = MQTTConfig(
            broker=os.getenv('FALCON_MQTT_BROKER', MQTTConfig.broker),
            port=int(os.getenv('FALCON_MQTT_PORT', MQTTConfig.port)),
        )
        
        return cls(
            api=api_config,
            game=game_config,
            ui=ui_config,
            mqtt=mqtt_config
        )


# Global settings instance
settings = Settings.load()


# Backwards compatibility
class Config:
    """Legacy config class for backwards compatibility"""
    
    @property
    def settings(self):
        return settings


config = Config()
