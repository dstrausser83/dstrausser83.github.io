#!/usr/bin/env python3
"""Regenerate sitemap.xml from the actual site tree.

Scans index.html, blog/index.html and blog/posts/*.html, pulls each file's
last commit date via git, and writes sitemap.xml. Exits 0 with "changed"
or "unchanged" printed — the weekly cron uses that to push only on change.

Run from the repo root:  python3 .github/scripts/sitemap_gen.py
"""
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import date

BASE = "https://dstrausser83.github.io"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "sitemap.xml")

# (repo path, url path, changefreq, priority)
PAGES = [
    ("index.html", "/", "weekly", "1.0"),
    ("blog/index.html", "/blog/", "daily", "0.9"),
    ("blog/author.html", "/blog/author.html", "monthly", "0.7"),
    ("cookies.html", "/cookies.html", "yearly", "0.3"),
]
for fn in sorted(os.listdir(os.path.join(ROOT, "blog", "posts"))):
    if fn.endswith(".html"):
        PAGES.append(
            (os.path.join("blog", "posts", fn), f"/blog/posts/{fn}", "monthly", "0.8")
        )


def lastmod(relpath):
    """Last commit date touching this file, YYYY-MM-DD; falls back to today."""
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%cs", "--", relpath],
            cwd=ROOT, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        if out:
            return out
    except Exception:
        pass
    return date.today().isoformat()


def main():
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for relpath, urlpath, freq, prio in PAGES:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = BASE + urlpath
        ET.SubElement(url, "lastmod").text = lastmod(relpath)
        ET.SubElement(url, "changefreq").text = freq
        ET.SubElement(url, "priority").text = prio
    ET.indent(urlset, space="  ")
    new = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        urlset, encoding="unicode"
    ) + "\n"

    old = ""
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = f.read()

    if old == new:
        print("unchanged")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(new)
    print("changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
