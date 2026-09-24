#!/usr/bin/env python3
"""Wire the AI chat widget into every site page.

Adds chat.css <link> before </head> and chat-widget.js <script> before
</body>. Root-relative paths work at any page depth. The widget stays
silent until WORKER_URL is configured (post-deploy), so wiring early is
safe. Idempotent.
Usage: python3 tools/stamp_chat.py [--check]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_TAG = '<link rel="stylesheet" href="/assets/css/chat.css" />'
JS_TAG = '<script src="/assets/js/chat-widget.js" defer></script>'


def targets():
    out = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", ".github", "tools", "workers", "ops")]
        for fn in sorted(files):
            if fn.endswith(".html"):
                out.append(os.path.join(root, fn))
    return sorted(out)


def stamp(path, check=False):
    with open(path) as f:
        html = f.read()
    orig = html
    if "chat-widget.js" not in html and "</body>" in html:
        html = html.replace("</body>", "  " + JS_TAG + "\n</body>", 1)
    if "chat.css" not in html and "</head>" in html:
        html = html.replace("</head>", "  " + CSS_TAG + "\n</head>", 1)
    if html == orig:
        return "unchanged"
    if check:
        return "would-change"
    with open(path, "w") as f:
        f.write(html)
    return "stamped"


def main():
    check = "--check" in sys.argv
    results = {}
    for path in targets():
        results[os.path.relpath(path, ROOT)] = stamp(path, check)
    changed = [k for k, v in results.items() if v == "stamped"]
    print("targets=%d changed=%d" % (len(results), len(changed)))
    for k in changed:
        print("  " + k)


if __name__ == "__main__":
    sys.exit(main())
