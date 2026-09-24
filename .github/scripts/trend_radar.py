#!/usr/bin/env python3
"""Daily Trend Radar — free GitHub Actions intel for the social engine.

Polls public RSS feeds across David's niches (ERP, small business, Eagles,
dad life, libertarian), scores items against his interest keywords, and writes
ops/intel/YYYY-MM-DD.md. Stdlib only. No API keys, no cost.

Raw material for drafter.py / Scribe — replaces token-burn research.
"""
import datetime
import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

FEEDS = [
    ("r/Odoo", "https://www.reddit.com/r/Odoo/new/.rss"),
    ("r/ERP", "https://www.reddit.com/r/ERP/new/.rss"),
    ("r/SAP", "https://www.reddit.com/r/SAP/new/.rss"),
    ("r/smallbusiness", "https://www.reddit.com/r/smallbusiness/new/.rss"),
    ("r/PhiladelphiaEagles", "https://www.reddit.com/r/PhiladelphiaEagles/new/.rss"),
    ("r/eagles", "https://www.reddit.com/r/eagles/new/.rss"),
    ("r/SingleParents", "https://www.reddit.com/r/SingleParents/new/.rss"),
    ("r/Libertarian", "https://www.reddit.com/r/Libertarian/new/.rss"),
    ("r/guitar", "https://www.reddit.com/r/guitar/new/.rss"),
    ("HN front", "https://news.ycombinator.com/rss"),
    ("GNews: SAP Business One", "https://news.google.com/rss/search?q=%22SAP%20Business%20One%22&hl=en-US&gl=US&ceid=US%3Aen"),
    ("GNews: Odoo", "https://news.google.com/rss/search?q=Odoo%20ERP&hl=en-US&gl=US&ceid=US%3Aen"),
    ("GNews: Eagles", "https://news.google.com/rss/search?q=Philadelphia%20Eagles&hl=en-US&gl=US&ceid=US%3Aen"),
]

INTERESTS = re.compile(
    r"\b(odoo|sap|erp|sap business one|small business|entrepreneur|automation|ai\b|"
    r"eagles|philadelphia|nfl|cowboys|hurts|barkley|dad|single dad|father|kids|"
    r"guitar|rock|band|libertarian|liberty|tax|taxes|regulation|government|"
    r"freedom|waste|spending|deficit)\b", re.I)

UA = {"User-Agent": "DeadBrands-TrendRadar/1.0 (+https://deadbrands.co/)"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def parse_items(xml_bytes, source):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items
    for entry in root.iter():
        if entry.tag.endswith(("item", "entry")):
            title = link = ""
            for child in entry:
                t = child.tag.lower()
                if t.endswith("title") and child.text:
                    title = html.unescape(child.text.strip())
                elif t.endswith("link"):
                    href = child.get("href")
                    link = href or (child.text or "").strip()
            if title and link:
                items.append({"title": title, "link": link, "source": source})
    return items


def score(title):
    hits = INTERESTS.findall(title)
    return len(hits), sorted(set(h.lower() for h in hits))


def main():
    today = datetime.date.today().isoformat()
    seen, scored = set(), []
    for source, url in FEEDS:
        try:
            xml_bytes = fetch(url)
        except Exception as e:
            print(f"feed failed: {source} ({type(e).__name__})", file=sys.stderr)
            continue
        for it in parse_items(xml_bytes, source):
            key = it["link"].split("?")[0].lower()
            if key in seen:
                continue
            seen.add(key)
            n, keys = score(it["title"])
            if n:
                scored.append((n, it, keys))
    scored.sort(key=lambda x: -x[0])
    top = scored[:20]

    lines = [f"# Trend Radar — {today}", "",
             f"Scanned {len(FEEDS)} feeds, {len(seen)} items, {len(scored)} matched. Top hits:", ""]
    for n, it, keys in top:
        lines.append(f"- **{it['title']}** ({it['source']}; matched: {', '.join(keys)})")
        lines.append(f"  {it['link']}")
    lines += ["", "_Generated free on GitHub Actions. Raw material for the social engine — "
                   "riff, don't repost._"]

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    out_dir = os.path.join(repo_root, "ops", "intel")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{today}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out_path} with {len(top)} hits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
