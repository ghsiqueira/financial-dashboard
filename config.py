import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-this'
    
    # Configuração de sessão
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Sessão expira em 7 dias
    
    # MongoDB - CORRIGIDO: Flask-PyMongo procura por MONGO_URI, não MONGODB_URI
    MONGO_URI = os.environ.get('MONGODB_URI') or os.environ.get('MONGO_URI')
    
    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # App
    ITEMS_PER_PAGE = 20
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload