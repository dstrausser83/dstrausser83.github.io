/**
 * deadbrands-chatbot — edge lead-chatbot for deadbrands.co
 * ==========================================================
 * Runs ONLY on Cloudflare Workers (+ Workers AI + Workers KV).
 * NEVER on David's PC. PC-outage survival is the core design rule:
 * the PC being down degrades SYNC, never lead capture.
 *
 * Flow:
 *   1. EDGE LEAD STORE  — every captured lead -> KV outbox immediately,
 *      keyed by UTC date namespace, synced:false. Never memory-only.
 *   2. OUTBOX + SYNC    — scheduled() every 15 min POSTs unsynced leads to
 *      the CRM intake endpoint; 2xx -> synced:true. Retry with backoff;
 *      failures stay queued. PC unreachable => sync waits, capture continues.
 *   3. CACHED AVAIL     — David's availability cached in KV (15-min TTL).
 *      PC offline => chatbot keeps booking from last cached availability.
 *      Honesty: self-serve Apollo booking link always offered; bot-assisted
 *      bookings are stored as TENTATIVE holds and the visitor is told plainly
 *      "I've held [time] for you — David's team will confirm it shortly."
 *   4. AVAIL ADAPTER    — getAvailability(): tries CRM_AVAILABILITY_URL first,
 *      then KV cache (fresh, then stale), then Apollo-link-only fallback.
 *
 * Endpoints:
 *   POST /chat   { sessionId, message, pageUrl }  -> { reply, persona, actions }
 *   POST /lead   structured capture fallback      -> { ok, leadId }
 *   GET  /health
 *   scheduled()  outbox sync cron
 */

// ---------------------------------------------------------------- models ---
const MODEL = "@cf/meta/llama-3.1-8b-instruct"; // Workers AI, free tier
const APOLLO_LINK = "https://app.apollo.io/#/meet/david_strausser_175";
const AVAIL_TTL_S = 15 * 60;          // availability cache: 15 min fresh
const AVAIL_STALE_TTL_S = 24 * 3600;  // stale cache kept 24h for outage mode
const SESSION_TTL_S = 2 * 3600;       // chat session memory: 2 h
const SYNC_LOOKBACK_DAYS = 2;

// --------------------------------------------------------------- personas ---
const PERSONAS = [
  {
    name: "Nova",
    style:
      "Warm, upbeat, a touch playful. Greets like a friend waving you over. " +
      "Short opener, one question at a time.",
  },
  {
    name: "Ruby",
    style:
      "Calm, direct, no-fluff. Professional but friendly. Gets to the point " +
      "and respects the visitor's time.",
  },
  {
    name: "Skye",
    style:
      "Curious and conversational. Asks open-ended questions, remembers " +
      "details, makes the chat feel human — while never claiming to be human.",
  },
];

const SERVICES_BLURB = [
  "Dead Brands, LLC — David Strausser's consulting and media company.",
  "Services: (1) independent ERP SELECTION consulting — helping small businesses",
  "choose between SAP Business One, Odoo, and other systems with an unbiased eye;",
  "(2) ERP implementations via Quaint Business Solutions (SAP Business One partner);",
  "(3) Odoo expertise (David knows Odoo inside and out); (4) AI, automation, sales",
  "and marketing services for small businesses; (5) the Shark Bite Biz podcast and",
  "brand/marketing content. David is a contracted Head of Sales for Quaint Business",
  "Solutions and CEO of Dead Brands, LLC.",
].join(" ");

// -------------------------------------------------------------- utilities ---
function corsHeaders(env, req) {
  const origins = (env.ALLOWED_ORIGINS ||
    "https://deadbrands.co,https://www.deadbrands.co")
    .split(",")
    .map((s) => s.trim());
  const origin = req.headers.get("Origin") || "";
  const allowed = origins.includes(origin) ? origin : origins[0];
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}
const json = (env, req, obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json", ...corsHeaders(env, req) },
  });

const uuid = () => crypto.randomUUID();
const nowISO = () => new Date().toISOString();
const todayUTC = () => nowISO().slice(0, 10); // YYYY-MM-DD

// ---------------------------------------------------- availability adapter ---
/**
 * Availability adapter. Fallback chain:
 *   1. Live CRM calendar endpoint (CRM_AVAILABILITY_URL) -> cache it 15 min.
 *   2. Fresh KV cache (< 15 min).
 *   3. Stale KV cache (up to 24 h) — PC-offline mode, flagged `stale:true`.
 *   4. null — offer the Apollo self-serve link only.
 *
 * CRM endpoint contract (see CONTRACT.md): GET returns
 *   { ok:true, timezone:"America/New_York", slots:[{start, end, label}], cached_at }
 * Auth: Authorization: Bearer <CRM_API_KEY>.
 */
