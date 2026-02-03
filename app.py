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

AVAILABLE_THEMES = {"classic", "magazine", "saffron", "Shodsetu"}
DEFAULT_THEME = "classic"

BRANDS = {
    "vayuveg": {
        "brand_name": "VAYUVEG",
        "site_url": "https://www.vayuveg.com",
        "logo_url": "https://www.vayuveg.com/images/WebSiteImg_email%20header.gif",
    },
    "shodhsetu": {
        "brand_name": "ShodhSetu",
        "site_url": "https://www.shodhsetu.com",
        "logo_url": "https://www.shodhsetu.com/Encyc/2025/6/28/Logo-Shodhsetu.png",
    },
}


def resolve_brand(value: str | None) -> str:
    return value if value in BRANDS else "vayuveg"


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


def render_newsletter(brand: str, theme: str, articles: list[dict[str, str]]):
    brand_cfg = BRANDS[brand]
    template_path = f"themes/{theme}/{brand}.html"

    return render_template(
        template_path,
        # ---- Brand ----
        brand_name=brand_cfg["brand_name"],
        site_url=brand_cfg["site_url"],
        logo_url=brand_cfg["logo_url"],

        # ---- Meta ----
        current_year=2026,
        unsubscribe_url="[UNSUBSCRIBE_URL]",

        # ---- Content ----
        articles=articles,
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


@app.route("/export", methods=["POST"])
def export():
    brand = resolve_brand(request.form.get("brand"))
    theme = resolve_theme(request.form.get("theme"))
    articles = parse_articles(request.form)

    if not articles:
        abort(400, "No articles to export")

    html = render_newsletter(brand, theme, articles)

    response = make_response(html)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{brand}-weekly-newsletter.html"'
    )
    return response




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
