#!/usr/bin/env python3
"""Build a blog post page from a markdown draft with frontmatter.

Usage: build_post.py <draft.md> [--image <file.jpg>]
Reads frontmatter (title, date, tags, excerpt), converts markdown body to HTML,
writes blog/posts/<slug>.html, and updates blog/posts.json.
"""
import json, re, sys, os
from datetime import date

BLOG_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BLOG_DIR, "posts")
IMAGES_DIR = os.path.join(BLOG_DIR, "images")
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
    out, in_list, list_tag = [], False, ""
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("### "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<h3>{md_inline(s[4:])}</h3>")
        elif s.startswith("## "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<h2>{md_inline(s[3:])}</h2>")
        elif s.startswith("# "):
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<h2>{md_inline(s[2:])}</h2>")
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
        else:
            if in_list: out.append(f"</{list_tag}>"); in_list = False
            out.append(f"<p>{md_inline(s)}</p>")
    if in_list: out.append(f"</{list_tag}>")
    return "\n".join(out)

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} — David Strausser</title>
  <meta name="description" content="{excerpt}" />
  <link rel="canonical" href="https://dstrausser83.github.io/blog/posts/{slug}.html" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{excerpt}" />
  {og_image}
  <link rel="stylesheet" href="../../assets/css/styles.css" />
  <style>
    .post-hero img {{ width: 100%; border-radius: var(--radius); border: 1.5px solid var(--line); }}
    .post-meta {{ color: var(--muted); font-size: 0.95rem; margin: 0.5rem 0 1.5rem; }}
    .post-tags span {{ display: inline-block; background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: 0.2rem 0.8rem; font-size: 0.85rem; margin-right: 0.4rem; }}
    .post-body h2 {{ margin-top: 2rem; }} .post-body h3 {{ margin-top: 1.5rem; }}
    .post-body blockquote {{ border-left: 3px solid var(--accent); margin: 1.5rem 0; padding: 0.5rem 1rem; color: var(--muted); font-style: italic; }}
    .back-link {{ display: inline-block; margin-bottom: 1.5rem; }}
  </style>
</head>
<body>
  <header class="site-header">
    <nav class="wrap nav">
      <a class="brand" href="../../index.html">David Strausser</a>
      <div class="nav-links">
        <a href="../../index.html#about">About</a>
        <a href="../../index.html#work">Work</a>
        <a href="../index.html">Blog</a>
        <a href="../../index.html#contact">Contact</a>
      </div>
    </nav>
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
</body>
</html>
"""

def build(draft_path, image_src=None):
    with open(draft_path, encoding="utf-8") as f:
        text = f.read()
    fm, body = parse_frontmatter(text)
    title = fm.get("title", "Untitled")
    slug = fm.get("slug", slugify(title))
    post_date = fm.get("date", date.today().isoformat())
    tags = [t.strip() for t in fm.get("tags", "").split(",") if t.strip()]
    excerpt = fm.get("excerpt", body[:160].replace("\n", " ") + "...")

    hero, og_image, image_rel = "", "", None
    img_file = image_src or fm.get("image")
    if img_file and os.path.exists(img_file):
        os.makedirs(IMAGES_DIR, exist_ok=True)
        dest = os.path.join(IMAGES_DIR, f"{slug}.jpg")
        with open(img_file, "rb") as a, open(dest, "wb") as b:
            b.write(a.read())
        image_rel = f"../images/{slug}.jpg"
        hero = f'<figure class="post-hero"><img src="{image_rel}" alt="{title}" /></figure>'
        og_image = f'<meta property="og:image" content="https://dstrausser83.github.io/blog/images/{slug}.jpg" />'

    html = PAGE_TEMPLATE.format(
        title=title, slug=slug, date=post_date, excerpt=excerpt,
        hero=hero, og_image=og_image, body=md_to_html(body),
        tags=" ".join(f"<span>{t}</span>" for t in tags),
    )
    os.makedirs(POSTS_DIR, exist_ok=True)
    out_path = os.path.join(POSTS_DIR, f"{slug}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    entry = {"slug": slug, "title": title, "date": post_date,
             "tags": tags, "excerpt": excerpt,
             "image": image_rel or "", "url": f"posts/{slug}.html"}
    posts = []
    if os.path.exists(INDEX_JSON):
        with open(INDEX_JSON, encoding="utf-8") as f:
            posts = json.load(f)
    posts = [p for p in posts if p["slug"] != slug] + [entry]
    posts.sort(key=lambda p: p["date"], reverse=True)
    with open(INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)
    print(f"built {out_path}")
    return slug

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: build_post.py <draft.md> [--image <file.jpg>]"); sys.exit(1)
    img = None
    if "--image" in sys.argv:
        img = sys.argv[sys.argv.index("--image") + 1]
    build(sys.argv[1], img)