async function getAvailability(env) {
  // 1) live attempt
  if (env.CRM_AVAILABILITY_URL) {
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 8000);
      const r = await fetch(env.CRM_AVAILABILITY_URL, {
        headers: { Authorization: `Bearer ${env.CRM_API_KEY || ""}` },
        signal: ctrl.signal,
      });
      clearTimeout(t);
      if (r.ok) {
        const data = await r.json();
        data.cached_at = nowISO();
        await env.DB_CACHE.put("cache:availability", JSON.stringify(data), {
          expirationTtl: AVAIL_STALE_TTL_S,
        });
        return { source: "live", stale: false, ...data };
      }
    } catch {
      /* fall through to cache — capture never blocks */
    }
  }
  // 2) fresh cache, 3) stale cache
  const cached = await env.DB_CACHE.get("cache:availability");
  if (cached) {
    const data = JSON.parse(cached);
    const age = Date.now() - Date.parse(data.cached_at || 0);
    if (!Number.isNaN(age) && age < AVAIL_TTL_S * 1000)
      return { source: "cache", stale: false, ...data };
    return { source: "cache", stale: true, ...data };
  }
  // 4) Apollo link only
  return null;
}

// ------------------------------------------------------- lead capture -------
/**
 * Writes a lead to the edge outbox immediately. KV key:
 *   outbox:<YYYY-MM-DD>:<uuid>
 * Also mirrors a canonical copy at lead:<uuid> for direct lookup.
 * Schema (see CONTRACT.md):
 *   { id, name, email, company, need, pageUrl, persona, summary,
 *     conversation, ts, synced:false, attempts:0, lastAttempt:null }
 */
async function storeLead(env, lead) {
  const record = {
    id: lead.id || uuid(),
    name: lead.name || null,
    email: lead.email || null,
    company: lead.company || null,
    need: lead.need || null,
    pageUrl: lead.pageUrl || null,
    persona: lead.persona || null,
    summary: lead.summary || null,
    conversation: lead.conversation || null,
    ts: nowISO(),
    synced: false,
    attempts: 0,
    lastAttempt: null,
    type: "lead",
  };
  const key = `outbox:${todayUTC()}:${record.id}`;
  await env.DB_LEADS.put(key, JSON.stringify(record));
  await env.DB_LEADS.put(`lead:${record.id}`, JSON.stringify(record));
  return record;
}

/** Tentative booking hold — bot-assisted "book me" requests. */
async function storeHold(env, hold) {
  const record = {
    id: hold.id || uuid(),
    name: hold.name || null,
    email: hold.email || null,
    requestedTime: hold.requestedTime || null,
    slot: hold.slot || null,
    pageUrl: hold.pageUrl || null,
    persona: hold.persona || null,
    summary: hold.summary || null,
    ts: nowISO(),
    synced: false,
    attempts: 0,
    lastAttempt: null,
    type: "tentative_hold",
    status: "tentative", // never "confirmed" until CRM verifies it
  };
  const key = `outbox:${todayUTC()}:${record.id}`;
  await env.DB_LEADS.put(key, JSON.stringify(record));
  return record;
}

// ------------------------------------------------------------- outbox sync ---
function backoffDue(lead) {
  if (!lead.lastAttempt) return true;
  const waitMs = Math.min(30 * 60 * 1000, 60 * 1000 * 2 ** (lead.attempts || 0));
  return Date.now() - Date.parse(lead.lastAttempt) >= waitMs;
}

