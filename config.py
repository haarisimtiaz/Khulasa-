import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from this file's own folder explicitly, rather than relying on
# dotenv's automatic discovery - that guesswork can fail depending on how
# the script is launched (double-clicked .bat, Task Scheduler, etc.).
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


class Config:
    WORLD_NEWS_API_KEY = os.environ.get("WORLD_NEWS_API_KEY")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///khulasa.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
