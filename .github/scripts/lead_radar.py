#!/usr/bin/env python3
"""Daily Lead Radar — free GitHub Actions prospecting intel for Dead Brands.

Scans public sources for buying-intent signals in David's hunting grounds
(ERP help requests, Odoo/SAP questions, small-biz tech pain, hiring posts
mentioning ERP), scores them, and writes ops/leads/YYYY-MM-DD.md.

Stdlib only. No API keys, no cost. Raw material for the prospecting machine.
"""
import datetime
import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

FEEDS = [
    ("r/ERP new", "https://www.reddit.com/r/ERP/new/.rss"),
    ("r/Odoo new", "https://www.reddit.com/r/Odoo/new/.rss"),
    ("r/SAP new", "https://www.reddit.com/r/SAP/new/.rss"),
    ("r/smallbusiness new", "https://www.reddit.com/r/smallbusiness/new/.rss"),
    ("r/Entrepreneur new", "https://www.reddit.com/r/Entrepreneur/new/.rss"),
    ("r/accounting new", "https://www.reddit.com/r/accounting/new/.rss"),
    ("r/manufacturing new", "https://www.reddit.com/r/manufacturing/new/.rss"),
    ("r/wholesale new", "https://www.reddit.com/r/wholesale/new/.rss"),
    ("HN hiring", "https://hnrss.org/whoishiring/jobs"),
    ("GNews: Odoo help", "https://news.google.com/rss/search?q=Odoo%20implementation%20help&hl=en-US&gl=US&ceid=US%3Aen"),
    ("GNews: SAP B1", "https://news.google.com/rss/search?q=%22SAP%20Business%20One%22%20partner&hl=en-US&gl=US&ceid=US%3Aen"),
    ("GNews: ERP selection", "https://news.google.com/rss/search?q=small%20business%20ERP%20selection&hl=en-US&gl=US&ceid=US%3Aen"),
]

# Buying-intent phrases — someone with a problem and a wallet.
INTENT = re.compile(
    r"\b(looking for|recommend|suggestion|advice|help with|need help|"
    r"migrating|migration|switching from|moving from|implementing|"
    r"implementation|choosing between|vs\b|comparison|worth it|"
    r"struggling with|pain|nightmare|hiring|consultant|partner|"
    r"freelancer|demo|trial|pricing|cost|budget)\b", re.I)

# Domain relevance — must be about business systems, not noise.
DOMAIN = re.compile(
    r"\b(erp|odoo|sap|netsuite|quickbooks|sage|acumatica|dynamics|"
    r"inventory|warehouse|accounting|payroll|crm|supply chain|"
    r"manufacturing|distribution|wholesale|ecommerce|e-commerce|"
    r"bookkeeping|invoicing|pos\b)\b", re.I)

UA = {"User-Agent": "DeadBrands-LeadRadar/1.0 (+https://dstrausser83.github.io/)"}


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
            title = link = desc = ""
            for child in entry:
                t = child.tag.lower()
                if t.endswith("title") and child.text:
                    title = html.unescape(child.text.strip())
                elif t.endswith("link"):
                    href = child.get("href")
                    link = href or (child.text or "").strip()
                elif t.endswith(("description", "summary", "content")) and child.text:
                    desc = html.unescape(child.text.strip())[:400]
            if title and link:
                items.append({"title": title, "link": link,
                              "desc": desc, "source": source})
    return items


def score(it):
    text = it["title"] + " " + it["desc"]
    intent_hits = set(m.lower() for m in INTENT.findall(text))
    domain_hits = set(m.lower() for m in DOMAIN.findall(text))
    if not domain_hits:
        return 0, [], []
    return len(intent_hits) * 2 + len(domain_hits), sorted(intent_hits), sorted(domain_hits)


ANGLE = {
    "looking for": "Ask what they're running now; offer a 15-min fit call.",
    "recommend": "Give one genuinely useful tip publicly, then DM the deeper help.",
    "migrating": "Migration horror stories are his best content — engage, then offer help.",
    "switching from": "Ask what's driving the switch; position a clean Odoo/SAP B1 path.",
    "hiring": "They're spending money on the problem — warm intro territory.",
    "help with": "Answer in public, build authority, soft CTA to deadbrands.co.",
}


def angle_for(intent_hits):
    for k in intent_hits:
        if k in ANGLE:
            return ANGLE[k]
    return "Engage helpfully in public; soft CTA to deadbrands.co where it fits."


def main():
    today = datetime.date.today().isoformat()
    seen, leads = set(), []
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
            s, ih, dh = score(it)
            if s >= 3:
                leads.append((s, it, ih, dh))
    leads.sort(key=lambda x: -x[0])
    top = leads[:15]

    lines = [f"# Lead Radar — {today}", "",
             f"Scanned {len(FEEDS)} sources, {len(seen)} items, {len(leads)} buying signals. Top prospects:", ""]
    for s, it, ih, dh in top:
        lines.append(f"## {it['title']}")
        lines.append(f"- Source: {it['source']} | Score: {s}")
        lines.append(f"- Signals: {', '.join(ih) or '—'} | Domain: {', '.join(dh)}")
        lines.append(f"- Angle: {angle_for(ih)}")
        lines.append(f"- Link: {it['link']}")
        lines.append("")
    lines.append("_Generated free on GitHub Actions. David's rule: engage helpfully in public first, "
                 "pitch never. These are conversations, not targets._")

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    out_dir = os.path.join(repo_root, "ops", "leads")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{today}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out_path} with {len(top)} leads")
    return 0


if __name__ == "__main__":
    sys.exit(main())
