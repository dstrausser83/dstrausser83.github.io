#!/usr/bin/env python3
"""
CMS breakpoint overrides engine (lane A5 - Mobile Previewer/Editor, 2026-09-30).

Additive module. Merges per-breakpoint content overrides into published HTML
WITHOUT touching lane B's templates/CSS/JS files.

Content schema (additive - content/<page>.json, desktop shape unchanged):
    "overrides": {
        "mobile": {
            "<section_id>": {
                "hidden": false,                          # hide section at this breakpoint
                "fields": { "<field_name>": "<value>" },  # text swaps (hero fields + generic)
                "image":  { "src": "...", "alt": "..." }, # image swap (hero <img>)
                "spacing": { "padding_top": "24px", "padding_bottom": "24px" },
                "order": 2                               # 1-based order at this breakpoint
            }
        },
        "tablet": { ...same shape... }
    }

Cascade rule: mobile/tablet inherit desktop unless explicitly overridden.
Pages without "overrides" build byte-identical to before.

Publish technique (CSS-only, no JS, no layout shift on desktop):
- Text swaps emit one copy per breakpoint, each keeping its natural display:
      <span class="bp-d bp-hide-m">desktop</span><span class="bp-m bp-hide-t bp-hide-d">mobile</span>
  Media queries hide only the non-matching copies, so desktop rendering is untouched.
- Image swaps duplicate the <img> per breakpoint (same copy technique as text),
  so each breakpoint gets its own src AND alt. CSS-only, no JS.
- Section hide adds bp-hide-m / bp-hide-t to the <section> tag.
- Spacing/order emit per-section rules inside the breakpoint media query.
- A single <style> block is injected before </head>, ONLY when overrides exist.
- All transforms are idempotent: rebuilding an already-built page is a no-op.
"""

import re

# Breakpoint -> media query. Phone <768px, tablet 768-1024px, desktop >=1025px.
BREAKPOINTS = {
    "mobile": "(max-width: 767px)",
    "tablet": "(min-width: 768px) and (max-width: 1024px)",
}

_BP_SHORT = {"mobile": "m", "tablet": "t"}

# Static utility CSS. Only display:none rules inside media queries - nothing
# here can affect desktop rendering except hiding breakpoint-specific copies.
_BASE_CSS = """/* CMS breakpoint overrides - auto-generated, additive (lane A5). CSS-only, no JS. */
@media (max-width: 767px) {
  .bp-hide-m { display: none !important; }
}
@media (min-width: 768px) and (max-width: 1024px) {
  .bp-hide-t { display: none !important; }
}
@media (min-width: 1025px) {
  .bp-hide-d { display: none !important; }
}"""

# Hero text fields -> (open-tag pattern, close tag). build_hero_section writes
# these exact shapes, so the engine finds desktop values reliably.
_HERO_TEXT_FIELDS = {
    "eyebrow": (r'<p class="eyebrow reveal">', "</p>"),
    "heading": (r'<h1 class="reveal">', "</h1>"),
    "tagline": (r'<p class="tagline reveal">', "</p>"),
    "hero_sub": (r'<p class="hero-sub reveal">', "</p>"),
    "hero_caption": (r"<figcaption>", "</figcaption>"),
}

# CTA buttons: class fragment -> (text field, url field)
_CTA_BUTTONS = {
    "btn btn-primary": ("cta_primary_text", "cta_primary_url"),
    "btn btn-ghost": ("cta_secondary_text", "cta_secondary_url"),
}

# Fields never handled by the generic verbatim text swap: CTA label+URL pairs are
# owned by _apply_cta (per-breakpoint anchor duplication), images by _apply_image.
_SKIP_FIELDS = {"cta_primary_text", "cta_primary_url",
                "cta_secondary_text", "cta_secondary_url",
                "hero_image_src", "hero_image_alt"}


# ============================================================================
# Small helpers
# ============================================================================

def _hide_classes(except_bp):
    """Hide classes for a copy that should show ONLY at except_bp (None = desktop)."""
    if except_bp is None:
        return ""
    shorts = {"mobile": "m", "tablet": "t"}
    others = [s for b, s in shorts.items()] + ["d"]
    mine = shorts[except_bp]
    return " ".join("bp-hide-" + s for s in others if s != mine)


def _desktop_hide_classes(bps):
    """Hide classes for the desktop copy when these breakpoints override it."""
    return " ".join("bp-hide-" + _BP_SHORT[b] for b in bps)


