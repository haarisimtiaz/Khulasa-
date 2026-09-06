from datetime import datetime

from flask import Flask, jsonify, render_template, request

from config import Config
from models import Article, db


def timeago(dt):
    if not dt:
        return ""
    seconds = (datetime.utcnow() - dt).total_seconds()
    if seconds < 60:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(hours // 24)
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"
    weeks = int(days // 7)
    if weeks < 5:
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    months = int(days // 30)
    return f"{months} month{'s' if months != 1 else ''} ago"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.jinja_env.filters["timeago"] = timeago

    db.init_app(app)
    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        scope = request.args.get("scope", "pakistan")
        category = request.args.get("category", "all")
        search_query = request.args.get("q", "").strip()

        display_time_expr = db.func.coalesce(Article.published_at, Article.fetched_at)

        query = Article.query.filter_by(scope=scope).order_by(display_time_expr.desc())
        if category != "all":
            query = query.filter_by(category=category)
        if search_query:
            like = f"%{search_query}%"
            query = query.filter(
                db.or_(Article.title.ilike(like), Article.summary.ilike(like))
            )
        articles = query.limit(30).all()

        # Categories are scoped too, so the tabs only show ones that exist for this scope.
        category_rows = (
            db.session.query(Article.category).filter_by(scope=scope).distinct().all()
        )
        categories = sorted({c[0] for c in category_rows if c[0]})

        lead, rest = (articles[0], articles[1:]) if articles else (None, [])

        return render_template(
            "index.html",
            lead=lead,
            articles=rest,
            categories=categories,
            active_category=category,
            active_scope=scope,
            search_query=search_query,
        )

    @app.route("/api/articles")
    def api_articles():
        scope = request.args.get("scope", "pakistan")
        category = request.args.get("category")
        display_time_expr = db.func.coalesce(Article.published_at, Article.fetched_at)
        query = Article.query.filter_by(scope=scope).order_by(display_time_expr.desc())
        if category and category != "all":
            query = query.filter_by(category=category)
        articles = query.limit(50).all()
        return jsonify([a.to_dict() for a in articles])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
