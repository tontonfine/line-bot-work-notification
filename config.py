import os
from dataclasses import dataclass

@dataclass
class Config:
    """アプリケーション設定"""

    # Database
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'database.db')
    DATABASE_TIMEOUT: int = int(os.getenv('DATABASE_TIMEOUT', '30'))

    # LINE Bot
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_CHANNEL_SECRET: str = os.getenv('LINE_CHANNEL_SECRET')

    # Flask
    SECRET_KEY: str = os.getenv('SECRET_KEY')
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'

    # Application
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '5001'))

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = 'json'  # json or text

config = Config()
