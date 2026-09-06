import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from this file's own folder explicitly, rather than relying on
# dotenv's automatic discovery - that guesswork can fail depending on how
# the script is launched (double-clicked .bat, Task Scheduler, etc.).
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


def _normalize_db_url(url):
    if url and url.startswith("postgres://"):
        # SQLAlchemy/psycopg2 require "postgresql://", but Render (and some
        # other providers) still hand out connection strings with the older
        # "postgres://" prefix.
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    WORLD_NEWS_API_KEY = os.environ.get("WORLD_NEWS_API_KEY")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.environ.get("DATABASE_URL")) or "sqlite:///khulasa.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
