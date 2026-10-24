import os
import secrets
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env in project root if present
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Application configuration for production and development."""
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

    # Cryptographically secure secret key with fallback
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

    # Cookie and Session Privacy Protection
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("RENDER", "False").lower() in ("true", "1")

    # Upload configuration (5 MB limit)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "docx"}

    # Groq Cloud AI API Configuration (loaded from environment)
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

    # Database configuration (SQLite default; compatible with PostgreSQL on Render)
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Fix for SQLAlchemy 1.4+ postgres:// -> postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_DIR, 'resume_analyzer.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
