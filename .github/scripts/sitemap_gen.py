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

BASE = "https://deadbrands.co"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "sitemap.xml")

# (repo path, url path, changefreq, priority)
PAGES = [
    ("index.html", "/", "weekly", "1.0"),
    ("about.html", "/about.html", "monthly", "0.8"),
    ("services.html", "/services.html", "weekly", "0.9"),
    ("resources.html", "/resources.html", "monthly", "0.8"),
    ("services/erp.html", "/services/erp.html", "monthly", "0.8"),
    ("services/odoo.html", "/services/odoo.html", "monthly", "0.8"),
    ("services/sap-business-one.html", "/services/sap-business-one.html", "monthly", "0.8"),
    ("services/dead-brands.html", "/services/dead-brands.html", "monthly", "0.7"),
    ("services/sales-expert.html", "/services/sales-expert.html", "monthly", "0.7"),
    ("services/marketing-expert.html", "/services/marketing-expert.html", "monthly", "0.7"),
    ("services/tech-consulting.html", "/services/tech-consulting.html", "monthly", "0.7"),
    ("services/business-development.html", "/services/business-development.html", "monthly", "0.7"),
    ("services/small-business-growth.html", "/services/small-business-growth.html", "monthly", "0.7"),
    ("blog/index.html", "/blog/", "daily", "0.9"),
    ("blog/author.html", "/blog/author.html", "monthly", "0.7"),
    ("cookies.html", "/cookies.html", "yearly", "0.3"),
    ("case-studies/index.html", "/case-studies/", "weekly", "0.9"),
]
for fn in sorted(os.listdir(os.path.join(ROOT, "case-studies"))):
    if fn.endswith(".html") and fn != "index.html":
        PAGES.append(
            (os.path.join("case-studies", fn), f"/case-studies/{fn}", "monthly", "0.8")
        )
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
