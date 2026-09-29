#!/usr/bin/env python3
"""Server-side render the homepage "Fresh off the press" blog cards.

The homepage section #home-blog-cards renders client-side from
blog/posts.json (JS fetch). That leaves crawlers and no-JS visitors with an
empty card grid — an SEO and UX gap. This script pre-renders the same 6
newest cards as static HTML inside the div. The existing JS still
hydrates/re-renders on load (same output), so behavior is unchanged for
normal visitors.

Idempotent: re-run after any blog/posts.json change (e.g. after
build_post.py publishes a new post). Replaces only the markup between the
SSR-HOME-CARDS-START / SSR-HOME-CARDS-END markers.

Usage: python3 render_home_blog_cards.py   (run from this directory)
"""
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(HERE, "index.html")
POSTS_JSON = os.path.join(HERE, "blog", "posts.json")
ET = ZoneInfo("America/New_York")
START = "<!-- SSR-HOME-CARDS-START (render_home_blog_cards.py) -->"
END = "<!-- SSR-HOME-CARDS-END -->"


def esc(s):
    # Mirror the JS esc(): & < > " only (single quotes left alone).
    return (str(s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def clean_title(title):
    t = (title or "").strip()
    return re.sub(r" ?\u2014 ?David Strausser$", "", t)


def fmt_card_date(p):
    try:
        dt = datetime.fromisoformat(
            p["published_at"].replace("Z", "+00:00")).astimezone(ET)
        hour = dt.strftime("%I").lstrip("0") or "0"
        return (f"{dt.strftime('%b')} {dt.day}, {dt.year} \u00B7 "
                f"{hour}:{dt.strftime('%M')} {dt.strftime('%p')} ET")
    except Exception:
        return p.get("date", "")


def card(p):
    # Mirrors the JS card builder in index.html (same structure/classes).
    title = clean_title(p.get("title"))
    img = (f'<img class="card-photo" src="blog/{esc(p["image"])}" '
           f'alt="{esc(title)}" loading="lazy" decoding="async" />'
           ) if p.get("image") else ""
    return (f'<article class="card">{img}'
            f'<h3><a href="blog/{esc(p["url"])}">{esc(title)}</a></h3>'
            f'<p class="post-card-date">{esc(fmt_card_date(p))}</p>'
            f'<p>{esc(p.get("excerpt") or p.get("description") or "")}</p>'
            '</article>')


def main():
    with open(POSTS_JSON, encoding="utf-8") as f:
        posts = json.load(f)
    posts = posts if isinstance(posts, list) else posts.get("posts", [])
    posts = sorted(posts,
                   key=lambda p: str(p.get("published_at") or p.get("date") or ""),
                   reverse=True)[:6]
    cards = "\n          ".join(card(p) for p in posts)
    block = f"{START}\n          {cards}\n          {END}"
    with open(INDEX_HTML, encoding="utf-8") as f:
        src = f.read()
    anchor = ('<div class="cards" id="home-blog-cards">\n'
              '          <!-- Populated from blog/posts.json \u2014 newest first. '
              'No manual edits needed. -->\n        </div>')
    if anchor not in src:
        raise SystemExit("could not find the #home-blog-cards anchor")
    new = ('<div class="cards" id="home-blog-cards">\n'
           f'          {block}\n        </div>')
    out = src.replace(anchor, new, 1)
    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"rendered {len(posts)} home blog cards into index.html")


if __name__ == "__main__":
    main()
