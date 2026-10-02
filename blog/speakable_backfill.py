#!/usr/bin/env python3
"""Backfill speakable schema into BlogPosting JSON-LD of archived blog posts.

String-surgery approach: inserts the speakable block right after the single-line
"keywords" line inside the BlogPosting <script type="application/ld+json"> block,
preserving the file's existing 2-space indentation byte-for-byte. Validates each
file after edit (JSON-LD parses, speakable present, HTML parses).

Usage:
  speakable_backfill.py --test            # patch first file only, print unified diff
  speakable_backfill.py --apply           # patch all files
  speakable_backfill.py --file X.html     # patch one specific file
"""
import json
import os
import re
import sys
from html.parser import HTMLParser

POSTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posts")
SCRIPT_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
KW_RE = re.compile(r'^(\s*)"keywords": "[^"]*",\s*$', re.M)


def find_blogposting_block(html):
    """Return (match_obj, raw_json, parsed) for the BlogPosting block, or None."""
    for m in SCRIPT_RE.finditer(html):
        raw = m.group(1)
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if isinstance(d, dict) and d.get("@type") == "BlogPosting":
            return m, raw, d
    return None


def insert_speakable(raw):
    """Insert the speakable block after the keywords line. Returns new raw or None."""
    m = KW_RE.search(raw)
    if not m:
        return None
    ind = m.group(1)
    block = (
        f'{ind}"speakable": {{\n'
        f'{ind}  "@type": "SpeakableSpecification",\n'
        f'{ind}  "cssSelector": ["h1", ".executive-summary", "meta[name=\'description\']"]\n'
        f'{ind}}},\n'
    )
    return raw[: m.end()] + "\n" + block.rstrip("\n") + raw[m.end():]


def validate_html(html):
    """Basic well-formedness check via HTMLParser; returns error str or None."""
    class Checker(HTMLParser):
        def error(self, message):
            raise ValueError(message)
    try:
        Checker().feed(html)
    except Exception as e:
        return str(e)
    if html.count("<script") != html.count("</script>"):
        return "unbalanced script tags"
    return None


def patch_file(path, dry_run=False):
    html = open(path, encoding="utf-8").read()
    found = find_blogposting_block(html)
    if not found:
        return ("SKIP", "no BlogPosting JSON-LD block")
    m, raw, d = found
    if "speakable" in d:
        return ("SKIP", "speakable already present")
    new_raw = insert_speakable(raw)
    if new_raw is None:
        return ("SKIP", "keywords line not in expected single-line form")
    # Validate the new JSON before touching the file
    try:
        d2 = json.loads(new_raw)
    except Exception as e:
        return ("SKIP", f"patched JSON invalid: {e}")
    if d2.get("speakable", {}).get("@type") != "SpeakableSpecification":
        return ("SKIP", "speakable shape wrong after insert")
    new_html = html[: m.start(1)] + new_raw + html[m.end(1):]
    err = validate_html(new_html)
    if err:
        return ("SKIP", f"HTML validation failed: {err}")
    if not dry_run:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_html)
    return ("PATCHED", f"speakable inserted ({len(new_html) - len(html):+d} bytes)")


def main():
    args = sys.argv[1:]
    if args == ["--test"]:
        files = sorted(f for f in os.listdir(POSTS_DIR) if f.endswith(".html"))
        target = None
        for f in files:
            found = find_blogposting_block(open(os.path.join(POSTS_DIR, f), encoding="utf-8").read())
            if found and "speakable" not in found[2]:
                target = f
                break
        if not target:
            print("No patchable file found for test.")
            return 1
        path = os.path.join(POSTS_DIR, target)
        before = open(path, encoding="utf-8").read()
        status, detail = patch_file(path, dry_run=True)
        print(f"TEST file: {target} -> {status}: {detail}")
        if status != "PATCHED":
            return 1
        # Show the actual diff that --apply would produce
        import difflib
        found = find_blogposting_block(before)
        raw = found[1]
        new_raw = insert_speakable(raw)
        diff = difflib.unified_diff(raw.splitlines(), new_raw.splitlines(),
                                   fromfile="before", tofile="after", lineterm="")
        print("\n".join(diff))
        return 0
    if args == ["--apply"]:
        files = sorted(f for f in os.listdir(POSTS_DIR) if f.endswith(".html"))
        results = {}
        for f in files:
            status, detail = patch_file(os.path.join(POSTS_DIR, f))
            results.setdefault(status, []).append((f, detail))
            print(f"{f}: {status} — {detail}")
        print(f"\nPATCHED: {len(results.get('PATCHED', []))}  SKIPPED: {len(results.get('SKIP', []))}")
        return 0
    if len(args) == 2 and args[0] == "--file":
        status, detail = patch_file(os.path.join(POSTS_DIR, args[1]))
        print(f"{args[1]}: {status} — {detail}")
        return 0 if status == "PATCHED" else 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
