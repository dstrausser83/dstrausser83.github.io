#!/usr/bin/env python3
"""Build a blog post page from a markdown draft with frontmatter.

Usage: build_post.py <draft.md> [--image <file.jpg>] [--video <file.mp4>]
Reads frontmatter (title, date, tags, excerpt, description, keywords, slug,
image, video, lane), converts markdown body to HTML, writes blog/posts/<slug>.html,
copies media into blog/images/ and blog/videos/, and updates blog/posts.json.

SEO/AEO features:
  - <title>, meta description, meta keywords, canonical, Open Graph / article tags
  - "## Quick answer" section wrapped in a styled callout (AEO direct-answer)
  - "## Frequently asked questions" -> FAQPage JSON-LD (AEO)
"""
import json, re, sys, os, hashlib
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")  # David's rule: real ET, not UTC-4 approx

def format_pub_display(published_at_iso, post_date):
    """'September 23, 2026 at 3:12 PM ET'; falls back to the plain date."""
    try:
        dt = datetime.fromisoformat(
            published_at_iso.replace("Z", "+00:00")).astimezone(ET)
        return dt.strftime("%B %d, %Y at %I:%M %p ET").replace(" 0", " ")
    except Exception:
        return post_date

BLOG_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BLOG_DIR, "posts")
IMAGES_DIR = os.path.join(BLOG_DIR, "images")
VIDEOS_DIR = os.path.join(BLOG_DIR, "videos")
INDEX_JSON = os.path.join(BLOG_DIR, "posts.json")

def slugify(title):
    s = title.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    return re.sub(r"[\s-]+", "-", s).strip("-")[:60]

def parse_frontmatter(text):
    fm, body = {}, text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            for line in text[3:end].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip().strip('"')
            body = text[end+3:].strip()
    return fm, body

# UTM attribution for Quaint Business Solutions links — David's order 2026-09-23:
# every quaintbusiness.com link must credit Dead Brands / David Strausser in
# Quaint's analytics (utm_source=deadbrands, utm_campaign=david-strausser).
QUAINT_UTM = ("utm_source=deadbrands&utm_medium=website"
              "&utm_campaign=david-strausser")

def tag_quaint_url(url, slug):
    if "quaintbusiness.com" not in url or "utm_source=" in url:
        return url
    content = f"blog-{slug}-inline" if slug else "blog-inline"
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{QUAINT_UTM}&utm_content={content}"

def md_inline(t, slug=None):
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    def _link(m):
        url = tag_quaint_url(m.group(2), slug)
        return f'<a href="{url}" target="_blank" rel="noopener">{m.group(1)}</a>'
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, t)
    return t