def _add_class(open_tag, cls):
    """Add CSS class(es) to an open tag. Idempotent."""
    if not cls:
        return open_tag
    for c in cls.split():
        if re.search(r'class="[^"]*\b' + re.escape(c) + r'\b', open_tag):
            cls = cls.replace(c, "").strip()
    if not cls:
        return open_tag
    if 'class="' in open_tag:
        return re.sub(r'class="([^"]*)"',
                      lambda m: 'class="%s %s"' % (m.group(1), cls),
                      open_tag, count=1)
    return open_tag[:-1] + ' class="%s">' % cls


def _is_disabled(html, pos):
    """True if pos sits inside a <!-- CMS-DISABLED ... --> comment."""
    head = html[:pos]
    last_open = head.rfind("<!--")
    last_close = head.rfind("-->")
    return last_open > last_close and "CMS-DISABLED" in html[last_open:pos]


def _already_swapped(inner, pos):
    """Rebuild guard: is pos already inside/at a bp copy-group?"""
    # Forward: a bp copy opens exactly at pos (hero field re-entry).
    if inner[pos:pos + 64].lstrip().startswith('<span class="bp-'):
        return True
    # Backward: pos sits right inside an already-opened bp copy span.
    head = inner[:pos]
    last_span = head.rfind("<span")
    last_close = head.rfind("</span>")
    if last_span > last_close:
        tag = inner[last_span:inner.find(">", last_span) + 1]
        if 'class="bp-' in tag:
            return True
    return False


def _section_span(html, section_id):
    """Return (open_tag, inner, close_tag, start, end) for a live section, or None."""
    pattern = re.compile(
        r'(<section\b[^>]*\bid="%s"[^>]*>)(.*?)(</section>)' % re.escape(section_id),
        re.DOTALL)
    for m in pattern.finditer(html):
        if not _is_disabled(html, m.start()):
            return m.group(1), m.group(2), m.group(3), m.start(), m.end()
    return None


# ============================================================================
# Per-section transforms
# ============================================================================

def _swap_field_copies(desktop_val, bp_vals):
    """Wrap desktop + breakpoint copies. bp_vals: {bp: value}."""
    bps = [b for b in ("mobile", "tablet") if b in bp_vals]
    parts = ['<span class="bp-d%s">%s</span>'
             % (" " + _desktop_hide_classes(bps) if bps else "", desktop_val)]
    for b in bps:
        parts.append('<span class="bp-%s %s">%s</span>'
                     % (_BP_SHORT[b], _hide_classes(b), bp_vals[b]))
    return "".join(parts)


def _apply_hero_text(hero_open, hero_inner, hero_close, fields, bp_fields, warnings, sec_id):
    """Text swaps inside the hero section. Returns new inner html."""
    # Collect per-field breakpoint values: {field: {bp: value}}
    wanted = {}
    for bp, bpv in bp_fields.items():
        for fname, val in bpv.items():
            if val:
                wanted.setdefault(fname, {})[bp] = val

    for fname, bpv in wanted.items():
        if fname in _HERO_TEXT_FIELDS:
            open_pat, close_tag = _HERO_TEXT_FIELDS[fname]
            pat = re.compile(r"(%s)(.*?)(%s)" % (open_pat, re.escape(close_tag)), re.DOTALL)
            m = pat.search(hero_inner)
            if not m or _already_swapped(hero_inner, m.start(2)):
                continue
            hero_inner = (hero_inner[:m.start(2)]
                          + _swap_field_copies(m.group(2), bpv)
                          + hero_inner[m.end(2):])
        elif fname not in _SKIP_FIELDS:
            desktop_val = fields.get(fname)
            if not desktop_val:
                continue
            m = re.search(re.escape(desktop_val), hero_inner)
            if not m or _already_swapped(hero_inner, m.start()):
                continue
            hero_inner = (hero_inner[:m.start()]
                          + _swap_field_copies(desktop_val, bpv)
                          + hero_inner[m.end():])
    return hero_inner


