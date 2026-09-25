# deadbrands-chatbot — CRM Contract + Deploy Runbook

Worker: `workers/chatbot/worker.js` (name `deadbrands-chatbot`)
Edge runtime: Cloudflare Workers + Workers AI + Workers KV.
**This chatbot never runs on David's PC.** PC-outage survival is the design rule:
the PC being down degrades SYNC, never lead capture.

---

## 1. CRM endpoint contract (for the parallel CRM-calendar build)

The worker ships with these endpoints UNCONFIGURED — lead capture works fully
without them (the outbox just queues until they're live).

### 1a. Lead intake (sync target)

Set env `CRM_LEAD_INTAKE_URL` to the full HTTPS URL (e.g.
`https://crm.deadbrands.co/api/lead-intake` or the portal's endpoint).
Auth: `Authorization: Bearer <CRM_API_KEY>` (`wrangler secret put CRM_API_KEY`).

The worker `POST`s JSON, `Content-Type: application/json`, one lead per request:

```json
{
  "id": "8f3a1c2e-…",
  "name": "Jane Smith",
  "email": "jane@acme.com",
  "company": "Acme Corp",
  "need": "Choosing between SAP Business One and Odoo for a 40-person distributor",
  "pageUrl": "https://deadbrands.co/services.html",
  "persona": "Nova",
  "summary": "Needs ERP selection help; 40-person distributor",
  "conversation": "user: …\nassistant: …",
  "ts": "2026-09-24T23:41:02.111Z",
  "synced": false,
  "attempts": 1,
  "lastAttempt": "2026-09-24T23:45:00.000Z",
  "type": "lead"
}
```

Tentative booking holds use `type: "tentative_hold"` with fields
`requestedTime` (ISO string, what the visitor asked for),
`slot` (the availability slot offered, if any) and `status: "tentative"`.
**A hold is never confirmed by the bot.** The CRM must confirm (or release) the
hold and follow up with the visitor. Map it to a pending task / pipeline stage
named e.g. `chatbot-hold`.

Success contract: **any 2xx** marks the lead `synced:true` at the edge.
On 4xx/5xx/network failure the lead stays queued with exponential backoff
(1m, 2m, 4m, … capped at 30m). Dedup on `id` — the worker retries, so the CRM
must treat repeated posts of the same `id` as idempotent.

### 1b. Availability (booking slots)

Set env `CRM_AVAILABILITY_URL` to the full HTTPS URL (e.g.
`https://crm.deadbrands.co/api/availability`).
Auth: same `Authorization: Bearer <CRM_API_KEY>`.

`GET` must return:

```json
{
  "ok": true,
  "timezone": "America/New_York",
  "slots": [
    { "start": "2026-09-25T14:00:00-04:00", "end": "2026-09-25T14:30:00-04:00", "label": "Tomorrow 2:00 PM ET" },
    { "start": "2026-09-25T15:30:00-04:00", "end": "2026-09-25T16:00:00-04:00", "label": "Tomorrow 3:30 PM ET" }
  ],
  "note": "optional human-readable note"
}
```

Rules for the CRM builder:
- Return **up to ~10** upcoming free 30-min slots; all fields ISO 8601 with offset.
- Keep response time **under 5 seconds** (the worker aborts at 8s and falls back).
- `label` is shown verbatim to visitors — keep it short and friendly ("Tomorrow 2:00 PM ET").
- The worker caches a successful response for **15 minutes** (`cache:availability`).
- If the endpoint errors or times out, the worker silently uses the cached slots
  (marked stale) or, with no cache at all, offers only the Apollo self-serve link.
- Recommended source: David's Google Calendar via the existing
  `google-calendar` skill / connector on the PC side — pushed or polled from the
  CRM, not from the worker.

---

## 2. Environment variables

| Var | Where | Purpose |
|---|---|---|
| `ALLOWED_ORIGINS` | `[vars]` | CORS allowlist. Default: `https://deadbrands.co,https://www.deadbrands.co` |
| `CRM_LEAD_INTAKE_URL` | `[vars]` | §1a. Empty = queue-only mode (fully functional). |
| `CRM_AVAILABILITY_URL` | `[vars]` | §1b. Empty = Apollo-link-only mode. |
| `CRM_API_KEY` | **secret** | `wrangler secret put CRM_API_KEY` — Bearer token for both CRM endpoints. |

---

## 3. KV schema

### DB_LEADS (outbox + canonical records)
| Key | Value |
|---|---|
| `outbox:<YYYY-MM-DD>:<uuid>` | Full lead/hold JSON (schema §1a). `synced:false` until the cron 2xx's it. Scanned with prefix `outbox:<date>:` for the last 2 days by the sync cron. |
| `lead:<uuid>` | Canonical copy of the latest state of that lead (synced flag kept current). |

### DB_CACHE (sessions, availability, rotation)
| Key | TTL | Value |
|---|---|---|
| `cache:availability` | 24h | Last good availability payload + `cached_at` (fresh < 15 min; older = stale/outage mode). |
| `session:<uuid>` | 2h | `{ personaIdx, createdAt, turns:[{u,a}…] }` — last 10 turns. |
| `persona:counter` | none | Monotonic integer — `counter % 3` picks Nova/Ruby/Skye so personas rotate across visitors. |

---

## 4. PC-outage survival chain (plain words)

1. Visitor chats → Workers AI answers → lead captured → written to KV **instantly** (nothing lives only in memory).
2. Every 15 min the cron POSTs unsynced leads to the CRM intake URL.
3. If the CRM/PC is unreachable: the POST fails, the lead stays in the outbox with
   backoff, the cron tries again next run. **Capture never blocks, nothing is lost.**
4. Availability: live CRM calendar → 15-min KV cache → stale KV cache (up to 24h,
   offered honestly as cached) → Apollo self-serve booking link
   (https://app.apollo.io/#/meet/david_strausser_175), which always works.
5. Bot-assisted bookings are stored as **TENTATIVE holds**; the visitor is told
   "I've held [time] for you — David's team will confirm it shortly."
   The bot never fake-confirms a booking it can't verify.

---

## 5. Deploy runbook (exact steps — nothing deployed from here)

Prereqs: a Cloudflare account David controls. The worker needs Workers AI
(free tier) and two KV namespaces.

1. `npm i -g wrangler`
2. `wrangler login` — **David's hands**: one browser click, OAuth into Cloudflare.
   Nobody else can do this step for him.
3. From `workers/chatbot/`:
   `wrangler kv:namespace create DB_LEADS`
   `wrangler kv:namespace create DB_CACHE`
   → paste both returned IDs into the `kv_namespaces` blocks in `wrangler.toml`,
   replacing the `REPLACE_WITH_…` placeholders.
4. `wrangler deploy` — run from `workers/chatbot/`.
   Copy the `*.workers.dev` URL it prints.

Then wire the site (parent agent's include step — NOT done here):
- In `assets/js/chat-widget.js` set `WORKER_URL` to the deployed worker URL.
- Add `<link rel="stylesheet" href="/assets/css/chat.css">` and
  `<script src="/assets/js/chat-widget.js" defer></script>` to the site template.
- Optionally `wrangler secret put CRM_API_KEY`, and set `CRM_LEAD_INTAKE_URL` /
  `CRM_AVAILABILITY_URL` in `wrangler.toml` once the CRM endpoints exist
  (chat works without them).

Post-deploy checks:
- `curl https://<worker>.workers.dev/health` → `{"ok":true,…}`
- Open deadbrands.co, wait 60s → chatbot greets; send a message, give name+email
  → `wrangler kv:key list --namespace-id <DB_LEADS_ID> --prefix "outbox:"` shows it.
