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
import json, re, sys, os
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

def md_inline(t):
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    return t

def md_to_html(body):
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
            out.append(f"<h3>{md_inline(s[4:])}</h3>")
        elif s.startswith("## "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            close_quick()
            out.append(f"<h2>{md_inline(s[3:])}</h2>")
            if s[3:].strip().lower() == "quick answer":
                out.append('<div class="quick-answer">')
                in_quick = True
        elif s.startswith("# "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            close_quick()
            out.append(f"<h1>{md_inline(s[2:])}</h1>")
        elif s.startswith("> "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<blockquote>{md_inline(s[2:])}</blockquote>")
        elif re.match(r"^[-*] ", s):
            if not in_list: out.append("<ul>"); in_list, list_tag = True, "ul"
            out.append(f"<li>{md_inline(s[2:])}</li>")
        elif re.match(r"^\d+\. ", s):
            if not in_list or list_tag != "ol":
                if in_list: out.append(f"</{list_tag}>")
                out.append("<ol>"); in_list, list_tag = True, "ol"
            out.append(f"<li>{md_inline(re.sub(r'^\d+\. ', '', s))}</li>")
        elif s == "":
            if in_list: out.append(f"</{list_tag}>"); in_list = False
        elif s == "---":
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            close_quick()
            out.append("<hr />")
        else:
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<p>{md_inline(s)}</p>")
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

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
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
  </style>
  {faq_jsonld}
</head>
<body>
  <header class="site-header" id="site-header">
    <div class="wrap header-inner">
      <a class="brand" href="../../index.html" aria-label="David Strausser — home">
        <img class="brand-photo" src="../../assets/photos/published/david-headshot-blazer.jpg" alt="David Strausser" width="76" height="76" />
        <span class="brand-name">David Strausser</span>
      </a>
      <button class="nav-toggle" id="nav-toggle" aria-expanded="false" aria-controls="site-nav" aria-label="Open menu">
        <span></span><span></span><span></span>
      </button>
      <nav class="site-nav" id="site-nav" aria-label="Primary">
        <a href="../../index.html#about">About</a>
        <a href="../../index.html#work">Work</a>
        <a href="../index.html" class="active">Blog</a>
        <a href="../../index.html#contact" class="nav-cta">Work With Me</a>
      </nav>
    </div>
  </header>
  <main>
    <article class="section">
      <div class="wrap narrow">
        <a class="back-link" href="../index.html">&larr; All posts</a>
        <h1>{title}</h1>
        <p class="post-meta">{date} &middot; by David Strausser</p>
        {hero}
        <div class="post-body prose">
{body}
        </div>
        <p class="post-tags">{tags}</p>
      </div>
    </article>
  </main>
  <footer class="site-footer">
    <div class="wrap">
      <p>&copy; <span id="year">2026</span> Dead Brands, LLC. All rights reserved.</p>
    </div>
  </footer>
  <script>document.getElementById('year').textContent = new Date().getFullYear();</script>
  <script src="../../assets/js/main.js" defer></script>
</body>
</html>
"""

def build(draft_path, image_src=None, video_src=None):
    with open(draft_path, encoding="utf-8") as f:
        text = f.read()
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
        body=md_to_html(body), faq_jsonld=faq_jsonld(faqs),
        tags=" ".join(f"<span>{t}</span>" for t in tags),
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
    posts.sort(key=lambda p: p["date"], reverse=True)
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
