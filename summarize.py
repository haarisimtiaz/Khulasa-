"""
Summarizes article text using Google Gemini (free tier).

Only called as a fallback: if World News API already gives us a decent
`summary` field for an article, ingest.py uses that directly and never
calls this (saves API cost). This only runs when we need to summarize
the raw `text` field ourselves.

Requires GEMINI_API_KEY to be set as an environment variable.
Get a free key (no credit card needed) at https://aistudio.google.com/apikey
"""

import os

from google import genai

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file "
                "or environment before running ingest.py."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def summarize_article(title: str, text: str, max_sentences: int = 3) -> str | None:
    """Return a short neutral summary of an article, or None if there's nothing to summarize."""
    if not text or len(text.strip()) < 100:
        return None

    prompt = (
        f"Summarize the following news article in {max_sentences} neutral, factual "
        f"sentences. Do not add opinion or commentary. Do not start with phrases like "
        f"'This article discusses' — just state the news directly.\n\n"
        f"Title: {title}\n\n"
        f"Article:\n{text[:6000]}"
    )

    client = _get_client()
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )
    return response.text.strip()
