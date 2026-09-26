# Image Audit Report — deadbrands.co

**Date:** 2026-09-26
**Scope:** all 73 HTML pages + all stylesheets in `~/workspace/sites/dstrausser83.github.io`
**Method:** automated extraction of every `<img>` src/srcset, `og:image` / `twitter:image` meta,
`<video>` poster, inline-style and stylesheet `background-image`; local files verified on disk
(dimensions + readability via PIL); remote URLs checked with curl (HEAD, ranged-GET fallback);
alt text, `.post-hero-card` / `.post-inline` patterns, and `og:image:width/height` accuracy checked per post.
Audit re-run after review — results below are final. **Nothing was deployed; all changes (none) are local.**

## Verdict: clean — no broken images

| Check | Result |
|---|---|
| Pages scanned | 73 |
| Image references extracted | 424 (313 `<img>`, 95 meta, 16 post pattern-checks) |
| Missing local files | **0** |
| Broken remote images | **0** (site is 100% self-hosted, zero hotlinks) |
| Corrupt/unreadable files | **0** |
| Content images missing `alt` | **0** |
| Blog posts missing hero card | **0 of 16** |
| Inline images violating `.post-inline` 620px cap | **0** |
| `og:image` / `twitter:image` mismatches | **0** (hero = og = twitter on all 16 posts) |
| Stale `og:image:width/height` | **0 of 16** (all accurate) |
| feed.xml enclosures resolving | **16 of 16** |

## Fixes applied

**None — nothing was broken.** Every `src` resolves, every `alt` is present, every hero/inline
pattern matches the `build_post.py` template. The 18 initial "missing file" hits were false
positives: `<img>` tags inside `<script>` blocks (client-side "related posts" JS templates using
`${p.image}` / `esc(p.image)` expressions, not literal URLs). The audit was refined to strip
script blocks and re-run clean.

One non-issue noted: `tools/canonical-header.html` references `assets/img/dead-brands-logo.png`
with a relative path — intentional, it is a partial injected into root-level pages by
`tools/enforce-base-template.py`.

## Unfixable / genuinely missing images

**None.** No image was found broken without a recoverable source.

## Optimization flags (not broken, but wasteful)

These are recommendations for a future image-resize pass — **not applied**, because changing hero
dimensions would invalidate the baked-in `og:image:width/height` metas, and quality calls are
David's.

1. **72 unique files wider than 1200px (~25 MB total).** Display caps are far smaller
   (`.post-inline` max 620px, hero cards ~1000px). Biggest offenders:
   - `blog/images/*-img2.jpg` / `*-img3.jpg` at 1920–2048px wide (300–880KB each)
   - `assets/img/merch/sharkbite-*.webp` at 1920px (250–300KB each)
   - `assets/img/services/*` at 1440–2048px (100–434KB each)
   - `assets/photos/published/*` at 1440–1600px (150–259KB each)
   - `assets/img/fiverr-ai-chatbot-cover.jpg` at 2736×912 (420KB)
   - `assets/img/case-studies/*.jpg` at 2048×1152 (~500KB each)
   - Suggested: heroes → max 1600w, inline → max 1240w (2× the 620px cap), then regenerate the
     `og:image:width/height` metas via `build_post.py`.
2. **`assets/img/dead-brands-logo.png` is 893KB (823×751)** yet renders at 40×40 in the header
   on every page (68 references) and 120×120 twice. Lossless re-compression saves 0% (already
   optimal) — the file is just detailed. Recommendation: ship a small header variant
   (e.g. 160px) and keep the full file only where large rendering matters. Note it also serves
   as `og:image` on ~10 service pages, where its near-square aspect is suboptimal for social
   cards (1200×630 preferred) — a dedicated og image per service page would share better.
3. **Two blog inline JPGs exceed 800KB** (`customization-…-img2.jpg` 880KB,
   `welcome-to-the-blog-…-img2.jpg` 812KB) — candidates for quality-85 re-encode.

## Files touched

No site files were modified. Report only.
