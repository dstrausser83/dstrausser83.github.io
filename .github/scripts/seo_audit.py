#!/usr/bin/env python3
"""Deterministic SEO/AEO/indexing audit for dstrausser83.github.io.

Stdlib only. Fetches the live site + redirect domains, checks:
  HTTP health, sitemap coverage, JSON-LD schema (homepage + blog post),
  canonical/redirect architecture, tracker scan (actual resource loads only),
  image alt coverage.
Writes a markdown report to ops/reports/YYYY-MM-DD.md and prints a summary.
Exit 0 always; individual failures are recorded in the report.
"""
import datetime
import html.parser
import json
import os
import re
import sys
import urllib.request

SITE = "https://dstrausser83.github.io"
REDIRECT_SOURCES = [
    "http://deadbrands.co",
    "https://deadbrands.co",
    "http://davidstrausser.com",
    "https://davidstrausser.com",
]
TRACKER_HOSTS = [
    "googletagmanager.com", "google-analytics.com", "analytics.google.com",
    "facebook.net", "connect.facebook.net", "hotjar.com", "segment.io",
    "mixpanel.com", "amplitude.com", "doubleclick.net",
]
ALLOWED_RESOURCE_HOSTS = ["fonts.googleapis.com", "fonts.gstatic.com",
                          "dstrausser83.github.io"]
EXPECTED_JSONLD = ["BlogPosting", "FAQPage", "Person", "Organization"]
TIMEOUT = 25


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url, allow_redirects=True):
    """Returns (status, final_url_or_location, headers_dict, body_text)."""
    handlers = [urllib.request.ProxyHandler()]  # honor env proxy (Hatch egress)
    if not allow_redirects:
        handlers.append(NoRedirect())
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={"User-Agent": "DeadBrands-SEO-Audit/1.0"})
    try:
        with opener.open(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", errors="replace")
            return r.status, r.geturl(), dict(r.headers.items()), body
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return e.code, e.headers.get("Location", "") or url, dict(e.headers.items()), body
    except Exception as e:  # DNS, reset, TLS... -> failed check, never a crash
        return 0, url, {}, f"FETCH_ERROR: {type(e).__name__}: {e}"


class PageParser(html.parser.HTMLParser):
    """Title, meta description, canonical, JSON-LD types, resource hosts, imgs."""
    def __init__(self):
        super().__init__()
        self.jsonld_types = []
        self.resource_hosts = set()
        self.imgs = 0
        self.imgs_no_alt = 0
        self.title = ""
        self.meta_desc = ""
        self.canonical = ""
        self._in_title = False
        self._in_jsonld = False
        self._buf = ""

    def _resource(self, url):
        m = re.match(r"https?://([^/]+)", url or "")
        if m:
            self.resource_hosts.add(m.group(1).lower())

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and a.get("name", "").lower() == "description":
            self.meta_desc = a.get("content", "")
        elif tag == "link":
            if a.get("rel", "").lower() == "canonical":
                self.canonical = a.get("href", "")
            self._resource(a.get("href", ""))
        elif tag in ("script", "img", "iframe"):
            self._resource(a.get("src", ""))
            if tag == "img":
                self.imgs += 1
                if not (a.get("alt") or "").strip():
                    self.imgs_no_alt += 1
            if tag == "script" and a.get("type") == "application/ld+json":
                self._in_jsonld = True
                self._buf = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            try:
                data = json.loads(self._buf)
                for it in (data if isinstance(data, list) else [data]):
                    t = it.get("@type")
                    self.jsonld_types.extend(t if isinstance(t, list) else [t] if t else [])
                    for n in it.get("@graph", []):
                        if n.get("@type"):
                            self.jsonld_types.append(n.get("@type"))
            except Exception:
                pass

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        if self._in_jsonld:
            self._buf += data


def main():
    today = datetime.date.today().isoformat()
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # 1. Homepage
    st, final, headers, body = fetch(SITE + "/")
    check("homepage 200", st == 200, f"HTTP {st}")
    p = PageParser()
    p.feed(body)
    check("no Set-Cookie", "set-cookie" not in {k.lower() for k in headers}, "stateless")
    check("title present", bool(p.title), p.title[:70])
    check("meta description", bool(p.meta_desc), p.meta_desc[:70])
    check("canonical self", p.canonical.rstrip("/") == SITE, p.canonical or "missing")

    # 2. Tracker scan — actual resource loads only
    hits = [h for h in p.resource_hosts if any(t in h for t in TRACKER_HOSTS)]
    check("no trackers", not hits, "clean" if not hits else f"FOUND: {hits}")
    unexpected = sorted(h for h in p.resource_hosts
                        if not any(h == a or h.endswith("." + a) for a in ALLOWED_RESOURCE_HOSTS))
    check("resource allowlist", not unexpected, f"loads: {sorted(p.resource_hosts)}")

    # 3. JSON-LD across homepage + one blog post
    _, _, _, sm = fetch(SITE + "/sitemap.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", sm)
    post_urls = [u for u in urls if "/blog/posts/" in u]
    all_types = set(p.jsonld_types)
    post_checked = ""
    if post_urls:
        _, _, _, pb = fetch(post_urls[0])
        pp = PageParser()
        pp.feed(pb)
        all_types |= set(pp.jsonld_types)
        post_checked = post_urls[0].rsplit("/", 1)[-1]
    for t in EXPECTED_JSONLD:
        check(f"JSON-LD {t}", t in all_types, "present" if t in all_types else "MISSING")

    # 4. Static SEO files
    for path in ["/llms.txt", "/robots.txt", "/sitemap.xml"]:
        st2, _, _, b2 = fetch(SITE + path)
        check(f"{path} 200", st2 == 200, f"HTTP {st2}, {len(b2)} bytes")

    # 5. Every sitemap URL returns 200
    bad = []
    for u in urls:
        s, _, _, _ = fetch(u)
        if s != 200:
            bad.append(f"{u} -> {s}")
    check("sitemap URLs 200", not bad, f"{len(urls)} checked" if not bad else "; ".join(bad[:5]))

    # 6. Redirect architecture preserved (expect 301/308 -> github.io)
    for src in REDIRECT_SOURCES:
        s, loc, _, _ = fetch(src, allow_redirects=False)
        ok = s in (301, 302, 307, 308) and "dstrausser83.github.io" in (loc or "")
        check(f"redirect {src}", ok, f"HTTP {s} -> {loc}")

    # 7. Image alt coverage (homepage)
    check("images have alt", p.imgs_no_alt == 0, f"{p.imgs} imgs, {p.imgs_no_alt} missing alt")

    passed = sum(1 for _, ok, _ in checks if ok)
    lines = [f"# SEO/AEO audit — {today}", "",
             f"**{passed}/{len(checks)} checks passed.**",
             f"Blog post sampled: {post_checked or 'none'}", "",
             "| Check | Result | Detail |", "|---|---|---|"]
    for name, ok, detail in checks:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    lines += ["", "_Deterministic audit via GitHub Actions (free). "
              "FAILs are informational — no architecture changes without approval._", ""]
    report = "\n".join(lines)

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))  # .github/scripts/ -> repo root
    out_dir = os.path.join(repo_root, "ops", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{today}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"audit {today}: {passed}/{len(checks)} passed -> {out_path}")
    for name, ok, detail in checks:
        if not ok:
            print(f"  FAIL: {name} — {detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
