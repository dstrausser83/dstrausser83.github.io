#!/usr/bin/env python3
"""90-day page-freshness rule for deadbrands.co.

David's rule: no page goes longer than 90 days without at least one minor
improvement. This script compares each page's last-tweak date (tracked in
ops/page-freshness.json) against today, flags stale pages, and drafts a
tweak proposal per stale page (analytics/Clarity-guided where data exists).

The tweak itself always stays Rock-reviewed before publish — this script
only PROPOSES.

Usage:
  python3 tools/freshness.py              # print stale-page report
  python3 tools/freshness.py --write      # also write ops/freshness-report.md
  python3 tools/freshness.py --tweaked /services.html "note"
                                         # record a tweak (resets the clock)
"""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "ops", "page-freshness.json")
REPORT = os.path.join(ROOT, "ops", "freshness-report.md")
RULE_DAYS = 90

# Heuristic tweak ideas per page family (Clarity/GA heatmaps refine these).
TWEAK_IDEAS = {
    "service": [
        "Check Clarity heatmap: is the booking CTA above the fold on mobile? If clicks are low, move CTA higher.",
        "Refresh the FAQ: add the #1 question prospects asked this quarter.",
        "Tighten the hero lede — does it still match what the page ranks for?",
    ],
    "about": [
        "Add one fresh proof point (podcast milestone, new credential, recent win).",
        "Check scroll depth: if visitors bounce before the story, trim the top.",
    ],
    "resources": [
        "Add the newest blog post to the Guides list; drop anything outdated.",
        "Check which guide links get clicks — expand the winners into deeper content.",
    ],
    "blog": [
        "Refresh the intro + add a 2026 update box if the post is >6 months old.",
        "Check FAQ schema still matches the on-page FAQs.",
    ],
    "home": [
        "Rotate the hero proof point / testimonial.",
        "Check CTA click-through in Clarity; A/B the button copy if it's soft.",
    ],
    "default": [
        "Read the page with fresh eyes: cut one weak paragraph, sharpen one headline.",
        "Verify every outbound link still works; fix or replace dead ones.",
    ],
}


def load():
    with open(DATA) as f:
        return json.load(f)


def save(data):
    with open(DATA, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def family_of(path):
    if path == "/index.html" or path == "/":
        return "home"
    if path.startswith("/services"):
        return "service"
    if path.startswith("/about"):
        return "about"
    if path.startswith("/resources"):
        return "resource"
    if path.startswith("/blog"):
        return "blog"
    return "default"


def stale_pages(data, today):
    out = []
    for path, info in sorted(data["pages"].items()):
        last = datetime.date.fromisoformat(info["last_tweak"])
        age = (today - last).days
        if age > RULE_DAYS:
            out.append((path, age, info))
    return out


def due_soon(data, today, window=14):
    out = []
    for path, info in sorted(data["pages"].items()):
        last = datetime.date.fromisoformat(info["last_tweak"])
        age = (today - last).days
        if RULE_DAYS - window < age <= RULE_DAYS:
            out.append((path, RULE_DAYS - age, info))
    return out


def report_text(data, today):
    stale = stale_pages(data, today)
    soon = due_soon(data, today)
    lines = [
        "# Page-freshness report — %s" % today.isoformat(),
        "",
        "Rule: no page goes longer than %d days without a minor improvement." % RULE_DAYS,
        "Tweaks stay Rock-reviewed before publish — proposals below are drafts.",
        "",
        "## Stale (over %d days) — %d page(s)" % (RULE_DAYS, len(stale)),
    ]
    if not stale:
        lines.append("None. Everything is fresh. Nice.")
    for path, age, info in stale:
        fam = family_of(path)
        lines.append("")
        lines.append("### %s — %d days since tweak (%s)" % (path, age, info["last_tweak"]))
        lines.append("Last tweak: %s" % info.get("tweak_note", "n/a"))
        lines.append("Proposed tweak ideas (check Clarity/GA first):")
        for idea in TWEAK_IDEAS.get(fam, TWEAK_IDEAS["default"]):
            lines.append("- %s" % idea)
    lines += ["", "## Due within 14 days — %d page(s)" % len(soon)]
    for path, left, info in soon:
        lines.append("- %s — %d days left (last: %s — %s)" % (path, left, info["last_tweak"], info.get("tweak_note", "n/a")[:60]))
    lines += ["",
              "Record a completed tweak with:",
              "  python3 tools/freshness.py --tweaked /path/to/page.html \"what changed\"",
              ""]
    return "\n".join(lines)


def main():
    data = load()
    today = datetime.date.today()
    if "--tweaked" in sys.argv:
        i = sys.argv.index("--tweaked")
        path, note = sys.argv[i + 1], sys.argv[i + 2]
        data["pages"].setdefault(path, {})
        data["pages"][path]["last_tweak"] = today.isoformat()
        data["pages"][path]["tweak_note"] = note
        data["pages"][path]["tweak_count"] = data["pages"][path].get("tweak_count", 0) + 1
        save(data)
        print("recorded tweak for %s" % path)
        return 0
    text = report_text(data, today)
    print(text)
    if "--write" in sys.argv:
        with open(REPORT, "w") as f:
            f.write(text)
        print("\nwrote %s" % REPORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
