#!/usr/bin/env python3
"""Verify every generated blog post's inline <style> carries the critical
rules from blog/build_post.py's PAGE_TEMPLATE.

Background: posts are generated once from PAGE_TEMPLATE, not regenerated on
template edits. If the template gains new rules (e.g. .post-inline image
sizing, .post-summary box), stale posts render broken until patched by hand.
This check fails the build listing any post missing a critical rule, so drift
gets caught on the push that introduced it instead of by a human eyeballing
the live site.

Critical rules (signatures normalized: whitespace collapsed, case kept):
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSTS_DIR = ROOT / "blog" / "posts"

# selector/property signatures that must appear in each post's inline <style>
CRITICAL = [
    ".post-inline",          # inline article images capped at 620px, centered
    "max-width: 620px",      # the actual cap value
    ".post-hero",            # hero image/video block
    ".post-summary",         # Quick Answer box styling
    "@media",                # responsive rules present
    ".post-body img",        # body image safety cap
]

STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)


def normalize(css: str) -> str:
    return re.sub(r"\s+", " ", css)


def main() -> int:
    posts = sorted(POSTS_DIR.glob("*.html"))
    if not posts:
        print("FAIL: no posts found in blog/posts/")
        return 1
    failures = {}
    for post in posts:
        html = post.read_text(encoding="utf-8")
        blocks = STYLE_RE.findall(html)
        combined = normalize(" ".join(blocks))
        missing = [sig for sig in CRITICAL if normalize(sig) not in combined]
        if missing:
            failures[post.name] = missing
    if failures:
        print(f"FAIL: {len(failures)}/{len(posts)} posts missing critical CSS rules:")
        for name, missing in failures.items():
            print(f"  - {name}: missing {', '.join(missing)}")
        print("Fix: patch the posts' inline <style> to match blog/build_post.py,")
        print("or regenerate the posts from the template.")
        return 1
    print(f"OK: all {len(posts)} posts carry the critical template rules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