async function syncOutbox(env) {
  const intake = env.CRM_LEAD_INTAKE_URL;
  if (!intake) return { skipped: "CRM_LEAD_INTAKE_URL not configured" };
  const days = [];
  for (let i = 0; i < SYNC_LOOKBACK_DAYS; i++) {
    const d = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    days.push(d);
  }
  const results = { delivered: 0, failed: 0, skipped: 0 };
  for (const day of days) {
    let cursor = undefined;
    do {
      const page = await env.DB_LEADS.list({ prefix: `outbox:${day}:`, cursor });
      for (const { name } of page.keys) {
        const raw = await env.DB_LEADS.get(name);
        if (!raw) continue;
        const lead = JSON.parse(raw);
        if (lead.synced) {
          results.skipped++;
          continue;
        }
        if (!backoffDue(lead)) {
          results.skipped++;
          continue;
        }
        lead.attempts = (lead.attempts || 0) + 1;
        lead.lastAttempt = nowISO();
        try {
          const ctrl = new AbortController();
          const t = setTimeout(() => ctrl.abort(), 15000);
          const r = await fetch(intake, {
            method: "POST",
            headers: {
              "content-type": "application/json",
              Authorization: `Bearer ${env.CRM_API_KEY || ""}`,
            },
            body: JSON.stringify(lead),
            signal: ctrl.signal,
          });
          clearTimeout(t);
          if (r.status >= 200 && r.status < 300) {
            lead.synced = true;
            await env.DB_LEADS.put(name, JSON.stringify(lead));
            await env.DB_LEADS.put(`lead:${lead.id}`, JSON.stringify(lead));
            results.delivered++;
          } else {
            await env.DB_LEADS.put(name, JSON.stringify(lead));
            results.failed++;
          }
        } catch {
          // PC/CRM unreachable -> stays queued, backoff applies. Never lost.
          await env.DB_LEADS.put(name, JSON.stringify(lead));
          results.failed++;
        }
      }
      cursor = page.list_complete ? undefined : page.cursor;
    } while (cursor);
  }
  return results;
}

// ---------------------------------------------------------- chat handling ---
const LEAD_TOOL = {
  name: "capture_lead",
  description:
    "Save the visitor's contact details to the CRM outbox as soon as you have " +
    "a name and email (plus anything else they shared). Call it once per " +
    "conversation, then confirm warmly. Do NOT ask for all fields upfront — " +
    "ask conversationally.",
  parameters: {
    type: "object",
    properties: {
      name: { type: "string", description: "Visitor's full name" },
      email: { type: "string", description: "Visitor's email address" },
      company: { type: "string", description: "Company or organization" },
      need: {
        type: "string",
        description: "What they need help with (1-2 sentences)",
      },
      summary: {
        type: "string",
        description: "Short summary of the conversation so far",
      },
    },
    required: ["name", "email"],
  },
};

async function getPersona(env, sessionId) {
  const skey = `session:${sessionId}`;
  const existing = await env.DB_CACHE.get(skey);
  if (existing) {
    const s = JSON.parse(existing);
    return { persona: PERSONAS[s.personaIdx] || PERSONAS[0], newSession: false, skey, s };
  }
  // rotate via atomic-ish counter
  let n = parseInt((await env.DB_CACHE.get("persona:counter")) || "0", 10) || 0;
  n += 1;
  await env.DB_CACHE.put("persona:counter", String(n));
  const personaIdx = n % PERSONAS.length;
  const s = { personaIdx, createdAt: nowISO(), turns: [] };
  await env.DB_CACHE.put(skey, JSON.stringify(s), { expirationTtl: SESSION_TTL_S });
  return { persona: PERSONAS[personaIdx], newSession: true, skey, s };
}

function systemPrompt(persona, avail, pageUrl) {
  let availNote;
  if (avail && avail.slots && avail.slots.length) {
    const labels = avail.slots.slice(0, 6).map((s) => s.label || s.start).join("; ");
    availNote =
      (avail.stale ? "(Note: these slots are from a cached calendar — offer them, and if the visitor picks one, save it as a TENTATIVE hold.) " : "") +
      `David's open times right now: ${labels}. You may offer these.`;
  } else if (avail && avail.stale) {
    availNote =
      "The calendar is temporarily offline, so no live slots are visible. " +
      "Offer the self-serve booking link below.";
  } else {
    availNote =
      "No calendar slots are available right now. Offer the self-serve booking link below.";
  }
  return [
    `You are ${persona.name}, an AI virtual assistant for Dead Brands, LLC — never a human, never David, never a sales rep. Say so if asked.`,
    `Personality: ${persona.style}`,
    `Company context: ${SERVICES_BLURB}`,
    `Team hand-off: the warm sales rep is "Deacon from our team" — route warm hand-offs to him by name and role.`,
    `Self-serve booking link (always works): ${APOLLO_LINK} — offer it freely whenever someone wants time with David.`,
    `Availability: ${availNote}`,
    `BOOKING HONESTY RULE (critical): you may NEVER fake-confirm a booking. If the visitor asks you to book a specific time, save it as a TENTATIVE hold via capture_lead (put the requested time in the need/summary) and say: "I've held [time] for you — David's team will confirm it shortly." The hold syncs to the CRM later.`,
    `Goal: qualify and capture leads — name, email, company, what they need. Ask conversationally, one question at a time. When you have name + email, call the capture_lead tool immediately, then confirm warmly.`,
    `Guardrails: never invent prices, timelines, client names, statistics, or David's credentials. If you don't know something, offer the free consult booking link (${APOLLO_LINK}) or Deacon's follow-up. Keep replies short and conversational — 1-3 short sentences, never walls of text.`,
    pageUrl ? `The visitor is on: ${pageUrl}` : "",
  ].join("\n");
}

