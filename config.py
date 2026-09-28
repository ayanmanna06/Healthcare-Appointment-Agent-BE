import os
import urllib.parse
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load environment variables strictly from backend/.env
load_dotenv(os.path.join(BASE_DIR, ".env"))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-healthcare-key-change-in-prod")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-super-secret-key-12345")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

    # Database: Strictly loaded from environment variables
    DB_TYPE = os.getenv("DB_TYPE", "mysql").lower()
    DB_USER = os.getenv("DB_USER", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "healthcare_agent_db")

    # If explicit DATABASE_URL is set, use it; otherwise build URI safely
    explicit_db_url = os.getenv("DATABASE_URL")
    if explicit_db_url:
        SQLALCHEMY_DATABASE_URI = explicit_db_url
    elif DB_TYPE == "mysql" and DB_HOST and DB_USER:
        encoded_user = urllib.parse.quote_plus(DB_USER)
        encoded_pass = urllib.parse.quote_plus(DB_PASSWORD)
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{encoded_user}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )
    else:
        # Fallback to local SQLite if DB_TYPE is sqlite
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'healthcare.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    } if DB_TYPE == "mysql" else {}

    # LLM Service Configuration: Loaded strictly from environment
    LLM_API_URL = os.getenv("LLM_API_URL", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "mistral-small:24b")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "15"))

    # Email Configuration: Loaded strictly from environment
    MAIL_SERVER = os.getenv("MAIL_SERVER") or os.getenv("SMTP_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT") or os.getenv("SMTP_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME") or os.getenv("SMTP_USERNAME", "")
    _raw_pwd = os.getenv("MAIL_PASSWORD") or os.getenv("SMTP_PASSWORD", "")
    MAIL_PASSWORD = _raw_pwd.replace(" ", "") if _raw_pwd else ""
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER") or os.getenv("SENDER_EMAIL") or MAIL_USERNAME
    ALWAYS_NOTIFY_ORGANIZER = os.getenv("ALWAYS_NOTIFY_ORGANIZER", "False").lower() in ("true", "1", "yes")
    ORGANIZER_EMAIL = os.getenv("SENDER_EMAIL") or MAIL_USERNAME

    # Decision Engine Weights
    WEIGHT_RATING = float(os.getenv("WEIGHT_RATING", "0.35"))
    WEIGHT_EXPERIENCE = float(os.getenv("WEIGHT_EXPERIENCE", "0.25"))
    WEIGHT_EARLIEST_SLOT = float(os.getenv("WEIGHT_EARLIEST_SLOT", "0.25"))
    WEIGHT_LOW_LOAD = float(os.getenv("WEIGHT_LOW_LOAD", "0.15"))