def md_to_html(body, slug=None):
    """Markdown -> HTML. ('## Quick answer' is extracted before this runs and
    becomes the Executive Summary box — never rendered in the body.)"""
    out, in_list, list_tag = [], False, ""
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("### "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<h3>{md_inline(s[4:], slug)}</h3>")
        elif s.startswith("## "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<h2>{md_inline(s[3:], slug)}</h2>")
        elif s.startswith("# "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<h1>{md_inline(s[2:], slug)}</h1>")
        elif s.startswith("> "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<blockquote>{md_inline(s[2:], slug)}</blockquote>")
        elif re.match(r"^[-*] ", s):
            if not in_list: out.append("<ul>"); in_list, list_tag = True, "ul"
            out.append(f"<li>{md_inline(s[2:], slug)}</li>")
        elif re.match(r"^\d+\. ", s):
            if not in_list or list_tag != "ol":
                if in_list: out.append(f"</{list_tag}>")
                out.append("<ol>"); in_list, list_tag = True, "ol"
            out.append(f"<li>{md_inline(re.sub(r'^\d+\. ', '', s), slug)}</li>")
        elif s == "":
            if in_list: out.append(f"</{list_tag}>"); in_list = False
        elif s == "---":
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append("<hr />")
        else:
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<p>{md_inline(s, slug)}</p>")
    if in_list: out.append(f"</{list_tag}>")
    return "\n".join(out)

def extract_quick_answer(body):
    """Pull the '## Quick answer' section out of the markdown body.
    Returns (body_without_qa, quick_answer_markdown). The quick answer becomes
    the Executive Summary box content (David 2026-09-26) — no duplicate block."""
    out, qa, in_qa = [], [], False
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("## "):
            if s[3:].strip().lower() == "quick answer":
                in_qa = True
                continue
            in_qa = False
        if in_qa:
            qa.append(line)
        else:
            out.append(line)
    return "\n".join(out), "\n".join(qa).strip()

def quick_answer_html(qa_md, slug=None):
    """Quick-answer markdown -> paragraph HTML for the summary box."""
    return "\n".join(
        f"<p>{md_inline(s, slug)}</p>"
        for s in (qa_md or "").split("\n") if s.strip()
    )

def extract_faq(body):
    """Pull (question, answer) pairs from '## Frequently asked questions'."""
    faqs, in_faq, q, a = [], False, None, []
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("## "):
            if q:
                faqs.append((q, " ".join(a).strip())); q, a = None, []
            in_faq = (s[3:].strip().lower() == "frequently asked questions")
        elif in_faq and s.startswith("### "):
            if q:
                faqs.append((q, " ".join(a).strip()))
            q, a = s[4:].strip(), []
        elif in_faq and q and s and not s.startswith("#"):
            a.append(re.sub(r"\*\*(.+?)\*\*", r"\1", s))
    if q:
        faqs.append((q, " ".join(a).strip()))
    return [(q, an) for q, an in faqs if q and an]

def faq_jsonld(faqs, slug=None):
    if not faqs:
        return ""
    def tag_faq_links(a):
        # FAQ answers carry markdown links; tag bare Quaint trial URLs the
        # same way the page body does so no untracked Odoo link ships (2026-09-24).
        return re.sub(r"\]\((https://quaintbusiness\.com[^)]*)\)",
                      lambda m: "](" + tag_quaint_url(m.group(1), slug) + ")", a)
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": tag_faq_links(a)}}
            for q, a in faqs
        ],
    }
    return '<script type="application/ld+json">\n' + json.dumps(data, indent=2) + "\n</script>"

def article_jsonld(title, description, slug, post_date, image_rel, tags):
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": description,
        "datePublished": post_date,
        "author": {
            "@type": "Person",
            "name": "David Strausser",
            "url": "https://deadbrands.co/",
            "jobTitle": "CEO of Dead Brands, LLC; Head of Sales for Quaint Business Solutions (SAP Business One & Odoo)",
        },
        "publisher": {
            "@type": "Organization",
            "name": "Dead Brands, LLC",
        },
        "mainEntityOfPage": f"https://deadbrands.co/blog/posts/{slug}.html",
        "keywords": ", ".join(tags),
    }
    if image_rel:
        data["image"] = f"https://deadbrands.co/blog/{image_rel}"
    return '<script type="application/ld+json">\n' + json.dumps(data, indent=2) + "\n</script>"

MEET_LINK = "https://app.apollo.io/#/meet/david_strausser_175"
TRIAL_LINK = ("https://quaintbusiness.com/tryodoo?utm_source=deadbrands"
              "&utm_medium=website&utm_campaign=david-strausser"
              "&utm_content=blog-cta-trial")
AUTHOR_URL = "../author.html"
HEADSHOT = "../../assets/photos/published/david-headshot-blazer.jpg"


def load_cta_templates():
    """Load CTA template library. Returns (templates dict, rotation list)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cta-templates.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("templates", {}), data.get("rotation", [])
    except (OSError, json.JSONDecodeError):
        return {}, []


def cta_html(slug, cta_name=None, cta_custom=None):
    """End-of-post CTA (David's rule 2026-09-23, extended 2026-09-26).

    cta_name: a template key from cta-templates.json (e.g. 'meeting').
    cta_custom: dict with heading/body/button/url for a one-off custom CTA.
    Neither given -> rotate through the 'rotation' list by slug hash.
    """
    templates, rotation = load_cta_templates()
    chosen = None
    if cta_custom:
        chosen = cta_custom
    elif cta_name and cta_name in templates:
        chosen = templates[cta_name]
    elif rotation:
        pick = rotation[int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(rotation)]
        chosen = templates.get(pick)
    if not chosen:
        # Fallback: original meeting CTA so a post never ships without one.
        chosen = {"heading": "Let's talk about your business",
                  "body": ("Running on spreadsheets, QuickBooks, or an ERP that fights you? "
                           "Grab a free 30-minute call — I'll tell you straight whether "
                           "SAP Business One or Odoo is the right move, and what it really costs."),
                  "button": "Book a Meeting with Me",
                  "url": MEET_LINK}
    heading = html_escape(chosen.get("heading", ""))
    body = html_escape(chosen.get("body", ""))
    button = html_escape(chosen.get("button", "Learn more"))
    url = html_escape_attr(chosen.get("url", "/"))
    target = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
    return f"""<section class="post-cta">
          <h2>{heading}</h2>
          <p>{body}</p>
          <a class="cta-btn" href="{url}"{target}>{button}</a>
        </section>"""


def html_escape(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def summary_html(inner_html):
    """Sharpie-style Executive Summary box under the hero (David 2026-09-26).
    Marker-font label sits ON the top border (border breaks around the text,
    never through it); hand-drawn wobbly border; auto-resizes with content.
    inner_html is ready-to-render HTML (the Quick Answer paragraphs)."""
    if not (inner_html or "").strip():
        return ""
    return f"""<aside class="post-summary" aria-label="Executive Summary">
          <p class="post-summary-label"><span>Executive Summary</span></p>
          {inner_html.strip()}
        </aside>"""


def author_box_html():
    return f"""<section class="author-box">
          <img src="{HEADSHOT}" alt="David Strausser" width="96" height="96" loading="lazy" />
          <div>
            <p class="author-name">Written by <a href="{AUTHOR_URL}">David Strausser</a></p>
            <p>David is CEO of <strong>Dead Brands, LLC</strong> and Head of Sales
            (contracted) for <strong>Quaint Business Solutions</strong> — an ERP
            veteran of over a decade across <strong>SAP Business One</strong> and
            <strong>Odoo</strong>. Ex-General Manager (Northeast) at Vision33 and
            VP of Business Development at SEIDOR. Single dad, guitarist, Eagles fan.</p>
            <p class="author-links"><a href="https://x.com/dstrausser83" target="_blank" rel="noopener">X / Twitter</a>
            &middot; <a href="https://open.spotify.com/show/1CZh0QdNr5Nn8CD8kInMAJ" target="_blank" rel="noopener">Shark Bite Biz podcast</a></p>
          </div>
        </section>"""


def shop_block_html():
    """Store promo under the post CTA (David 2026-09-26): random product from
    products.json + view-all link. Random per page load via JS."""
    return """<section class="post-shop">
          <p class="eyebrow">Shop the brand</p>
          <h2>Take a piece of the bite with you</h2>
          <div class="post-shop-card" id="post-shop-card"><p>Loading the goods&hellip;</p></div>
          <a class="post-shop-all" href="/merch/">View all in the store &rarr;</a>
        </section>
        <script>
        (function () {
          var el = document.getElementById("post-shop-card");
          if (!el) return;
          function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
          fetch("/assets/data/products.json").then(function (r) { return r.json(); }).then(function (d) {
            var ps = (d.products || []).filter(function (p) { return p && p.image && p.name; });
            if (!ps.length) { el.innerHTML = ""; return; }
            var p = ps[Math.floor(Math.random() * ps.length)];
            var url = esc(p.url || "/merch/");
            el.innerHTML = '<a href="' + url + '"><img src="' + esc(p.image) + '" alt="' + esc(p.alt || p.name) + '" loading="lazy" width="96" height="96" /></a>'
              + '<div><p class="post-shop-name"><a href="' + url + '">' + esc(p.name) + '</a></p>'
              + '<p class="post-shop-price">$' + Number(p.price).toFixed(2) + '</p></div>';
          }).catch(function () { el.innerHTML = ""; });
        })();
        </script>"""


CTA_CSS = """
    .post-cta { background: var(--card); border: 1.5px solid var(--accent); border-radius: var(--radius); padding: 1.5rem; margin: 2.5rem 0 1.5rem; text-align: center; }
    .post-cta h2 { margin-top: 0; }
    .post-cta p { color: var(--muted); max-width: 34rem; margin: 0.5rem auto 1.25rem; }
    .cta-btn { display: inline-block; background: var(--accent); color: #fff; font-weight: 700; padding: 0.8rem 1.75rem; border-radius: 999px; text-decoration: none; }
    .cta-btn:hover { filter: brightness(1.1); }
    .author-box { display: flex; gap: 1.25rem; align-items: flex-start; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 1.25rem; margin: 0 0 2rem; }
    .author-box img { border-radius: 50%; object-fit: cover; flex-shrink: 0; }
    .author-box p { margin: 0.4rem 0; color: var(--muted); font-size: 0.95rem; }
    .author-box .author-name { font-size: 1.05rem; color: inherit; font-weight: 700; }
    .author-links a { font-size: 0.9rem; }
"""

SHOP_CSS = """
    .post-shop { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 1.5rem; margin: 0 0 2rem; text-align: center; }
    .post-shop h2 { margin: 0.25rem 0 0.5rem; }
    .post-shop-card { display: flex; gap: 1rem; align-items: center; justify-content: center; margin: 1rem auto; max-width: 26rem; text-align: left; min-height: 96px; }
    .post-shop-card img { width: 96px; height: 96px; object-fit: cover; border-radius: 12px; flex-shrink: 0; }
    .post-shop-name { font-weight: 700; margin: 0 0 0.25rem; }
    .post-shop-price { color: var(--accent-deep); font-weight: 700; margin: 0; }
    .post-shop-all { display: inline-block; margin-top: 0.5rem; font-weight: 700; }
"""


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<!-- Consent defaults: analytics stays off until the visitor accepts (assets/js/consent.js) -->
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('consent', 'default', {{ad_storage:'denied', analytics_storage:'denied', ad_user_data:'denied', ad_personalization:'denied'}});
</script>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} — David Strausser</title>
  <meta name="description" content="{description}" />
  {meta_keywords}
  <link rel="canonical" href="https://deadbrands.co/blog/posts/{slug}.html" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  {og_image}
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{description}" />
  {twitter_image}
  <link rel="icon" href="../../assets/img/favicon.png" type="image/png" />
  <link rel="apple-touch-icon" href="../../assets/img/apple-touch-icon.png" />
  <link rel="stylesheet" href="../../assets/css/styles.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Permanent+Marker&display=swap" />
  <style>
    .post-hero img {{ width: 100%; border-radius: var(--radius); border: 1.5px solid var(--line); }}
    .post-hero video {{ width: 100%; border-radius: var(--radius); border: 1.5px solid var(--line); margin-bottom: 1rem; }}
    .post-meta {{ color: var(--muted); font-size: 0.95rem; margin: 0.5rem 0 1.5rem; }}
    .post-tags span {{ display: inline-block; background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: 0.2rem 0.8rem; font-size: 0.85rem; margin-right: 0.4rem; }}
    .post-body h2 {{ margin-top: 2rem; }} .post-body h3 {{ margin-top: 1.5rem; }}
    .post-body blockquote {{ border-left: 3px solid var(--accent); margin: 1.5rem 0; padding: 0.5rem 1rem; color: var(--muted); font-style: italic; }}
    .post-hero-card {{ position: relative; border-radius: var(--radius); overflow: hidden; margin: 1.5rem 0 0; }}
    .post-hero-card img {{ width: 100%; height: auto; display: block; }}
    .post-inline {{ margin: 1.75rem 0; }}
    .post-inline img {{ max-width: 100%; height: auto; display: block; border-radius: var(--radius); }}
    .post-body img {{ max-width: 100%; height: auto; }}
    .post-hero-card .hero-title-overlay {{ position: absolute; left: 0; right: 0; bottom: 0; padding: 3.5rem 1.75rem 1.5rem;
      background: linear-gradient(to top, rgba(10,5,3,0.88) 0%, rgba(10,5,3,0.45) 55%, rgba(10,5,3,0) 100%); }}
    .post-hero-card .hero-title-overlay h1 {{ color: #fff; margin: 0 0 0.5rem; font-size: clamp(1.6rem, 4vw, 2.6rem); line-height: 1.15; }}
    .post-hero-card .post-meta {{ color: rgba(255,255,255,0.85); margin: 0; font-size: 0.95rem; }}
    .post-hero-card .post-meta a {{ color: #fff; }}
    @media (max-width: 640px) {{
      .post-hero-card img {{ height: 380px; object-fit: cover; }}
      .post-hero-card .hero-title-overlay {{ padding: 3rem 1.25rem 1.25rem; }}
      .post-hero-card .hero-title-overlay h1 {{ font-size: 1.4rem; line-height: 1.2; }}
      .post-hero-card .post-meta {{ font-size: 0.85rem; }}
    }}
    .post-summary {{ position: relative; background: var(--accent-deep); color: #fff;
      border: 3px solid #1a1a1a;
      border-radius: 255px 15px 225px 15px / 15px 225px 15px 255px;
      padding: 1.75rem 1.75rem 1.25rem; margin: 2rem 0 0; }}
    .post-summary p {{ margin: 0.35rem 0; color: #fff; }}
    .post-summary .post-summary-label {{ position: absolute; top: -1.35rem; left: 1.25rem; margin: 0; }}
    .post-summary .post-summary-label span {{ font-family: 'Permanent Marker', 'Segoe Print', cursive;
      font-size: 1.5rem; color: #fff; background: var(--accent-deep);
      padding: 0 0.6rem; text-transform: none; letter-spacing: 0.02em; }}
    .back-link {{ display: inline-block; margin-bottom: 1.5rem; }}
{cta_css}
{shop_css}
  </style>
  {faq_jsonld}
  {article_jsonld}
</head>
<body>
  <header class="site-header" id="site-header">
    <div class="wrap header-inner">
      <a class="brand" href="../../index.html" aria-label="Dead Brands, LLC — home">
        <img class="brand-logo" src="../../assets/img/dead-brands-logo.png" alt="Dead Brands logo" width="40" height="40" />
        <span class="brand-name">Dead Brands <small>LLC</small></span>
      </a>
      <button class="nav-toggle" id="nav-toggle" aria-expanded="false" aria-controls="site-nav" aria-label="Open menu">
        <span></span><span></span><span></span>
      </button>
      <nav class="site-nav" id="site-nav" aria-label="Primary">
        <a href="/about.html" class="%%A_about%%">About</a>
        <div class="nav-drop">
          <button class="nav-drop-toggle %%A_services%%" aria-haspopup="true" aria-expanded="false" type="button">Services <svg class="caret" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" focusable="false"><path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
          <div class="nav-drop-menu" role="menu" aria-label="Services">
            <div class="nav-drop-cols">
              <div class="nav-drop-col">
                <p class="nav-drop-label">Grow your business</p>
                <a href="/services/dead-brands.html" class="%%A_dead_brands%%" role="menuitem">Dead Brand Stuff</a>
                <a href="/services/small-business-growth.html" class="%%A_small_business_growth%%" role="menuitem">Small Business Growth</a>
                <a href="/services/sales-expert.html" class="%%A_sales_expert%%" role="menuitem">Sales Expert</a>
                <a href="/services/marketing-expert.html" class="%%A_marketing_expert%%" role="menuitem">Marketing Expert</a>
                <a href="/services/business-development.html" class="%%A_business_development%%" role="menuitem">Biz Dev</a>
              </div>
              <div class="nav-drop-col">
                <p class="nav-drop-label">Technology &amp; ERP</p>
                <a href="/services/tech-consulting.html" class="%%A_tech_consulting%%" role="menuitem">Tech Consulting</a>
                <a href="/services/odoo.html" class="%%A_odoo%%" role="menuitem">Odoo</a>
                <a href="/services/sap-business-one.html" class="%%A_sap_business_one%%" role="menuitem">SAP Business One</a>
                <a href="/services/erp.html" class="%%A_erp%%" role="menuitem">ERP</a>
              </div>
            </div>
            <a href="/services.html" class="nav-drop-all %%A_services_index%%">View all services <span aria-hidden="true">&rarr;</span></a>
          </div>
        </div>
        <a href="/resources.html" class="%%A_resources%%">Resource Center</a>
        <a href="/blog/index.html" class="%%A_blog%%">Blog</a>
        <a href="/case-studies/" class="%%A_case_studies%%">Case Studies</a>
        <a href="/merch/" class="%%A_shop%%">Shop</a>
        <a href="/index.html#contact" class="nav-cta">Work With Me</a>
      </nav>
    </div>
  </header>
  <main>
    <article class="section">
      <div class="wrap narrow">
        <a class="back-link" href="../index.html">&larr; All posts</a>
        {hero}
        {summary}
        <div class="post-body prose">
{body}
        </div>
        <p class="post-tags">{tags}</p>
        {cta}
        {shop_block}
        {author_box}
      </div>
    </article>
  </main>
  <footer class="site-footer">
    <div class="wrap">
      <p>&copy; <span id="year">2026</span> Dead Brands, LLC. All rights reserved. &middot; <a href="/cookies.html">Cookie Policy</a> &middot; <a href="#" onclick="window.DBConsent && window.DBConsent.show(); return false;">Cookie settings</a></p>
    </div>
  </footer>
  <script>document.getElementById('year').textContent = new Date().getFullYear();</script>
  <script src="../../assets/js/main.js" defer></script>
  <script src="../../assets/js/consent.js" defer></script>
</body>
</html>
"""

def html_escape_attr(s):
    """Escape a string for use inside a double-quoted HTML attribute."""
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def insert_inline_images(body_html, inline_images):
    """Insert inline <figure> images into the article body at ~1/4, ~1/2 and
    ~3/4 through the paragraphs (David 2026-09-26: hero + 2-3 blog images).
    inline_images: list of (rel_path, alt_text, (w, h) or None)."""
    if not inline_images:
        return body_html
    # Split on paragraph closes; keep delimiters.
    parts = body_html.split("</p>")
    n_para = len(parts) - 1  # last element is tail after final </p>
    if n_para < 4:
        # Too short to split sensibly — append figures at the end.
        figs = "".join(inline_figure_html(rel, alt, dims)
                       for rel, alt, dims in inline_images)
        return body_html + figs
    # Insertion paragraph indices (0-based) for up to 3 images.
    fracs = [i / (len(inline_images) + 1) for i in range(1, len(inline_images) + 1)]
    targets = sorted({max(1, min(n_para - 1, int(n_para * f))) for f in fracs})
    offset = 0
    for t, (rel, alt, dims) in zip(targets, inline_images):
        idx = t + offset
        if idx < len(parts):
            parts[idx] = parts[idx] + inline_figure_html(rel, alt, dims)
            offset += 1
    return "</p>".join(parts)


def inline_figure_html(rel, alt_raw, dims):
    alt = html_escape_attr(re.sub(r"\s+", " ", (alt_raw or "").strip())[:160] or "Article illustration")
    size_attrs = f' width="{dims[0]}" height="{dims[1]}"' if dims else ""
    return (f'<figure class="post-inline"><img src="../{rel}" alt="{alt}"'
            f'{size_attrs} loading="lazy" /></figure>')


def build(draft_path, image_srcs=None, video_src=None, image_alts=None,
          cta_name=None, cta_custom=None):
    # image_srcs: list of image files — [hero, inline1, inline2, inline3].
    # Backcompat: a single string is treated as [hero].
    with open(draft_path, encoding="utf-8") as f:
        text = f.read()
    # Scribe drafts can carry a UTF-8 BOM which breaks frontmatter
    # detection and produces "Untitled" posts — strip it (2026-09-23).
    text = text.lstrip("\ufeff")
    fm, body = parse_frontmatter(text)
    title = (fm.get("title") or "").strip()
    slug = (fm.get("slug") or "").strip() or slugify(title)
    # Hard guard (2026-09-24): a blank title or empty slug once shipped a ghost
    # entry (slug="", title="", image="images/.jpg") to the live blog listing.
    # Refuse to build instead of publishing garbage.
    if not title or title.lower() == "untitled":
        raise ValueError(f"refusing to build {draft_path}: blank/untitled title")
    if not slug:
        raise ValueError(f"refusing to build {draft_path}: empty slug")
    post_date = fm.get("date", date.today().isoformat())
    # David's rule 2026-09-23: every post shows its publish timestamp.
    # Stamped at build (= publish) time; frontmatter may override for backfills.
    published_at = fm.get("published_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pub_display = format_pub_display(published_at, post_date)
    # Scribe drafts sometimes wrap tags in stray quotes ("sap-business-one").
    # Strip them at build so they never reach the page or JSON-LD (2026-09-24).
    tags = [t.strip().strip("\"'") for t in fm.get("tags", "").split(",")]
    tags = [t for t in tags if t]
    excerpt = fm.get("excerpt", body[:160].replace("\n", " ") + "...")
    description = fm.get("description", excerpt)
    keywords = fm.get("keywords", "")
    meta_keywords = (f'<meta name="keywords" content="{keywords}" />' if keywords else "")

    # Normalize image args: accept a single string (legacy) or a list.
    if isinstance(image_srcs, str):
        image_srcs = [image_srcs]
    if isinstance(image_alts, str):
        image_alts = [image_alts]
    image_srcs = image_srcs or []
    image_alts = image_alts or []
    image_src = image_srcs[0] if image_srcs else None
    image_alt = image_alts[0] if image_alts else None

    hero, og_image, image_rel, video_rel = "", "", None, None
    img_dims = None  # (w, h) of the published hero JPEG — reused for og tags + hero attrs
    img_file = image_src or fm.get("image")
    if img_file and os.path.exists(img_file):
        os.makedirs(IMAGES_DIR, exist_ok=True)
        dest = os.path.join(IMAGES_DIR, f"{slug}.jpg")
        # Never copy a file onto itself — open(dest,'wb') truncates before read
        if os.path.abspath(img_file) == os.path.abspath(dest):
            image_rel = f"images/{slug}.jpg"
        else:
            with open(img_file, "rb") as a, open(dest, "wb") as b:
                b.write(a.read())
            image_rel = f"images/{slug}.jpg"
        if image_rel:
            og_image = f'<meta property="og:image" content="https://deadbrands.co/blog/images/{slug}.jpg" />'
            try:
                from PIL import Image
                with Image.open(os.path.join(IMAGES_DIR, f"{slug}.jpg")) as im:
                    img_dims = im.size
                og_image += (f'\n  <meta property="og:image:width" content="{img_dims[0]}" />'
                             f'\n  <meta property="og:image:height" content="{img_dims[1]}" />')
            except Exception:
                pass
    vid_file = video_src or fm.get("video")
    if vid_file and os.path.exists(vid_file):
        os.makedirs(VIDEOS_DIR, exist_ok=True)
        vdest = os.path.join(VIDEOS_DIR, f"{slug}.mp4")
        with open(vid_file, "rb") as a, open(vdest, "wb") as b:
            b.write(a.read())
        video_rel = f"../videos/{slug}.mp4"

    if video_rel:
        poster = f' poster="../{image_rel}"' if image_rel else ""
        hero = (f'<figure class="post-hero-card"><video controls preload="metadata"{poster} '
                f'src="{video_rel}"><source src="{video_rel}" type="video/mp4"></video>'
                f'<div class="hero-title-overlay"><h1>{html_escape(title)}</h1>'
                f'<p class="post-meta">{pub_display} &middot; by <a href="../author.html">David Strausser</a></p></div></figure>')
    elif image_rel:
        # Hero alt priority (David 2026-09-26: descriptive alt on every post
        # image): frontmatter image_alt > --image-alt arg (scribe image brief)
        # > description > title. Never empty.
        alt_raw = ((fm.get("image_alt") or "").strip()
                   or (image_alt or "").strip()
                   or description.strip()
                   or title)
        alt_raw = re.sub(r"\s+", " ", alt_raw)[:160]
        alt = html_escape_attr(alt_raw)
        # Real pixel dims kill layout shift; lazy keeps it off the critical path.
        size_attrs = ""
        if img_dims:
            size_attrs = f' width="{img_dims[0]}" height="{img_dims[1]}"'
        hero = (f'<figure class="post-hero-card"><img src="../{image_rel}" alt="{alt}"'
                f'{size_attrs} loading="eager" fetchpriority="high" />'
                f'<div class="hero-title-overlay"><h1>{html_escape(title)}</h1>'
                f'<p class="post-meta">{pub_display} &middot; by <a href="../author.html">David Strausser</a></p></div></figure>')
    else:
        # No hero image (should not happen — imageless posts are never
        # published): title block without the card.
        hero = (f'<div class="hero-title-plain"><h1>{html_escape(title)}</h1>'
                f'<p class="post-meta">{pub_display} &middot; by <a href="../author.html">David Strausser</a></p></div>')

    # Inline images (David 2026-09-26): image_srcs[1:4] are copied as
    # images/<slug>-img2.jpg … -img4.jpg and inserted as <figure> elements
    # into the body at ~1/4, ~1/2, ~3/4 (hero + 2-3 blog images).
    inline_images = []
    for idx, src in enumerate(image_srcs[1:4], start=2):
        if not (src and os.path.exists(src)):
            continue
        dest = os.path.join(IMAGES_DIR, f"{slug}-img{idx}.jpg")
        if os.path.abspath(src) != os.path.abspath(dest):
            os.makedirs(IMAGES_DIR, exist_ok=True)
            with open(src, "rb") as a, open(dest, "wb") as b:
                b.write(a.read())
        dims = None
        try:
            from PIL import Image
            with Image.open(dest) as im:
                dims = im.size
        except Exception:
            pass
        alt_src = (image_alts[idx - 1] if len(image_alts) > idx - 1 else "") or description or title
        inline_images.append((f"images/{slug}-img{idx}.jpg", alt_src, dims))

    faqs = extract_faq(body)
    # Executive Summary box carries the Quick Answer (David 2026-09-26):
    # pull it out of the body so it never renders twice.
    body, qa_md = extract_quick_answer(body)
    body_html = insert_inline_images(md_to_html(body, slug), inline_images)
    if qa_md:
        summary_inner = quick_answer_html(qa_md, slug)
    else:  # fallback: frontmatter summary > excerpt
        summary_fallback = (fm.get("summary") or "").strip() or excerpt
        summary_inner = f"<p>{html_escape(summary_fallback)}</p>" if summary_fallback.strip() else ""
    html = PAGE_TEMPLATE.format(
        title=title, slug=slug, date=post_date, pub_display=pub_display,
        description=description,
        meta_keywords=meta_keywords, hero=hero, og_image=og_image,
        twitter_image=(f'<meta name="twitter:image" content="https://deadbrands.co/blog/images/{slug}.jpg" />'
                       if image_rel else ""),
        summary=summary_html(summary_inner),
        body=body_html, faq_jsonld=faq_jsonld(faqs, slug),
        article_jsonld=article_jsonld(title, description, slug, published_at, image_rel, tags),
        tags=" ".join(f"<span>{t}</span>" for t in tags),
        cta=cta_html(slug, cta_name, cta_custom), author_box=author_box_html(), cta_css=CTA_CSS,
        shop_block=shop_block_html(), shop_css=SHOP_CSS,
    )
    # Resolve shared-nav active tokens: generated posts are always blog pages.
    html = re.sub(r"%%A_blog%%", "active", html)
    html = re.sub(r"%%A_[a-z_]+%%", "", html)
    os.makedirs(POSTS_DIR, exist_ok=True)
    out_path = os.path.join(POSTS_DIR, f"{slug}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    entry = {"slug": slug, "title": title, "date": post_date,
             "published_at": published_at,
             "tags": tags, "excerpt": excerpt, "description": description,
             "image": image_rel or "", "video": video_rel or "",
             "url": f"posts/{slug}.html"}
    posts = []
    if os.path.exists(INDEX_JSON):
        with open(INDEX_JSON, encoding="utf-8") as f:
            posts = json.load(f)
    posts = [p for p in posts if p["slug"] != slug] + [entry]
    # Newest first — (date, published_at) so same-day posts order by
    # actual publish time (David's rule 2026-09-23).
    posts.sort(key=lambda p: (p.get("date", ""), p.get("published_at", "")), reverse=True)
    with open(INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)
    print(f"built {out_path} (faqs={len(faqs)}, video={'yes' if video_rel else 'no'})")
    return slug

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: build_post.py <draft.md> [--image <file.jpg>]... [--video <file.mp4>] [--image-alt <text>]... [--cta <template-name>] [--cta-custom <heading>|<body>|<button>|<url>]"); sys.exit(1)
    argv = sys.argv[2:]
    imgs = [argv[j + 1] for j in range(len(argv) - 1) if argv[j] == "--image" and j + 1 < len(argv)]
    alts = [argv[j + 1] for j in range(len(argv) - 1) if argv[j] == "--image-alt" and j + 1 < len(argv)]
    vid = argv[argv.index("--video") + 1] if "--video" in argv else None
    cta_name = argv[argv.index("--cta") + 1] if "--cta" in argv and argv.index("--cta") + 1 < len(argv) else None
    cta_custom = None
    if "--cta-custom" in argv and argv.index("--cta-custom") + 1 < len(argv):
        parts = argv[argv.index("--cta-custom") + 1].split("|")
        if len(parts) == 4:
            cta_custom = {"heading": parts[0], "body": parts[1], "button": parts[2], "url": parts[3]}
    build(sys.argv[1], imgs or None, vid, alts or None, cta_name, cta_custom)