def _apply_cta(hero_inner, fields, bp_fields, warnings, sec_id):
    """CTA label/URL overrides: duplicate anchors per breakpoint (CSS-only swap)."""
    for cls, (text_f, url_f) in _CTA_BUTTONS.items():
        bp_text = {bp: bp_fields[bp][text_f] for bp in bp_fields
                   if bp_fields[bp].get(text_f)}
        bp_url = {bp: bp_fields[bp][url_f] for bp in bp_fields
                  if bp_fields[bp].get(url_f)}
        if not bp_text and not bp_url:
            continue
        pat = re.compile(
            r'<a class="%s" href="([^"]*)">(.*?)</a>' % re.escape(cls), re.DOTALL)
        m = pat.search(hero_inner)
        if not m or 'bp-d' in m.group(0)[:60]:
            continue  # already processed (rebuild guard)
        durl, dinner = m.group(1), m.group(2)
        bps = [b for b in ("mobile", "tablet") if b in bp_text or b in bp_url]
        # Desktop copy keeps natural display; hidden where overridden.
        desktop = '<a class="%s bp-d %s" href="%s">%s</a>' % (
            cls, _desktop_hide_classes(bps), durl, dinner)
        copies = [desktop]
        for b in bps:
            label = bp_text.get(b, dinner)
            url = bp_url.get(b, durl)
            copies.append('<a class="%s bp-%s %s" href="%s">%s</a>' % (
                cls, _BP_SHORT[b], _hide_classes(b), url, label))
        hero_inner = hero_inner[:m.start()] + "".join(copies) + hero_inner[m.end():]
    return hero_inner


def _apply_image(hero_inner, bp_images, warnings, sec_id):
    """Image swap via per-breakpoint <img> copies (CSS-only, correct alt text).

    Mirrors the text-swap technique: the desktop <img> keeps natural display
    and is hidden where overridden; each breakpoint gets its own copy with its
    own src + alt. (A <picture>/<source> approach cannot carry per-breakpoint
    alt text, so copies are the honest implementation.)
    """
    bps = [b for b in ("mobile", "tablet") if bp_images.get(b, {}).get("src")]
    if not bps:
        if any(bp_images.get(b) for b in ("mobile", "tablet")):
            warnings.append("%s: image override without src ignored" % sec_id)
        return hero_inner
    pat = re.compile(r"<img\b[^>]*>")
    m = pat.search(hero_inner)
    if not m:
        warnings.append("%s: no <img> found for image swap" % sec_id)
        return hero_inner
    if "bp-d" in m.group(0)[:120]:
        return hero_inner  # already processed (rebuild guard)
    tag = m.group(0)
    desktop = _add_class(tag, "bp-d " + _desktop_hide_classes(bps))
    copies = [desktop]
    for b in bps:
        t = re.sub(r'\ssrc="[^"]*"', ' src="%s"' % bp_images[b]["src"], tag, count=1)
        alt = bp_images[b].get("alt")
        if alt:
            if ' alt="' in t:
                t = re.sub(r'\salt="[^"]*"', ' alt="%s"' % alt, t, count=1)
            else:
                t = t.replace(">", ' alt="%s">' % alt, 1)
        t = _add_class(t, "bp-%s %s" % (_BP_SHORT[b], _hide_classes(b)))
        copies.append(t)
    return hero_inner[:m.start()] + "".join(copies) + hero_inner[m.end():]


def _apply_generic_text(sec_open, sec_inner, sec_close, fields, bp_fields, warnings, sec_id):
    """Generic sections: swap first verbatim occurrence of each overridden field."""
    wanted = {}
    for bp, bpv in bp_fields.items():
        for fname, val in bpv.items():
            if val and fname not in _SKIP_FIELDS:
                wanted.setdefault(fname, {})[bp] = val
    for fname, bpv in wanted.items():
        desktop_val = fields.get(fname)
        if not desktop_val:
            warnings.append("%s: field '%s' has no desktop value; skip" % (sec_id, fname))
            continue
        m = re.search(re.escape(desktop_val), sec_inner)
        if not m:
            warnings.append("%s: desktop text for '%s' not found in markup; skip"
                            % (sec_id, fname))
            continue
        if _already_swapped(sec_inner, m.start()):
            continue  # already wrapped (rebuild guard)
        sec_inner = (sec_inner[:m.start()] + _swap_field_copies(desktop_val, bpv)
                     + sec_inner[m.end():])
    return sec_inner


# ============================================================================
# Public entry points
# ============================================================================