async function handleChat(env, req, body) {
  const { sessionId, message, pageUrl } = body || {};
  if (!sessionId || !message) return json(env, req, { error: "sessionId and message required" }, 400);
  if (String(message).length > 4000) return json(env, req, { error: "message too long" }, 400);

  const { persona, skey, s } = await getPersona(env, String(sessionId));
  const avail = await getAvailability(env);

  const history = (s.turns || []).slice(-8).flatMap((t) => [
    { role: "user", content: t.u },
    { role: "assistant", content: t.a },
  ]);
  const messages = [
    { role: "system", content: systemPrompt(persona, avail, pageUrl) },
    ...history,
    { role: "user", content: String(message) },
  ];

  let ai;
  try {
    ai = await env.AI.run(MODEL, {
      messages,
      tools: [LEAD_TOOL],
      max_tokens: 300,
      temperature: 0.7,
    });
  } catch (e) {
    return json(env, req, {
      reply:
        "I'm having a quick technical moment — want to grab time directly? " +
        `Here's David's booking link: ${APOLLO_LINK}`,
      persona: persona.name,
      fallback: true,
    });
  }

  let reply = "";
  const actions = [];
  if (ai && ai.tool_calls && ai.tool_calls.length) {
    for (const tc of ai.tool_calls) {
      if (tc.name === "capture_lead") {
        const args = tc.arguments || {};
        const conv = [...history, { role: "user", content: String(message) }]
          .map((m) => `${m.role}: ${m.content}`)
          .join("\n")
          .slice(-3000);
        const lead = await storeLead(env, {
          name: args.name,
          email: args.email,
          company: args.company,
          need: args.need,
          pageUrl: pageUrl || null,
          persona: persona.name,
          summary: args.summary || args.need || null,
          conversation: conv,
        });
        actions.push({ type: "lead_captured", leadId: lead.id });
        reply += "";
      }
    }
    reply =
      ai.response ||
      "Got it — you're all set! Deacon from our team will follow up shortly. Want to grab a time with David directly too? " +
        APOLLO_LINK;
  } else {
    reply = ai && ai.response ? ai.response : "How can I help you today?";
  }

  // remember the turn (trimmed)
  s.turns = [...(s.turns || []), { u: String(message).slice(0, 500), a: reply.slice(0, 500) }].slice(-10);
  await env.DB_CACHE.put(skey, JSON.stringify(s), { expirationTtl: SESSION_TTL_S });

  return json(env, req, {
    reply,
    persona: persona.name,
    personaLabel: "AI virtual assistant",
    actions,
    availability: avail ? { source: avail.source, stale: !!avail.stale } : { source: "apollo_link" },
  });
}

// ----------------------------------------------------------------- router ---
export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(env, req) });
    }
    if (req.method === "GET" && url.pathname === "/health") {
      return json(env, req, {
        ok: true,
        model: MODEL,
        crm_intake_configured: !!env.CRM_LEAD_INTAKE_URL,
        availability_configured: !!env.CRM_AVAILABILITY_URL,
        ts: nowISO(),
      });
    }
    if (req.method === "POST" && url.pathname === "/chat") {
      let body;
      try {
        body = await req.json();
      } catch {
        return json(env, req, { error: "invalid JSON" }, 400);
      }
      return handleChat(env, req, body);
    }
    if (req.method === "POST" && url.pathname === "/lead") {
      let body;
      try {
        body = await req.json();
      } catch {
        return json(env, req, { error: "invalid JSON" }, 400);
      }
      if (!body.name || !body.email)
        return json(env, req, { error: "name and email required" }, 400);
      const lead = await storeLead(env, body);
      return json(env, req, { ok: true, leadId: lead.id });
    }
    if (req.method === "POST" && url.pathname === "/hold") {
      let body;
      try {
        body = await req.json();
      } catch {
        return json(env, req, { error: "invalid JSON" }, 400);
      }
      if (!body.requestedTime)
        return json(env, req, { error: "requestedTime required" }, 400);
      const hold = await storeHold(env, body);
      return json(env, req, {
        ok: true,
        holdId: hold.id,
        status: "tentative",
        message: "Held tentatively — the team will confirm shortly.",
      });
    }
    return json(env, req, { error: "not found" }, 404);
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(syncOutbox(env));
  },
};
