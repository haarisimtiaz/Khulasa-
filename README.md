# Khulasa

A Pakistani news aggregator that summarizes articles from Dawn, Geo, ARY,
Dunya, and other outlets via World News API, so visitors get the gist
without reading the full article. Every summary links back to the
original publisher.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your real keys:
   ```
   cp .env.example .env
   ```
   Then edit `.env` and paste in your `WORLD_NEWS_API_KEY` (from
   worldnewsapi.com/console) and `ANTHROPIC_API_KEY` (from
   console.anthropic.com). `.env` is already in `.gitignore` — it will
   never be committed to GitHub.

3. Pull the first batch of articles:
   ```
   python ingest.py
   ```
   This fetches Pakistani news, summarizes anything that doesn't
   already have a summary, and stores it in a local SQLite database
   (`khulasa.db`).

4. Run the site:
   ```
   python app.py
   ```
   Visit `http://127.0.0.1:5000`.

## Keeping it fresh

`ingest.py` only adds articles that aren't already in the database, so
it's safe to re-run anytime. In production, schedule it to run every
30–60 minutes:
- **Railway**: use a Cron Job service pointed at `python ingest.py`.
- **Vercel** (serverless, no persistent background jobs): trigger it via
  a scheduled GitHub Action that calls a protected endpoint, or run
  ingestion on a separate small always-on host (e.g. Railway) while
  the Flask site itself serves from Vercel.

World News API caches: you may only cache results for up to 1 hour
before refreshing, so don't set the ingest interval much longer than
that if you want to stay within their terms.

## Deploying

Set `WORLD_NEWS_API_KEY`, `ANTHROPIC_API_KEY`, and `DATABASE_URL` as
environment variables in your hosting platform's dashboard (Vercel /
Railway project settings) — never in code. For a real deployment,
swap SQLite for a hosted Postgres database (Railway and Vercel both
offer this) since SQLite's local file won't persist reliably on
serverless platforms.

## Project structure

```
khulasa/
├── app.py            # Flask app + routes
├── ingest.py         # Fetches & stores new articles (run on a schedule)
├── summarize.py       # Claude-based summarization fallback
├── models.py           # Article database model
├── config.py            # Reads secrets from environment variables
├── templates/
│   ├── base.html
│   └── index.html
└── static/
    └── style.css
```
