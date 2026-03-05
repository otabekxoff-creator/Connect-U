import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///connectu.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # Telegram
    BOT_TOKEN = os.environ.get('BOT_TOKEN') or '8230210984:AAGld9gVSXps2zC22qyKH5gKXV946wdS2CM'
    MINI_APP_URL = os.environ.get('MINI_APP_URL') or 'https://connect-u-4.onrender.com/login.html'
    
    # CORS
    CORS_ORIGINS = ['http://127.0.0.1:5000', 'https://connect-u-4.onrender.com/login.html']
