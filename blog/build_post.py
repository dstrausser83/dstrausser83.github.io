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
from datetime import date

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
    """Markdown -> HTML. Wraps '## Quick answer' in a styled callout div."""
    out, in_list, list_tag = [], False, ""
    in_quick = False
    def close_quick():
        nonlocal in_quick
        if in_quick:
            out.append("</div>")
            in_quick = False
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("### "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<h3>{md_inline(s[4:], slug)}</h3>")
        elif s.startswith("## "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            close_quick()
            out.append(f"<h2>{md_inline(s[3:], slug)}</h2>")
            if s[3:].strip().lower() == "quick answer":
                out.append('<div class="quick-answer">')
                in_quick = True
        elif s.startswith("# "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            close_quick()
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
            close_quick()
            out.append("<hr />")
        else:
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<p>{md_inline(s, slug)}</p>")
    if in_list: out.append(f"</{list_tag}>")
    close_quick()
    return "\n".join(out)

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

def faq_jsonld(faqs):
    if not faqs:
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
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
            "url": "https://dstrausser83.github.io/",
            "jobTitle": "CEO of Dead Brands, LLC; Head of Sales for Quaint Business Solutions (SAP Business One & Odoo)",
        },
        "publisher": {
            "@type": "Organization",
            "name": "Dead Brands, LLC",
        },
        "mainEntityOfPage": f"https://dstrausser83.github.io/blog/posts/{slug}.html",
        "keywords": ", ".join(tags),
    }
    if image_rel:
        data["image"] = f"https://dstrausser83.github.io/blog/{image_rel}"
    return '<script type="application/ld+json">\n' + json.dumps(data, indent=2) + "\n</script>"

MEET_LINK = "https://app.apollo.io/#/meet/david_strausser_175"
TRIAL_LINK = ("https://quaintbusiness.com/tryodoo?utm_source=deadbrands"
              "&utm_medium=website&utm_campaign=david-strausser"
              "&utm_content=blog-cta-trial")
AUTHOR_URL = "../author.html"
HEADSHOT = "../../assets/photos/published/david-headshot-blazer.jpg"


def cta_html(slug):
    """Alternating end-of-post CTA (David's rule 2026-09-23): even hash ->
    book-a-meeting, odd hash -> free Odoo trial. Stable per slug."""
    if int(hashlib.md5(slug.encode()).hexdigest(), 16) % 2 == 0:
        return f"""<section class="post-cta">
          <h2>Let's talk about your business</h2>
          <p>Running on spreadsheets, QuickBooks, or an ERP that fights you?
          Grab a free 30-minute call — I'll tell you straight whether
          SAP Business One or Odoo is the right move, and what it really costs.</p>
          <a class="cta-btn" href="{MEET_LINK}" target="_blank" rel="noopener">Book a Meeting with Me</a>
        </section>"""
    return f"""<section class="post-cta">
          <h2>Try Odoo free</h2>
          <p>See why so many small businesses are ditching a dozen disconnected
          apps for one platform. Spin up Odoo and kick the tires yourself —
          no credit card, no sales call required.</p>
          <a class="cta-btn" href="{TRIAL_LINK}" target="_blank" rel="noopener">Start Your Free Odoo Trial</a>
        </section>"""


def author_box_html():
    return f"""<section class="author-box">
          <img src="{HEADSHOT}" alt="David Strausser" width="96" height="96" />
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
  <link rel="canonical" href="https://dstrausser83.github.io/blog/posts/{slug}.html" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  {og_image}
  <link rel="icon" href="../../assets/img/favicon.png" type="image/png" />
  <link rel="apple-touch-icon" href="../../assets/img/apple-touch-icon.png" />
  <link rel="stylesheet" href="../../assets/css/styles.css" />
  <style>
    .post-hero img {{ width: 100%; border-radius: var(--radius); border: 1.5px solid var(--line); }}
    .post-hero video {{ width: 100%; border-radius: var(--radius); border: 1.5px solid var(--line); margin-bottom: 1rem; }}
    .post-meta {{ color: var(--muted); font-size: 0.95rem; margin: 0.5rem 0 1.5rem; }}
    .post-tags span {{ display: inline-block; background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: 0.2rem 0.8rem; font-size: 0.85rem; margin-right: 0.4rem; }}
    .post-body h2 {{ margin-top: 2rem; }} .post-body h3 {{ margin-top: 1.5rem; }}
    .post-body blockquote {{ border-left: 3px solid var(--accent); margin: 1.5rem 0; padding: 0.5rem 1rem; color: var(--muted); font-style: italic; }}
    .quick-answer {{ background: var(--card); border: 1.5px solid var(--accent); border-radius: var(--radius); padding: 1rem 1.25rem; margin: 1rem 0 1.5rem; }}
    .quick-answer p {{ margin: 0.4rem 0; }}
    .back-link {{ display: inline-block; margin-bottom: 1.5rem; }}
{cta_css}
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
        <a href="../../index.html#about">About</a>
        <a href="../../index.html#career">Career</a>
        <a href="../../index.html#work">Work</a>
        <a href="../../index.html#testimonials">Testimonials</a>
        <a href="https://open.spotify.com/show/1CZh0QdNr5Nn8CD8kInMAJ" target="_blank" rel="noopener">Podcast</a>
        <a href="../index.html" class="active">Blog</a>
        <a href="../../index.html#life">Life</a>
        <a href="../../index.html#shop">Shop</a>
        <a href="../../index.html#contact" class="nav-cta">Work With Me</a>
      </nav>
    </div>
  </header>
  <main>
    <article class="section">
      <div class="wrap narrow">
        <a class="back-link" href="../index.html">&larr; All posts</a>
        <h1>{title}</h1>
        <p class="post-meta">{date} &middot; by <a href="../author.html">David Strausser</a></p>
        {hero}
        <div class="post-body prose">
{body}
        </div>
        <p class="post-tags">{tags}</p>
        {cta}
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

def build(draft_path, image_src=None, video_src=None):
    with open(draft_path, encoding="utf-8") as f:
        text = f.read()
    # Scribe drafts can carry a UTF-8 BOM which breaks frontmatter
    # detection and produces "Untitled" posts — strip it (2026-09-23).
    text = text.lstrip("\ufeff")
    fm, body = parse_frontmatter(text)
    title = fm.get("title", "Untitled")
    slug = fm.get("slug", slugify(title))
    post_date = fm.get("date", date.today().isoformat())
    tags = [t.strip() for t in fm.get("tags", "").split(",") if t.strip()]
    excerpt = fm.get("excerpt", body[:160].replace("\n", " ") + "...")
    description = fm.get("description", excerpt)
    keywords = fm.get("keywords", "")
    meta_keywords = (f'<meta name="keywords" content="{keywords}" />' if keywords else "")

    hero, og_image, image_rel, video_rel = "", "", None, None
    img_file = image_src or fm.get("image")
    if img_file and os.path.exists(img_file):
        os.makedirs(IMAGES_DIR, exist_ok=True)
        dest = os.path.join(IMAGES_DIR, f"{slug}.jpg")
        # Never copy a file onto itself — open(dest,'wb') truncates before read
        if os.path.abspath(img_file) == os.path.abspath(dest):
            image_rel = f"images/{slug}.jpg"
            og_image = f'<meta property="og:image" content="https://dstrausser83.github.io/blog/images/{slug}.jpg" />'
        else:
            with open(img_file, "rb") as a, open(dest, "wb") as b:
                b.write(a.read())
            image_rel = f"images/{slug}.jpg"
            og_image = f'<meta property="og:image" content="https://dstrausser83.github.io/blog/images/{slug}.jpg" />'
    vid_file = video_src or fm.get("video")
    if vid_file and os.path.exists(vid_file):
        os.makedirs(VIDEOS_DIR, exist_ok=True)
        vdest = os.path.join(VIDEOS_DIR, f"{slug}.mp4")
        with open(vid_file, "rb") as a, open(vdest, "wb") as b:
            b.write(a.read())
        video_rel = f"../videos/{slug}.mp4"

    if video_rel:
        poster = f' poster="../{image_rel}"' if image_rel else ""
        hero = (f'<figure class="post-hero"><video controls preload="metadata"{poster} '
                f'src="{video_rel}"><source src="{video_rel}" type="video/mp4"></video></figure>')
    elif image_rel:
        hero = f'<figure class="post-hero"><img src="../{image_rel}" alt="{title}" /></figure>'

    faqs = extract_faq(body)
    html = PAGE_TEMPLATE.format(
        title=title, slug=slug, date=post_date, description=description,
        meta_keywords=meta_keywords, hero=hero, og_image=og_image,
        body=md_to_html(body, slug), faq_jsonld=faq_jsonld(faqs),
        article_jsonld=article_jsonld(title, description, slug, post_date, image_rel, tags),
        tags=" ".join(f"<span>{t}</span>" for t in tags),
        cta=cta_html(slug), author_box=author_box_html(), cta_css=CTA_CSS,
    )
    os.makedirs(POSTS_DIR, exist_ok=True)
    out_path = os.path.join(POSTS_DIR, f"{slug}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    entry = {"slug": slug, "title": title, "date": post_date,
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
        print("usage: build_post.py <draft.md> [--image <file.jpg>] [--video <file.mp4>]"); sys.exit(1)
    img = sys.argv[sys.argv.index("--image") + 1] if "--image" in sys.argv else None
    vid = sys.argv[sys.argv.index("--video") + 1] if "--video" in sys.argv else None
    build(sys.argv[1], img, vid)
