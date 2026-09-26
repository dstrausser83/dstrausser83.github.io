# Base Template — every page, no exceptions

Standing rule (David, 2026-09-26): **every page gets tracking, heatmap,
analytics, and the same header & footer.** This is the core of the whole
site — the base every landing page inherits.

## The five required elements

1. **Head consent defaults** — first thing inside `<head>`: the
   `gtag('consent', 'default', ...)` block denying ad/analytics storage
   until the visitor accepts. (Text: see `tools/enforce-base-template.py`
   `HEAD_CONSENT`.)
2. **Tracking scripts before `</body>`** (all `defer`):
   `main.js`, `consent.js`, `chat-widget.js`. `consent.js` is the gate —
   Clarity, first-party `heat.js`, RB2B, and Leadfeeder load only on Accept,
   nothing loads on Decline.
3. **Standard header** — `<header class="site-header" id="site-header">`
   (canonical copy: `tools/canonical-header.html`; set `aria-current` on the
   page's own nav section).
4. **Standard footer** — `<footer class="site-footer">` (canonical copy:
   `tools/canonical-footer.html`), including the Cookie Policy link and the
   **Cookie settings** link (`window.DBConsent.show()`) so visitors can
   change consent after the fact.
5. **Stylesheet cache-bust** — `styles.css?v=<ver>` (`?v=YYYYMMDDx`); bump
   on ALL pages + `blog/build_post.py` whenever `assets/css/styles.css`
   changes.

## Exemptions (documented, enforced by CI)

- **Redirect stubs** (`meta refresh` + `noindex`, e.g. `shop/index.html`,
  `services/erp-selection.html`): exempt from all five. They exist for
  0 seconds; firing tracker pixels there would double-count the visit that
  lands on the real page a moment later. The destination page carries the
  full template.
- **Partials** under `tools/` (`nav-template.html`, `footer-template.html`,
  `canonical-*.html`): not pages, skipped.

## Tooling

- `tools/enforce-base-template.py` — fixes every violation in place.
- `.github/scripts/check-base-template.py` — CI gate; fails the build on
  any violation. Wired into `site-checks.yml` (`base-template` job).
- `blog/build_post.py` `PAGE_TEMPLATE` — new blog posts are generated with
  the full template baked in.
