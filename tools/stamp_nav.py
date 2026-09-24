#!/usr/bin/env python3
"""Stamp the shared nav (with Services dropdown) into every site page.

The nav template lives in tools/nav-template.html with %%A_<key>%% tokens.
Each target file maps to an active key; the matching token becomes "active",
all others become "". New pages should include the raw template tokens and
be listed in ACTIVE_MAP — the stamper resolves them.

Usage: python3 tools/stamp_nav.py [--check]
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "tools", "nav-template.html")

# file (relative to ROOT) -> active nav key ("" = none)
ACTIVE_MAP = {
    "index.html": "",
    "about.html": "about",
    "services.html": "services services_index",
    "services/dead-brands.html": "services dead_brands",
    "services/small-business-growth.html": "services small_business_growth",
    "services/sales-expert.html": "services sales_expert",
    "services/marketing-expert.html": "services marketing_expert",
    "services/business-development.html": "services business_development",
    "services/tech-consulting.html": "services tech_consulting",
    "services/odoo.html": "services odoo",
    "services/sap-business-one.html": "services sap_business_one",
    "services/erp.html": "services erp",
    "services/dead-brands/index.html": "services dead_brands",
    "services/small-business-growth/index.html": "services small_business_growth",
    "services/sales-expert/index.html": "services sales_expert",
    "services/marketing-expert/index.html": "services marketing_expert",
    "services/business-development/index.html": "services business_development",
    "services/tech-consulting/index.html": "services tech_consulting",
    "services/odoo/index.html": "services odoo",
    "services/sap-business-one/index.html": "services sap_business_one",
    "services/erp/index.html": "services erp",
    "resources.html": "resources",
    "blog/index.html": "blog",
    "blog/author.html": "blog",
}
# blog posts all get the blog key
BLOG_POSTS_DIR = os.path.join(ROOT, "blog", "posts")

NAV_RE = re.compile(
    r'(<nav class="site-nav" id="site-nav" aria-label="Primary">)(.*?)(</nav>)',
    re.DOTALL,
)
TOKEN_RE = re.compile(r"%%A_([a-z_]+)%%")


def render_nav(active_keys):
    tpl = open(TEMPLATE).read().rstrip() + "\n"
    def repl(m):
        return "active" if m.group(1) in active_keys else ""
    return TOKEN_RE.sub(repl, tpl)


def stamp_file(path, active_keys, check=False):
    with open(path) as f:
        html = f.read()
    m = NAV_RE.search(html)
    if not m:
        return "no-nav"
    new_nav = m.group(1) + "\n" + render_nav(active_keys) + "      " + m.group(3)
    new_html = html[: m.start()] + new_nav + html[m.end():]
    if new_html == html:
        return "unchanged"
    if check:
        return "would-change"
    with open(path, "w") as f:
        f.write(new_html)
    return "stamped"


def main():
    check = "--check" in sys.argv
    targets = dict(ACTIVE_MAP)
    if os.path.isdir(BLOG_POSTS_DIR):
        for fn in sorted(os.listdir(BLOG_POSTS_DIR)):
            if fn.endswith(".html"):
                targets[os.path.join("blog", "posts", fn)] = "blog"
    results = {}
    for rel, keys in sorted(targets.items()):
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            results[rel] = "missing"
            continue
        results[rel] = stamp_file(path, set(keys.split()), check)
    changed = [k for k, v in results.items() if v in ("stamped", "would-change")]
    print("targets=%d changed=%d" % (len(results), len(changed)))
    for k, v in results.items():
        if v not in ("unchanged",):
            print("  %-45s %s" % (k, v))
    # also report leftover tokens anywhere (should be none)
    leftovers = []
    for rel in targets:
        path = os.path.join(ROOT, rel)
        if os.path.exists(path) and "%%A_" in open(path).read():
            leftovers.append(rel)
    if leftovers:
        print("LEFTOVER TOKENS in:", leftovers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
