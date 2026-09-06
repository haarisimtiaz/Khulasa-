"""
Fetches the latest Pakistani news from World News API and stores new
articles in the database. Run this on a schedule (cron, GitHub Actions,
Railway cron job, etc.) to keep the site fresh.

Usage:
    python ingest.py
"""

import os
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
from dateutil import parser as dateparser

from app import create_app
from models import Article, db
from summarize import summarize_article

BASE_URL = "https://api.worldnewsapi.com"

# Matches "word" characters that ARE Latin-script letters (covers English
# plus common accented European letters). Used to detect non-Latin script
# (Georgian, Arabic, Cyrillic, CJK, etc.) regardless of what language tag
# the API attaches to the article.
_LATIN_LETTER_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")
_ANY_LETTER_RE = re.compile(r"\w", re.UNICODE)


def is_mostly_latin_script(text: str, threshold: float = 0.6) -> bool:
    """Returns False if text is dominated by non-Latin script (e.g. Georgian,
    Arabic, CJK) even if the API's own language tag claims it's English."""
    if not text:
        return True

    letters = _ANY_LETTER_RE.findall(text)
    if len(letters) < 5:
        return True  # too little signal to judge either way

    latin_count = sum(1 for ch in letters if _LATIN_LETTER_RE.match(ch))
    return (latin_count / len(letters)) >= threshold


def source_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return "unknown"


def _api_key() -> str:
    api_key = os.environ.get("WORLD_NEWS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "WORLD_NEWS_API_KEY is not set. Add it to your .env file "
            "or environment before running ingest.py."
        )
    return api_key


def fetch_pakistan_news(number: int = 50) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/search-news",
        headers={"x-api-key": _api_key()},
        params={
            "source-country": "pk",
            "entities": "LOC:Pakistan",  # article must actually mention Pakistan
            "language": "en",
            "number": number,
            "sort": "publish-time",
            "sort-direction": "DESC",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("news", [])


def fetch_world_news(number: int = 30) -> list[dict]:
    """General world news with no source-country filter, for the 'World' tab."""
    resp = requests.get(
        f"{BASE_URL}/search-news",
        headers={"x-api-key": _api_key()},
        params={
            "language": "en",
            "number": number,
            "sort": "publish-time",
            "sort-direction": "DESC",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("news", [])


def _store_batch(raw_articles: list[dict], scope: str) -> dict:
    """Store new articles from one fetched batch, tagged with the given scope.
    Returns counts: {"added": int, "from_api": int, "from_gemini": int, "gemini_failed": int}."""
    stats = {"added": 0, "from_api": 0, "from_gemini": 0, "gemini_failed": 0}

    for item in raw_articles:
        url = item.get("url")
        if not url:
            continue

        # Safety net #1: even with language=en on the request, a few
        # mistagged articles can slip through the API's own metadata.
        item_language = item.get("language")
        if item_language and item_language != "en":
            continue

        # Safety net #2: don't trust the tag alone. Check the actual
        # characters in the title, in case the API mislabels the language.
        if not is_mostly_latin_script(item.get("title", "")):
            continue

        if Article.query.filter_by(url=url).first():
            continue  # already have this one (possibly from the other batch)

        text = item.get("text") or ""
        summary = item.get("summary")
        if summary:
            stats["from_api"] += 1
        else:
            # Fall back to our own LLM summary only when the API
            # didn't already give us one. Any failure here (bad key,
            # rate limit, network blip) falls back to a plain text
            # excerpt instead of crashing the whole batch.
            try:
                summary = summarize_article(item.get("title"), text)
                stats["from_gemini"] += 1
                # Gemini's free tier allows ~15 requests/minute. A fixed
                # pause between calls keeps us safely under that regardless
                # of how many new articles show up in a single run.
                time.sleep(4.5)
            except Exception as e:
                print(f"Summarization failed for '{item.get('title')}': {e}")
                summary = text[:300] + ("..." if len(text) > 300 else "")
                stats["gemini_failed"] += 1

        published_at = None
        raw_date = item.get("publish_date")
        if raw_date:
            try:
                parsed = dateparser.parse(raw_date)
                if parsed.tzinfo is not None:
                    # The source gave us an explicit timezone (e.g. +05:30) -
                    # convert to true UTC instead of storing the local time
                    # as if it already were UTC.
                    parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

                # World News API occasionally returns publish_date values that
                # are hours ahead of the real current time for reasons we
                # can't fully diagnose from our side. Rather than store and
                # display an impossible ("in the future") timestamp, discard
                # it entirely - the article still gets saved, just without a
                # trusted publish time (falls back to fetched_at for display).
                if parsed <= datetime.utcnow() + timedelta(minutes=5):
                    published_at = parsed
                else:
                    print(f"Note: discarding future-looking publish_date for '{item.get('title')}'. "
                          f"Raw value from API: {raw_date!r} -> parsed as {parsed}")
            except (ValueError, TypeError):
                published_at = None

        article = Article(
            external_id=str(item["id"]) if item.get("id") else None,
            source=source_domain(url),
            title=item.get("title", "Untitled"),
            summary=summary,
            url=url,
            image=item.get("image"),
            category=item.get("category") or "general",
            scope=scope,
            published_at=published_at,
        )
        db.session.add(article)
        try:
            db.session.commit()
            stats["added"] += 1
        except Exception as e:
            print(f"Failed to save '{article.title}': {e}")
            db.session.rollback()

    return stats


def run_ingest():
    app = create_app()
    with app.app_context():
        pk_articles = fetch_pakistan_news()
        pk_stats = _store_batch(pk_articles, scope="pakistan")
        print(
            f"Pakistan: {pk_stats['added']} new articles added out of {len(pk_articles)} fetched "
            f"({pk_stats['from_api']} used API summary, {pk_stats['from_gemini']} summarized by Gemini, "
            f"{pk_stats['gemini_failed']} Gemini failures)."
        )

        world_articles = fetch_world_news()
        world_stats = _store_batch(world_articles, scope="world")
        print(
            f"World: {world_stats['added']} new articles added out of {len(world_articles)} fetched "
            f"({world_stats['from_api']} used API summary, {world_stats['from_gemini']} summarized by Gemini, "
            f"{world_stats['gemini_failed']} Gemini failures)."
        )

        print(f"Ingest complete: {pk_stats['added'] + world_stats['added']} new articles total.")


if __name__ == "__main__":
    run_ingest()
