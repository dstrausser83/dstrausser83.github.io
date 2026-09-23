# Dead Brands mailing list — 5-minute setup

The site popup sends signups here. You do this once; Rock wires the site after.

## Steps

1. **Create the sheet.** Go to <https://sheets.new> and name it
   `Dead Brands mailing list`. (Leave it empty — the script adds the header row.)

2. **Open Apps Script.** In the sheet: `Extensions` → `Apps Script`.

3. **Paste the code.** Delete everything in the editor, paste the full
   contents of `Code.gs` from this folder, then `Ctrl+S` / `Cmd+S` to save.

4. **Deploy as a web app.**
   - Click `Deploy` → `New deployment`.
   - Type: `Web app`.
   - Description: `Dead Brands mailing list`.
   - **Execute as:** `Me`.
   - **Who has access:** `Anyone`.
   - Click `Deploy`.
   - Google will ask for authorization: choose your account → `Advanced` →
     `Go to <project name> (unsafe)` → `Allow`. (It's your own script
     touching your own sheet — that's the scary-looking but normal step.)

5. **Copy the Web app URL** (it looks like
   `https://script.google.com/macros/s/AKfyc.../exec`) and send it to Rock.

Rock pastes it into the site, pushes, and the popup goes live — every signup
lands as a new row: Timestamp, First name, Last name, Email.

## v2 upgrade (analytics + CRM dashboard)

The `Code.gs` in this folder now routes pageviews (from `assets/js/analytics.js`)
into a `Pageviews` tab, serves `?action=kpis&key=READ_KEY` JSON for the CRM
portal, and builds a live `Dashboard` tab. To upgrade an existing v1 project:

1. Paste the new `Code.gs` over the old one and save.
2. **Project Settings → Script properties:** add `READ_KEY` = a long random
   string (the same value goes in the CRM portal config).
   The mailing-list tab is detected automatically from the v1 header row and
   remembered in a `MAIL_SHEET_NAME` property — which tab is active in the UI
   never matters. Override `MAIL_SHEET_NAME` manually only if the wrong tab
   was picked.
3. In the editor, run `setupDashboard()` once (authorizes on first run).
4. **Deploy → Manage deployments →** edit the Web app → **New version**.
   The `/exec` URL stays the same.

## v3 upgrade (Quaint referral click tracking)

The `Code.gs` now accepts `action="quaint_click"` from
`assets/js/quaint-clicks.js` and logs each outbound click to Quaint into a new
`Quaint Clicks` tab (dedupe on Event ID — retries never double-count). The
`?action=kpis` JSON gains a `quaint_referrals` block the CRM portal renders.

To upgrade an existing v2 project:

1. Paste the new `Code.gs` over the old one and save.
2. **Deploy → Manage deployments →** edit the Web app → **New version**.
   The `/exec` URL stays the same.
3. (Optional) run `setupDashboard()` again to add the Quaint rows to the
   Dashboard tab.

Until this redeploy happens, click events from the site are **not lost** —
the browser buffers them and they flush into the sheet on a later visit
after the new version is live.

## Notes

- Signups you collect are yours, in your Google account. No third-party
  form service ever sees them.
- To stop the popup later, tell Rock — it's a one-line change.
- Preview the popup design anytime at:
  `https://dstrausser83.github.io/?preview=popup`
