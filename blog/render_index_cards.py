#!/usr/bin/env python3
"""Server-side render the blog post cards into blog/index.html.

The index page renders its cards client-side from posts.json (JS fetch).
That leaves crawlers and no-JS visitors with an empty card grid — an SEO and
UX gap. This script pre-renders the same cards as static HTML inside
<div id="cards"> so the grid is populated in the raw HTML. The existing JS
still hydrates/re-renders on load (same output), and live search keeps working.

Idempotent: re-run after any posts.json change (e.g. after build_post.py
publishes a new post). Replaces only the markup between the
SSR-CARDS-START / SSR-CARDS-END markers.

Usage: python3 render_index_cards.py   (run from this directory)
"""
import html
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(HERE, "index.html")
POSTS_JSON = os.path.join(HERE, "posts.json")
ET = ZoneInfo("America/New_York")
START = "<!-- SSR-CARDS-START (render_index_cards.py) -->"
END = "<!-- SSR-CARDS-END -->"


def fmt_card_date(p):
    try:
        dt = datetime.fromisoformat(
            p["published_at"].replace("Z", "+00:00")).astimezone(ET)
        hour = dt.strftime("%I").lstrip("0") or "0"
        return (f"{dt.strftime('%b')} {dt.day}, {dt.year} \u00B7 "
                f"{hour}:{dt.strftime('%M')} {dt.strftime('%p')} ET")
    except Exception:
        return p.get("date", "")


def esc(s):
    return html.escape(s or "", quote=True)


def clean_title(title):
    """Strip a trailing author suffix (pulled in from <title> tags) so card
    headings show the clean post title."""
    t = (title or "").strip()
    suffix = "\u2014 David Strausser"
    if t.endswith(suffix):
        t = t[: -len(suffix)].rstrip(" \u2014-").strip()
    return t


def card(p):
    # Mirrors the JS card() in index.html (same structure/classes).
    title = clean_title(p.get("title"))
    img = (f'<img src="{esc(p["image"])}" alt="{esc(title)}" '
           'loading="lazy" decoding="async" />') if p.get("image") else ""
    tags = "".join(f"<span>{esc(t)}</span>" for t in (p.get("tags") or []))
    rt = p.get("reading_time")
    meta = esc(fmt_card_date(p)) + (f" \u00B7 {rt} min read" if rt else "")
    return (f'<article class="post-card">\n        {img}\n'
            '        <div class="post-card-body">\n'
            f'          <h3><a href="{esc(p["url"])}">{esc(title)}</a></h3>\n'
            f'          <p class="post-card-date">{meta}</p>\n'
            f'          <p class="post-card-excerpt">{esc(p.get("excerpt"))}</p>\n'
            f'          <div class="post-card-tags">{tags}</div>\n'
            '        </div>\n      </article>')


def main():
    with open(POSTS_JSON) as f:
        posts = json.load(f)
    cards = "\n      ".join(card(p) for p in posts)
    block = f"{START}\n      {cards}\n      {END}"
    with open(INDEX_HTML) as f:
        src = f.read()
    pattern = re.compile(
        re.escape('<div id="cards" class="post-cards">')
        + r".*?"
        + re.escape("</div>\n        <p id=\"no-results\""),
        re.DOTALL)
    new = (f'<div id="cards" class="post-cards">\n      {block}\n    </div>\n'
           '        <p id="no-results"')
    out, n = pattern.subn(new, src, count=1)
    if n != 1:
        # First run: the div is still empty on one line.
        empty = '<div id="cards" class="post-cards"></div>'
        if empty in src:
            out = src.replace(
                empty,
                f'<div id="cards" class="post-cards">\n      {block}\n    </div>',
                1)
            n = 1
    if n != 1:
        raise SystemExit("could not find the #cards div to inject into")
    with open(INDEX_HTML, "w") as f:
        f.write(out)
    print(f"rendered {len(posts)} cards into index.html")


if __name__ == "__main__":
    main()