def _strip_breakpoint_markup(html):
    """Remove previously generated breakpoint markup, restoring the merge base.

    Makes apply_breakpoint_overrides idempotent in the strong sense: changing
    an override value, or removing all overrides, then rebuilding, yields the
    same result as building once from a pristine template. No-op on pages
    that never had breakpoint markup.
    """
    # 1. Injected <style> block (marked with the generator comment). Consumes the
    #    leading newline that inject_breakpoint_css adds before <style>.
    html = re.sub(
        r"\n<style>\s*/\* CMS breakpoint overrides.*?\*/.*?</style>",
        "", html, flags=re.DOTALL)

    # 2. Duplicated <img> copies -> single desktop <img>, bp classes removed.
    def _unimg(m):
        tag = re.sub(r"\s*bp-[a-z0-9-]+", "", m.group(1))
        tag = re.sub(r'\s*class="\s*"', "", tag)
        return re.sub(r"\s+", " ", tag).replace(" >", ">")
    html = re.sub(
        r'(<img\b[^>]*\bbp-d\b[^>]*>)(?:<img\b[^>]*\bbp-[mt]\b[^>]*>)+',
        _unimg, html)

    # 2b. Legacy <picture> wrappers (early picture-engine builds) -> bare <img>.
    html = re.sub(
        r"<picture>(?:<source\b[^>]*>)+(<img\b[^>]*>)</picture>",
        r"\1", html)

    # 3. Text span copies -> desktop inner. The desktop copy's closing </span>
    #    is the last one before the first bp-m/bp-t copy (greedy inner).
    def _unspan(m):
        return m.group(1)
    html = re.sub(
        r'<span class="bp-d(?: [^"]*)?">(.*)</span>'
        r'(?:<span class="bp-[mt] [^"]*">.*?</span>)+',
        _unspan, html, flags=re.DOTALL)

    # 4. Duplicated CTA anchors -> single desktop anchor with bp classes removed.
    def _unanchor(m):
        cls = re.sub(r"\s*bp-[a-z0-9-]+", "", m.group(1)).strip()
        cls = re.sub(r"\s+", " ", cls)
        return '<a class="%s"%s>%s</a>' % (cls, m.group(2), m.group(3))
    html = re.sub(
        r'<a class="([^"]*\bbp-d\b[^"]*)"([^>]*)>(.*?)</a>'
        r"(?:<a\b[^>]*\bbp-[mt]\b[^>]*>.*?</a>)+",
        _unanchor, html, flags=re.DOTALL)

    # 5. bp-* class tokens on section/main open tags (hide/spacing/order/reorder).
    def _unclass(m):
        tag = m.group(0)
        tag = re.sub(r"\s*bp-[a-z0-9-]+", "", tag)
        tag = re.sub(r'\s*class="\s*"', "", tag)
        return re.sub(r"\s+", " ", tag).replace(" >", ">")
    html = re.sub(r"<(?:section|main)\b[^>]*>", _unclass, html)

    return html


