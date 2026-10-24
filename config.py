import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env in project root
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-capstone-key-2026-resume-analyzer")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 Megabytes limit
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "docx"}

    # Groq API Configuration
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    # SQLite Database URI
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'resume_analyzer.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    # Keep GROQ_API_KEY None or mock during standard tests unless integration testing
