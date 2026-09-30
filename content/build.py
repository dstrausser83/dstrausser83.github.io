#!/usr/bin/env python3
"""
CMS Build Script - Merge content JSON into HTML templates.
Usage: python3 build.py <page_slug>

This script:
1. Reads content/<page>.json
2. Loads the template HTML (the current .html file)
3. Replaces editable fields with values from JSON
4. Handles section enabled/disabled (wraps in HTML comments if disabled)
5. Writes the output HTML

The template HTML is lane B's code - this script only swaps content values,
never restructures the markup.
"""

import json
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime, timezone

from bp_engine import apply_breakpoint_overrides, inject_breakpoint_css  # lane A5

SITE_ROOT = Path(__file__).resolve().parent.parent  # lane A5: location-independent (PC + VM)
CONTENT_DIR = SITE_ROOT / "content"
HISTORY_DIR = CONTENT_DIR / "history"

def build_hero_section(html, fields):
    """Replace hero section fields in the HTML."""
    # Find hero section
    pattern = r'(<section class="hero" id="top">)(.*?)(</section>)'
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        raise ValueError("Hero section not found in template")
    
    hero = m.group(2)
    
    # Replace each field
    # Eyebrow
    hero = re.sub(
        r'<p class="eyebrow reveal">.*?</p>',
        f'<p class="eyebrow reveal">{fields["eyebrow"]}</p>',
        hero, count=1, flags=re.DOTALL
    )
    
    # Heading (allow HTML)
    hero = re.sub(
        r'<h1 class="reveal">.*?</h1>',
        f'<h1 class="reveal">{fields["heading"]}</h1>',
        hero, count=1, flags=re.DOTALL
    )
    
    # Tagline
    hero = re.sub(
        r'<p class="tagline reveal">.*?</p>',
        f'<p class="tagline reveal">{fields["tagline"]}</p>',
        hero, count=1, flags=re.DOTALL
    )
    
    # Hero sub (allow HTML)
    hero = re.sub(
        r'<p class="hero-sub reveal">.*?</p>',
        f'<p class="hero-sub reveal">{fields["hero_sub"]}</p>',
        hero, count=1, flags=re.DOTALL
    )
    
    # Primary CTA
    hero = re.sub(
        r'<a class="btn btn-primary" href="[^"]*">.*?</a>',
        f'<a class="btn btn-primary" href="{fields["cta_primary_url"]}">{fields["cta_primary_text"]}</a>',
        hero, count=1, flags=re.DOTALL
    )
    
    # Secondary CTA
    hero = re.sub(
        r'<a class="btn btn-ghost" href="[^"]*">.*?</a>',
        f'<a class="btn btn-ghost" href="{fields["cta_secondary_url"]}">{fields["cta_secondary_text"]}</a>',
        hero, count=1, flags=re.DOTALL
    )
    
    # Hero image
    hero = re.sub(
        r'<img src="[^"]*" alt="[^"]*"',
        f'<img src="{fields["hero_image_src"]}" alt="{fields["hero_image_alt"]}"',
        hero, count=1
    )
    
    # Caption
    hero = re.sub(
        r'<figcaption>.*?</figcaption>',
        f'<figcaption>{fields["hero_caption"]}</figcaption>',
        hero, count=1, flags=re.DOTALL
    )
    
    return m.group(1) + hero + m.group(3)

def build_page_html(content, html):
    """Pure merge: content JSON + template HTML -> built HTML (no file IO).
    Lane A5 (2026-09-30): extracted from build_page so the portal breakpoint
    preview reuses the exact publish logic in-memory."""
    # Build each section
    for section_id, section in content["sections"].items():
        if not section.get("enabled", True):
            # Wrap disabled sections in HTML comments
            pattern = rf'(<section[^>]*id="{section_id}"[^>]*>)(.*?)(</section>)'
            html = re.sub(
                pattern,
                r'<!-- CMS-DISABLED \1\2\3 -->',
                html, count=1, flags=re.DOTALL
            )
            print(f"  Disabled section: {section_id}")
            continue
        
        # Re-enable if previously disabled
        pattern = rf'<!-- CMS-DISABLED (<section[^>]*id="{section_id}"[^>]*>)(.*?)(</section>) -->'
        html = re.sub(pattern, r'\1\2\3', html, count=1, flags=re.DOTALL)
        
        # Build section fields
        if section_id == "top" and "fields" in section:
            try:
                # Find and replace the hero section
                old_pattern = r'<section class="hero" id="top">.*?</section>'
                new_hero = build_hero_section(html, section["fields"])
                # Extract just the section from the result
                m = re.search(r'(<section class="hero" id="top">.*?</section>)', new_hero, re.DOTALL)
                if m:
                    html = re.sub(old_pattern, m.group(1), html, count=1, flags=re.DOTALL)
                    print(f"  Built section: {section_id} ({section['label']})")
            except Exception as e:
                print(f"  WARN {section_id}: {e}")
    
    # Lane A5 (2026-09-30): per-breakpoint overrides (additive; desktop untouched).
    # apply_breakpoint_overrides runs UNCONDITIONALLY: its strip pass removes
    # stale breakpoint markup from earlier builds, so removing all overrides
    # and republishing restores the pristine template byte-for-byte.
    overrides = content.get("overrides") or {}
    html, bp_css, bp_warnings = apply_breakpoint_overrides(html, content, overrides)
    for w in bp_warnings:
        print(f"  BP-WARN {w}")
    html = inject_breakpoint_css(html, bp_css)

    return html


def build_page(page_slug):
    """Build a page from its content JSON."""
    content_file = CONTENT_DIR / f"{page_slug}.json"
    if not content_file.exists():
        raise FileNotFoundError(f"Content file not found: {content_file}")
    
    content = json.loads(content_file.read_text())
    html_file = SITE_ROOT / content["file"]
    
    if not html_file.exists():
        raise FileNotFoundError(f"HTML template not found: {html_file}")
    
    # Backup current HTML before building
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_file = HISTORY_DIR / f"{page_slug}-{timestamp}.html.bak"
    shutil.copy2(html_file, backup_file)
    print(f"Backed up {html_file.name} to {backup_file.name}")
    
    html = html_file.read_text()
    
    html = build_page_html(content, html)

    # Write the built HTML
    html_file.write_text(html)
    print(f"\nBUILT {html_file}")
    print(f"Backup: {backup_file}")
    return str(html_file), str(backup_file)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 build.py <page_slug>")
        sys.exit(1)
    
    page_slug = sys.argv[1]
    try:
        build_page(page_slug)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
