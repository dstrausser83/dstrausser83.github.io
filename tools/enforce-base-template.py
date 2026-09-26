#!/usr/bin/env python3
"""Enforce the Dead Brands base template on every page.

Base template (David 2026-09-26 — standing rule): every page carries the same
core — consent-gated tracking (head consent defaults + consent.js), the
standard site header, and the standard site footer with cookie-policy +
cookie-settings links.

Redirect stubs (meta refresh + noindex) are exempt: they exist for 0 seconds
and firing tracker pixels on them would double-count the visit that lands on
the real page a moment later. Only their stale comments get cleaned.

Partials under tools/ are not pages and are skipped.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if ROOT.name != "dstrausser83.github.io":
    # allow running from repo root directly
    ROOT = Path("/home/hatch/workspace/sites/dstrausser83.github.io")

HEAD_CONSENT = """<!-- Consent defaults: analytics stays off until the visitor accepts (assets/js/consent.js) -->
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('consent', 'default', {ad_storage:'denied', analytics_storage:'denied', ad_user_data:'denied', ad_personalization:'denied'});
</script>"""

STALE_COMMENT = "<!-- Microsoft Clarity: heatmaps, click maps, session recordings (free) -->"

HEADER = (ROOT / "tools" / "canonical-header.html").read_text(encoding="utf-8")
FOOTER = (ROOT / "tools" / "canonical-footer.html").read_text(encoding="utf-8")

FOOTER_RE = re.compile(r'<footer class="site-footer">.*?</footer>', re.S)
HEAD_RE = re.compile(r"<head[^>]*>")


def is_redirect(h: str) -> bool:
    return 'http-equiv="refresh"' in h


def fix_page(p: Path) -> str:
    h = p.read_text(encoding="utf-8")
    orig = h
    h = h.replace(STALE_COMMENT, "")
    h = re.sub(r"\n{3,}", "\n\n", h)

    if is_redirect(h):
        if h != orig:
            p.write_text(h, encoding="utf-8")
            return "redirect stub: stale comment cleaned"
        return "redirect stub: untouched"

    if "gtag('consent', 'default'" not in h:
        h = HEAD_RE.sub(lambda m: m.group(0) + "\n" + HEAD_CONSENT, h, count=1)

    # NOTE: match an actual <script> tag, not the head comment which also
    # mentions consent.js in its text.
    if not re.search(r'<script[^>]*consent\.js', h):
        rel = p.parent.relative_to(ROOT)
        src = "/assets/js/consent.js" if str(rel) != "." else "assets/js/consent.js"
        h = h.replace("</body>", f'  <script src="{src}" defer></script>\n</body>', 1)

    if "site-header" not in h:
        h = h.replace("<body>", "<body>\n" + HEADER, 1)

    if "site-footer" not in h:
        if "</main>" in h:
            h = h.rsplit("</main>", 1)
            h = h[0] + "</main>\n" + FOOTER + h[1]
        else:
            h = h.replace("</body>", FOOTER + "\n</body>", 1)
    elif "DBConsent" not in h:
        # trimmed footer without cookie policy/settings links -> upgrade
        h = FOOTER_RE.sub(FOOTER, h, count=1)

    if h != orig:
        p.write_text(h, encoding="utf-8")
        return "FIXED"
    return "ok"


def main() -> int:
    changed, errors = [], []
    for p in sorted(ROOT.rglob("*.html")):
        if "tools/" in p.as_posix():
            continue
        try:
            status = fix_page(p)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{p}: {e}")
            continue
        if status not in ("ok", "redirect stub: untouched"):
            changed.append(f"{p.relative_to(ROOT)}: {status}")
    print(f"changed {len(changed)} pages:")
    for c in changed:
        print("  ", c)
    if errors:
        print("ERRORS:")
        for e in errors:
            print("  ", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
