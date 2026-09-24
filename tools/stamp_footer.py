#!/usr/bin/env python3
"""Stamp the shared footer (with social row) into every site page.

The footer template lives in tools/footer-template.html. This unifies the
previously divergent footers (5 variants) into one: social row (Podcast, X,
Instagram), copyright, contact, cookie links. Idempotent.
Usage: python3 tools/stamp_footer.py [--check]
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "tools", "footer-template.html")

FOOTER_RE = re.compile(r'[ \t]*<footer class="site-footer">.*?</footer>', re.DOTALL)


def targets():
    out = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", ".github", "tools", "workers", "ops")]
        for fn in sorted(files):
            if fn.endswith(".html"):
                out.append(os.path.join(root, fn))
    return sorted(out)


def stamp(path, template, check=False):
    with open(path) as f:
        html = f.read()
    if not FOOTER_RE.search(html):
        return "no-footer"
    new = FOOTER_RE.sub(lambda m: template.rstrip("\n"), html, count=1)
    if new == html:
        return "unchanged"
    if check:
        return "would-change"
    with open(path, "w") as f:
        f.write(new)
    return "stamped"


def main():
    check = "--check" in sys.argv
    template = open(TEMPLATE).read()
    results = {}
    for path in targets():
        results[os.path.relpath(path, ROOT)] = stamp(path, template, check)
    changed = [k for k, v in results.items() if v == "stamped"]
    missing = [k for k, v in results.items() if v == "no-footer"]
    print("targets=%d changed=%d no-footer=%d" % (len(results), len(changed), len(missing)))
    for k in missing:
        print("  NO FOOTER: " + k)


if __name__ == "__main__":
    sys.exit(main())
