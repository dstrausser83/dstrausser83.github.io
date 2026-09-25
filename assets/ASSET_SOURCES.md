# Asset Sources — deadbrands.co

Provenance manifest for every visual and vendor asset on the site.
Last updated: 2026-09-24.

## Rules (standing)

- Everything is hosted locally in this repo. Nothing is hotlinked.
- No third-party partner logos anywhere. Vendor (Odoo / SAP) material only.
- No AI-generated people, no watermarks, no fake screenshots.
- Alt text and captions are honest: a screenshot is only ever described as what it shows.
- White papers / ebooks are LINKED to official sources, never re-hosted, unless the
  license explicitly allows redistribution.

## Service page imagery (`assets/img/services/`)

Per-file source URLs and license basis live in `ATTRIBUTION.md` next to the files.
Summary of license basis by file:

| File | Basis |
|---|---|
| dead-brands-1.jpg | CC BY-SA 3.0 (Wikimedia Commons) — attribution in ATTRIBUTION.md |
| dead-brands-2.jpg | CC0 (Wikimedia Commons) |
| small-business-growth-1.jpg | Vecteezy free license |
| small-business-growth-2.jpg | Pexels license (photo by Ivan Samkov) |
| sales-expert-1.jpg | Official odoo.com imagery (Odoo partner reuse) |
| sales-expert-2.jpg | Pexels license |
| marketing-expert-1.jpg | Whatagraph product screenshot (fair use, commentary) |
| marketing-expert-2.jpg | Benchmark Email product screenshot (fair use, commentary) |
| business-development-1.jpg | CC BY 2.0 (Wikimedia Commons) — attribution in ATTRIBUTION.md |
| business-development-2.jpg | Public domain — NASA |
| tech-consulting-1.jpg | CC BY-SA 2.0 (Wikimedia Commons) — attribution in ATTRIBUTION.md |
| tech-consulting-2.jpg | Used with source credit (BackToCode) |
| odoo-1.jpg | Official odoo.com CDN asset (odoocdn.com) — Odoo partner reuse |
| odoo-2.jpg | Official odoo.com imagery — Odoo partner reuse |
| odoo-3.jpg | Official odoo.com imagery — Odoo partner reuse |
| sap-business-one-1.jpg | Official SAP product image (SAP DAM, via mirror) — SAP partner reuse |
| sap-business-one-2.jpg | Detail crop of sap-business-one-1.jpg (official SAP product image) — SAP partner reuse |
| erp-1.jpg | ShopXpert product screenshot (fair use, commentary) |
| erp-2.jpg | CC BY-SA 3.0 (Wikimedia Commons) — attribution in ATTRIBUTION.md |
| erp-3.jpg | Used with source credit (WorkD) |

"Odoo partner reuse" / "SAP partner reuse": David Strausser operates as an Odoo and
SAP Business One implementation partner. Both vendors permit partners to reuse official
product imagery in partner marketing. If either vendor ever objects to a specific asset,
it will be removed same-day.

## Layout system (added 2026-09-24)

Every service page uses a distinct layout recipe — no two pages share the same
hero treatment + body figure combination:

- Heroes: `svc-hero-figure` (centered), `fig-band` (full-bleed), `fig-hero-offset` (right-pushed)
- Body: `fig-inset` (68% centered), `fig-wide` (column breakout), `fig-frame` (polaroid),
  `fig-sidenote` (caption as side note), `fig-numbered` (numbered caption), `fig-left-align` (85% left)

Recipes are documented in the deploy notes; the CSS lives in `assets/css/styles.css`.

## Official vendor resources (linked, not hosted)

These appear on `resources.html` under "Official vendor resources", and since
2026-09-24 also inline in each product page's "Further reading" section
(`services/odoo.html`, `services/sap-business-one.html`):

- Odoo official documentation — https://www.odoo.com/documentation/
- Odoo CRM product tour — https://www.odoo.com/app/crm
- Odoo Accounting product tour — https://www.odoo.com/app/accounting
- Odoo Inventory product tour — https://www.odoo.com/app/inventory
- SAP Business One product page — https://www.sap.com/products/business-one.html

All links verified live 2026-09-24 (odoo.com pages fetched directly; the SAP product
page is SAP's canonical B1 URL, cited in this repo's image attribution).
