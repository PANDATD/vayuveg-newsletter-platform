"""
VAYUVEG Newsletter Builder – Clean Flask Core

Design goals:
- One render file per theme
- No partials, no includes
- Editor is form-only
- Preview and Generate share same renderer
- Stateless (no DB for now)
"""

from __future__ import annotations

from itertools import zip_longest
from typing import Dict, List, Optional

import markdown
from flask import Flask, abort, make_response, render_template, request
from markupsafe import escape

app = Flask(__name__)

AVAILABLE_THEMES = {"classic", "magazine", "saffron"}
DEFAULT_THEME = "classic"


def resolve_theme(value: Optional[str]) -> str:
    """Ensure only allowed themes are rendered."""
    return value if value in AVAILABLE_THEMES else DEFAULT_THEME


def _getlist_fallback(form, *names: str) -> List[str]:
    """
    Return the first non-empty getlist among candidate field names.
    Keeps backward-compatibility with older editor field names.
    """
    for name in names:
        values = form.getlist(name)
        if values and any(v.strip() for v in values):
            return values
    return form.getlist(names[0]) if names else []


def parse_articles(form) -> List[Dict[str, str]]:
    """
    Preferred field names:
      - title, summary, image, url

    Backward-compatible aliases:
      - desc (summary), img (image), link (url)
    """
    articles: List[Dict[str, str]] = []

    titles = _getlist_fallback(form, "title")
    summaries = _getlist_fallback(form, "summary", "desc")
    images = _getlist_fallback(form, "image", "img")
    links = _getlist_fallback(form, "url", "link")

    for title, summary, image, url in zip_longest(
        titles, summaries, images, links, fillvalue=""
    ):
        title = (title or "").strip()
        if not title:
            continue

        articles.append(
            {
                "title": escape(title),
                "summary": markdown.markdown((summary or "").strip()),
                "image": escape((image or "").strip()),
                "url": escape((url or "").strip()),
            }
        )

    return articles


def render_newsletter(theme: str, articles: list[dict[str, str]]):
    template_path = f"themes/{theme}/newsletter.html"

    return render_template(
        template_path,
        # --- Brand & Identity ---
        brand_name="VAYUVEG",
        site_url="https://www.vayuveg.com",
        current_year=2025,
        # --- Header ---
        header_image_url=(
            "https://www.vayuveg.com/images/WebSiteImg_email%20header.gif"
        ),
        # --- Top CTA (Audio Infopack) ---
        spotify_url=(
            "https://open.spotify.com/show/0X23ATZVGrXCLXzR95DubJ?si=16321e1ab9c14d08"
        ),
        # --- Articles (already parsed & sanitized) ---
        articles=articles,
        # --- Social Links ---
        social_links=[
            {
                "name": "Instagram",
                "url": "https://www.instagram.com/vayuvegofficial/",
                "icon": "https://img.icons8.com/fluency/24/instagram-new.png",
            },
            {
                "name": "Facebook",
                "url": "https://www.facebook.com/VayuvegOfficial",
                "icon": "https://img.icons8.com/fluency/24/facebook-new.png",
            },
            {
                "name": "X",
                "url": "https://x.com/vayuvegofficial",
                "icon": "https://img.icons8.com/fluency/24/twitterx--v1.png",
            },
            {
                "name": "Spotify",
                "url": ("https://open.spotify.com/show/0X23ATZVGrXCLXzR95DubJ"),
                "icon": ("https://img.icons8.com/?size=48&id=G9XXzb9XaEKX&format=png"),
            },
        ],
        # --- Compliance ---
        unsubscribe_url=("[UNSUBSCRIBE_URL]"),
    )


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/editor")
def editor():
    return render_template("editor.html")


@app.route("/export", methods=["POST"])
def export():
    """
    Export the newsletter as a downloadable HTML file.
    Uses the same render path as preview/generate.
    """
    theme = resolve_theme(request.form.get("theme"))
    articles = parse_articles(request.form)

    if not articles:
        abort(400, "No articles to export")

    html = render_newsletter(theme, articles)

    response = make_response(html)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Content-Disposition"] = (
        'attachment; filename="vayuveg-newsletter.html"'
    )

    return response


@app.route("/preview", methods=["POST"])
def preview():
    # FIX: resolve theme from form, not from request object
    theme = resolve_theme(request.form.get("theme"))
    articles = parse_articles(request.form)
    # Preview allows empty articles so iframe never errors while typing
    return render_newsletter(theme, articles)


@app.route("/generate", methods=["POST"])
def generate():
    theme = resolve_theme(request.form.get("theme"))
    articles = parse_articles(request.form)

    if not articles:
        abort(400, "No articles provided")

    return render_newsletter(theme, articles)


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True)
