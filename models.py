from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(64), unique=True, nullable=True)
    source = db.Column(db.String(120), nullable=False)       # e.g. "dawn.com"
    title = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(1000), nullable=False, unique=True)
    image = db.Column(db.String(1000), nullable=True)
    category = db.Column(db.String(50), nullable=True, default="general")
    scope = db.Column(db.String(20), nullable=False, default="pakistan")  # "pakistan" or "world"
    published_at = db.Column(db.DateTime, nullable=True)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def display_time(self):
        """Publish time if we trust it, otherwise when we fetched it - always something sensible to show."""
        return self.published_at or self.fetched_at

    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "image": self.image,
            "category": self.category,
            "scope": self.scope,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "display_time": self.display_time.isoformat() if self.display_time else None,
        }