def apply_breakpoint_overrides(html, content, overrides):
    """Merge overrides into html. Returns (html, css_text, warnings).

    Each section is processed exactly once, with all of its breakpoint
    overrides applied together (cascade: inherit desktop unless overridden).
    """
    warnings = []
    sections = content.get("sections", {})
    css_rules = []
    order_groups = {}   # bp -> [(sec_id, n)]

    # Strip any previously generated breakpoint markup first: rebuilds and
    # override removals must converge to the same result as a pristine build.
    html = _strip_breakpoint_markup(html)

    # --- merge per-section across breakpoints ---
    merged = {}  # sec_id -> {"hidden": set(bp), "fields": {bp: {...}},
                 #            "image": {bp: {...}}, "spacing": {bp: {...}},
                 #            "order": {bp: n}}
    for bp, sec_map in (overrides or {}).items():
        if bp not in BREAKPOINTS:
            warnings.append("unknown breakpoint '%s'; skip" % bp)
            continue
        for sec_id, ov in (sec_map or {}).items():
            if sec_id not in sections:
                warnings.append("%s: unknown section '%s'; skip" % (bp, sec_id))
                continue
            if not sections[sec_id].get("enabled", True):
                warnings.append("%s: section '%s' is disabled; skip" % (bp, sec_id))
                continue
            ov = ov or {}
            m = merged.setdefault(sec_id, {"hidden": set(), "fields": {},
                                           "image": {}, "spacing": {},
                                           "order": {}})
            if ov.get("hidden"):
                m["hidden"].add(bp)
            if ov.get("fields"):
                m["fields"][bp] = {k: v for k, v in ov["fields"].items() if v}
            if ov.get("image"):
                m["image"][bp] = ov["image"]
            if ov.get("spacing"):
                m["spacing"][bp] = ov["spacing"]
            if ov.get("order"):
                try:
                    m["order"][bp] = int(ov["order"])
                except (TypeError, ValueError):
                    warnings.append("%s: bad order value for '%s'; skip" % (bp, sec_id))

    # --- process each section once ---
    for sec_id, m in merged.items():
        found = _section_span(html, sec_id)
        if not found:
            warnings.append("section '%s' not in markup; skip" % sec_id)
            continue
        sec_open, sec_inner, sec_close, sstart, send = found
        fields = sections[sec_id].get("fields", {}) or {}

        if sec_id == "top":
            sec_inner = _apply_cta(sec_inner, fields, m["fields"], warnings, sec_id)
            sec_inner = _apply_hero_text(
                sec_open, sec_inner, sec_close, fields, m["fields"], warnings, sec_id)
            sec_inner = _apply_image(sec_inner, m["image"], warnings, sec_id)
        else:
            if any(m["image"].get(b, {}).get("src") for b in BREAKPOINTS):
                warnings.append("%s: image swap only supported on hero; skip" % sec_id)
            sec_inner = _apply_generic_text(
                sec_open, sec_inner, sec_close, fields, m["fields"], warnings, sec_id)

        # Canonical breakpoint order (mobile, tablet) so output is deterministic
        # across processes (set iteration order varies with hash randomization).
        for bp in [b for b in ("mobile", "tablet") if b in m["hidden"]]:
            sec_open = _add_class(sec_open, "bp-hide-" + _BP_SHORT[bp])

        for bp, spacing in m["spacing"].items():
            short = _BP_SHORT[bp]
            pt, pb = spacing.get("padding_top"), spacing.get("padding_bottom")
            if pt or pb:
                cls = "bp-sp-%s-%s" % (sec_id, short)
                sec_open = _add_class(sec_open, cls)
                decls = []
                if pt:
                    decls.append("padding-top: %s !important;" % pt)
                if pb:
                    decls.append("padding-bottom: %s !important;" % pb)
                css_rules.append((bp, ".%s { %s }" % (cls, " ".join(decls))))

        for bp, n in m["order"].items():
            order_groups.setdefault(bp, []).append((sec_id, n))
            sec_open = _add_class(sec_open, "bp-ord-%s" % sec_id)

        html = html[:sstart] + sec_open + sec_inner + sec_close + html[send:]

    # --- order: flex parent + per-section order rules ---
    for bp, pairs in order_groups.items():
        short = _BP_SHORT[bp]
        parent_cls = "bp-reorder-" + short
        # Prefer <main> if it wraps every ordered section, else <body>.
        m_main = re.search(r"<main\b[^>]*>.*?</main>", html, re.DOTALL)
        if m_main and all('id="%s"' % sid in m_main.group(0) for sid, _ in pairs):
            parent_pat = re.compile(r"(<main\b[^>]*>)")
        else:
            parent_pat = re.compile(r"(<body\b[^>]*>)")
        pm = parent_pat.search(html)
        if pm and parent_cls not in pm.group(1):
            html = (html[:pm.start(1)] + _add_class(pm.group(1), parent_cls)
                    + html[pm.end(1):])
        css_rules.append((bp, ".%s { display: flex !important; flex-direction: column !important; }"
                          % parent_cls))
        for sid, n in pairs:
            css_rules.append((bp, ".%s > .bp-ord-%s { order: %d; }" % (parent_cls, sid, n)))

    css_text = _build_css(css_rules)
    return html, css_text, warnings


def _build_css(css_rules):
    """Assemble the <style> body: base utilities + per-section rules per breakpoint."""
    if not css_rules:
        return ""  # no overrides -> no style block at all (desktop builds stay clean)
    chunks = [_BASE_CSS]
    by_bp = {}
    for bp, rule in css_rules:
        by_bp.setdefault(bp, []).append(rule)
    for bp in ("mobile", "tablet"):
        if bp in by_bp:
            chunks.append("@media %s {\n  %s\n}" % (
                BREAKPOINTS[bp], "\n  ".join(by_bp[bp])))
    return "\n".join(chunks)


def inject_breakpoint_css(html, css_text):
    """Inject the <style> block before </head>. Idempotent; no-op without overrides."""
    if not css_text or "bp-hide-m" in html and "CMS breakpoint overrides" in html:
        return html
    style = "<style>\n%s\n</style>" % css_text
    if "</head>" in html:
        return html.replace("</head>", style + "\n</head>", 1)
    return style + "\n" + html
