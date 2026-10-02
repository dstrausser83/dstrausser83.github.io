#!/usr/bin/env python3
"""CI: enforce the Dead Brands base template on every page.

Standing rule (David 2026-09-26): every page carries the same core —
consent-gated tracking (head consent defaults + consent.js script tag),
the standard site header, and the standard site footer including the
cookie-policy + cookie-settings (DBConsent) links.

Exempt: partials under tools/ (not pages) and meta-refresh redirect stubs
(noindex; firing tracker pixels on a 0-second redirect would double-count
the visit that lands on the real page a moment later).

Run tools/enforce-base-template.py to fix violations, then re-run this.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_RE = re.compile(r"<script[^>]*consent\.js")


def main() -> int:
    failures = {}
    checked = 0
    for p in sorted(ROOT.rglob("*.html")):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith("tools/"):
            continue
        h = p.read_text(encoding="utf-8")
        if 'http-equiv="refresh"' in h:
            continue  # redirect stub, exempt by design
        checked += 1
        missing = []
        if "gtag('consent', 'default'" not in h:
            missing.append("head consent-defaults")
        if not SCRIPT_RE.search(h):
            missing.append("consent.js script")
        if "site-header" not in h:
            missing.append("site-header")
        if "site-footer" not in h:
            missing.append("site-footer")
        elif "DBConsent" not in h:
            missing.append("footer cookie-settings links")
        if missing:
            failures[rel] = missing
    if failures:
        print(f"FAIL: {len(failures)}/{checked} pages violate the base template:")
        for name, missing in failures.items():
            print(f"  - {name}: missing {', '.join(missing)}")
        print("Fix: run tools/enforce-base-template.py, verify, re-push.")
        return 1
    print(f"OK: all {checked} pages carry the base template.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
