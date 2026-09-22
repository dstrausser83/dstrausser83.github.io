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

## Notes

- Signups you collect are yours, in your Google account. No third-party
  form service ever sees them.
- To stop the popup later, tell Rock — it's a one-line change.
- Preview the popup design anytime at:
  `https://dstrausser83.github.io/?preview=popup`
