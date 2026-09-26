#!/usr/bin/env python3
"""Regenerate the 'Latest blog posts' block in llms.txt from blog/posts.json.

Keeps the AI-crawler summary current on every blog publish: the 10 most
recent posts as markdown links with date + one-line excerpt, wrapped in
<!-- BLOG-POSTS:START --> / <!-- BLOG-POSTS:END --> markers. Hand-written
content outside the markers is never touched. If the markers are missing
(someone hand-edited the file), the block is inserted before the
'## Key links' section, or appended at the end as a last resort.

Prints 'changed' or 'unchanged'. Run from the repo root:
  python3 .github/scripts/llms_gen.py
"""
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LLMS = os.path.join(ROOT, "llms.txt")
POSTS_JSON = os.path.join(ROOT, "blog", "posts.json")
MAX_POSTS = 10
START = "<!-- BLOG-POSTS:START -->"
END = "<!-- BLOG-POSTS:END -->"


def fmt_date(raw):
    """'2026-09-26' or ISO -> 'September 26, 2026'."""
    try:
        return datetime.fromisoformat(str(raw)[:10]).strftime("%B %d, %Y")
    except Exception:
        return str(raw)[:10]


def build_items(posts):
    """Just the markdown list lines (no heading, no markers)."""
    lines = []
    for p in posts[:MAX_POSTS]:
        title = p.get("title", p.get("slug", "Untitled")).strip()
        url = f"https://deadbrands.co/blog/{p.get('url', 'posts/' + p.get('slug', '') + '.html')}"
        excerpt = re.sub(r"\s+", " ", p.get("excerpt") or p.get("description") or "").strip()
        if len(excerpt) > 140:
            excerpt = excerpt[:137].rsplit(" ", 1)[0] + "..."
        date_s = fmt_date(p.get("date", ""))
        line = f"- [{title}]({url}) — {date_s}"
        if excerpt:
            line += f": {excerpt}"
        lines.append(line)
    return lines


def build_block(posts):
    lines = ["## Latest blog posts", "", START] + build_items(posts) + [END, ""]
    return "\n".join(lines)


def main():
    try:
        with open(POSTS_JSON, encoding="utf-8") as f:
            posts = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"posts.json unreadable: {e}", file=sys.stderr)
        return 1
    # posts.json is maintained newest-first by build_post.py; be safe anyway.
    posts = sorted(posts, key=lambda p: (p.get("date", ""), p.get("published_at", "")),
                   reverse=True)
    block = build_block(posts)

    try:
        with open(LLMS, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"llms.txt unreadable: {e}", file=sys.stderr)
        return 1

    if START in text and END in text:
        # Markers present: refresh only the list between them, keep the
        # existing heading and surrounding hand-written content untouched.
        inner = START + "\n" + "\n".join(build_items(posts)) + "\n" + END
        new_text = re.sub(re.escape(START) + r".*?" + re.escape(END),
                          inner, text, flags=re.DOTALL)
    elif "## Key links" in text:
        new_text = text.replace("## Key links", block + "## Key links", 1)
    else:
        new_text = text.rstrip("\n") + "\n\n" + block

    if new_text == text:
        print("unchanged")
        return 0
    with open(LLMS, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
