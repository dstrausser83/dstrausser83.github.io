/**
 * deadbrands-chatbot — edge lead-chatbot for deadbrands.co
 * ==========================================================
 * Cloudflare Workers + Workers AI (free tier) + Workers KV.
 * Widget contract: POST /chat { sessionId, message, pageUrl }
 *   -> { reply, persona, personaLabel, actions }
 *
 * Personas Nova/Ruby/Skye are picked server-side via a rotating KV counter.
 * They are presented as AI virtual assistants — never human. If asked, they say so.
 *
 * Knowledge: entries from the site's chat_knowledge.json are bundled below and
 * matched by keyword against each visitor message (top-2 entries injected into
 * the system prompt). The model must NEVER invent prices, timelines, client
 * names, stats, or credentials — the guardrail says so explicitly.
 *
 * KV bindings (optional but recommended):
 *   DB_LEADS — lead/hold outbox + canonical records
 *   DB_CACHE — sessions, persona counter, availability cache
 * AI binding: AI (Workers AI)
 * The worker degrades gracefully if a binding is missing: chat still answers
 * from Workers AI; lead persistence falls back gracefully instead of 500ing.
 *
 * Env vars: ALLOWED_ORIGINS, CRM_LEAD_INTAKE_URL, CRM_AVAILABILITY_URL
 * Secret: CRM_API_KEY (Bearer for the CRM endpoints). No secrets in this file.
 */

const KNOWLEDGE = [{"key": "service:sap-business-one", "title": "SAP Business One Implementation & Consulting | David Strausser", "keywords": ["sap business one", "sap business one"], "body": "SAP Business One Implementation & Consulting | David Strausser Skip to content Dead Brands LLC Services — ERP SAP Business One The ERP I’ve sold, delivered, and run the business of — implemented for SMBs who need it done right. SAP Business One 10.0 — sales dashboards and visual process flow (detail of official SAP product image) I don’t just implement SAP Business One — I’ve run the business of implementing it. As G"}, {"key": "service:odoo", "title": "Odoo Implementation & Consulting for SMBs | David Strausser", "keywords": ["odoo", "odoo"], "body": "Odoo Implementation & Consulting for SMBs | David Strausser Skip to content Dead Brands LLC Services — ERP Odoo One system for the whole operation — implemented the grown-up way, so your team actually uses it. One system for the whole operation — implemented the grown-up way. Odoo is the Swiss Army knife of business software: CRM, accounting, inventory, manufacturing, ecommerce, project management, HR — dozens of app"}, {"key": "service:erp", "title": "ERP for SMBs — Selection, Implementation & Add-Ons | David Strausser", "keywords": ["erp", "erp consulting"], "body": "ERP for SMBs — Selection, Implementation & Add-Ons | David Strausser Skip to content Dead Brands LLC Services — ERP ERP The system your business runs on is the most important technology decision you’ll make this decade. Get it right. Photo: WorkD Start here Selection comes first. Always. Most ERP disasters don’t start at go-live — they start at selection, when a vendor sells you their product instead of your solution"}, {"key": "service:erp-selection", "title": "ERP Selection Consultative Services | David Strausser", "keywords": ["erp selection", "erp selection"], "body": "ERP Selection Consultative Services | David Strausser Redirecting to ERP for SMBs — Selection, Implementation & Add-Ons …"}, {"key": "service:tech-consulting", "title": "Tech Consulting — AI & Automation for SMBs | David Strausser", "keywords": ["tech consulting", "tech consulting"], "body": "Tech Consulting — AI & Automation for SMBs | David Strausser Skip to content Dead Brands LLC Services — Technology Tech Consulting Practical AI and automation for SMBs. Kill the swivel-chair work, connect your systems, and adopt technology that earns its keep. Photo: Wikimedia Commons (CC BY-SA 2.0) Everybody’s selling AI right now. Most of it is noise — chatbots nobody asked for, “AI-powered” features that do what a"}, {"key": "service:business-development", "title": "Business Development Specialist — Partnerships & Market Entry | David Strausser", "keywords": ["business development", "business development"], "body": "Business Development Specialist — Partnerships & Market Entry | David Strausser Skip to content Dead Brands LLC Services — Business Development Business Development Specialist Partnerships, alliances, and new markets — including the US/Latin America corridor I’ve worked for 15 years. Photo: Wikimedia Commons (CC BY 2.0) Sales closes deals. Business development opens doors that didn’t exist before — partnerships, alli"}, {"key": "service:sales-expert", "title": "Sales Expert — Pipeline, Process & BDR Playbooks | David Strausser", "keywords": ["sales expert", "sales"], "body": "Sales Expert — Pipeline, Process & BDR Playbooks | David Strausser Skip to content Dead Brands LLC Services — Sales Sales Expert Pipeline, process, and playbooks — from a guy who’s carried the number, run the region, and built the BD engine. Photo: Pexels I’ve been VP of Business Development at SEIDOR. I ran the Northeast region as General Manager at Vision33. Today I’m Head of Sales for Quaint Business Solutions. I’"}, {"key": "service:marketing-expert", "title": "Marketing Expert — Content Engine & Brand Storytelling | David Strausser", "keywords": ["marketing expert", "marketing"], "body": "Marketing Expert — Content Engine & Brand Storytelling | David Strausser Skip to content Dead Brands LLC Services — Marketing Marketing Expert Marketing that compounds: a story worth telling, told every week, everywhere your customers already are. Screenshot: Benchmark Email Here’s what I believe about marketing, and it’s unfashionable: the tactics don’t matter until the story is right. You can run the perfect ad cam"}, {"key": "service:small-business-growth", "title": "Small Business Growth Consulting | David Strausser | Dead Brands, LLC", "keywords": ["small business growth", "small business growth"], "body": "Small Business Growth Consulting | David Strausser | Dead Brands, LLC Skip to content Dead Brands LLC Services — Growth Small Business Growth Growth isn’t a tactic. It’s systems, sales, and marketing working together — instead of stepping on each other. Photo: Ivan Samkov via Pexels Most small businesses don’t have a growth problem. They have a everything-fighting-everything problem. Sales is winging it without a pro"}, {"key": "service:dead-brands", "title": "Dead Brand Stuff — Brand Revival & Growth Marketing | Dead Brands, LLC", "keywords": ["dead brands", "brand revival"], "body": "Dead Brand Stuff — Brand Revival & Growth Marketing | Dead Brands, LLC Skip to content Dead Brands LLC Services — Dead Brands Dead Brand Stuff Reviving the brands of yesterday, building the businesses of tomorrow. For good companies whose story stopped being true somewhere around 2014. Photo: Wikimedia Commons (CC BY-SA 3.0) Here’s a pattern I see constantly: a company with a solid business, real customers, and real "}, {"key": "about:david", "title": "About David Strausser", "keywords": ["david", "founder", "about", "who", "strausser", "ceo"], "body": "About Us | Dead Brands, LLC Skip to content Dead Brands LLC About Us We’re Dead Brands. A family-oriented small business with a loud personality that gets shit done. Who we are Dead Brands, LLC is a small crew with a big engine, based in Pottsville, Pennsylvania. We’re family-oriented to the core — this business runs on the same values as the dinner table: show up, tell the truth, and take care of your people. We’re "}, {"key": "contact:info", "title": "Contact Dead Brands", "keywords": ["contact", "email", "phone", "call", "whatsapp", "reach", "talk", "number"], "body": "Email David at david@deadbrands.co or call/text +1 (619) 779-2842. WhatsApp: https://wa.me/16197792842. Book a free consult any time: https://app.apollo.io/#/meet/david_strausser_175"}, {"key": "contact:emergency", "title": "Urgent help — reach David directly", "keywords": ["urgent", "emergency", "asap", "down", "crisis", "immediately", "critical", "halted", "broken"], "body": "If something is urgent — your system is down, production is halted, or you need David right now — call or text him directly at +1 (619) 779-2842. He's typically available for texts until 7 PM ET daily. For anything non-urgent, the free consult booking link is https://app.apollo.io/#/meet/david_strausser_175"}, {"key": "booking:how", "title": "Book a free consult", "keywords": ["book", "meeting", "schedule", "appointment", "call", "demo", "consult", "talk", "time", "calendar", "availability"], "body": "The fastest way to grab time with David is his booking link: https://app.apollo.io/#/meet/david_strausser_175 — pick a time that works for you. Or tell me your name, email, and a preferred time right here in chat and I'll hold it on his calendar."}, {"key": "brand:podcast", "title": "Shark Bite Biz podcast", "keywords": ["podcast", "shark bite", "sharkbite", "show", "listen"], "body": "The podcast Shark Bite Biz “In a world full of sharks, learn how to bite first!” 200+ episodes and counting — conversations with founders, executives, and fascinating humans about the 3 G’s : personal growth, professional growth, and business growth. Born during the 2020 lockdowns as a way to keep networking when the world shut down, it became a front-row seat to how real businesses actually grow in the roaring 20’s."}, {"key": "proof:fmt-steel-sap-business-one", "title": "FMT Steel — SAP Business One", "keywords": ["fmt steel — sap business one", "case study", "customer", "client", "results"], "body": "FMT Steel: 300% Growth on SAP Business One | Dead Brands Case Studies Skip to content Dead Brands LLC Home / Case Studies / FMT Steel SAP Business One Manufacturing FMT Steel: 300% Growth on SAP Business One A steel products manufacturer replaced error-prone manual processes with SAP Business One — including a full quality management system — and grew the business 300% while becoming 500% more profitable. 300% busine"}, {"key": "proof:inspiralia-odoo", "title": "Inspiralia — Odoo", "keywords": ["inspiralia — odoo", "case study", "customer", "client", "results"], "body": "Inspiralia: One Odoo System Replaces Five Disconnected Tools | Dead Brands Case Studies Skip to content Dead Brands LLC Home / Case Studies / Inspiralia Odoo Professional services Inspiralia: One Odoo System Replaces Five Disconnected Tools Austrian innovation consultancy Inspiralia consolidated Monday.com, DocuSign, MailChimp and legacy VPN-gated tools into a single Odoo platform — CRM, Sales, Accounting, Project an"}, {"key": "proof:purish-odoo", "title": "Purish — Odoo", "keywords": ["purish — odoo", "case study", "customer", "client", "results"], "body": "Purish: From Paper and Excel to Same-Day Shipping with Odoo | Dead Brands Case Studies Skip to content Dead Brands LLC Home / Case Studies / Purish Odoo Distribution & e-commerce Purish: From Paper and Excel to Same-Day Shipping with Odoo Berlin cosmetics distributor Purish replaced paper-and-Excel warehouse operations with Odoo Inventory, Purchase and Accounting — doubling purchase-to-invoice efficiency and shipping"}, {"key": "pricing:policy", "title": "Pricing", "keywords": ["price", "pricing", "cost", "how much", "quote", "rates", "fee", "fees"], "body": "Dead Brands doesn't publish fixed pricing — every engagement is scoped around your company size, systems, and goals. The free consult is the way to get a real number: https://app.apollo.io/#/meet/david_strausser_175"}, {"key": "process:how", "title": "How engagements work", "keywords": ["process", "how it works", "steps", "start", "begin", "engagement", "work with"], "body": "It starts with a free consult to understand your business and systems. From there David scopes the work — ERP selection, implementation, or growth work — and lays out next steps. Book the first step here: https://app.apollo.io/#/meet/david_strausser_175"}, {"key": "company:deadbrands", "title": "Dead Brands, LLC", "keywords": ["dead brands", "company", "business", "llc", "firm"], "body": "Dead Brands, LLC — brand revival, ERP consulting (SAP Business One and Odoo), and AI/automation for small business. Founded by David Strausser. Small crew, big engine."}, {"key": "how-it-works", "title": "How working with Dead Brands works", "keywords": ["process", "how it works", "engagement", "steps", "discovery", "assessment", "proposal", "timeline", "what happens next"], "body": "Three steps. (1) Discovery call: thirty minutes, free — a fit check on what hurts and whether Dead Brands is the right crew; if not, they say so. (2) Assessment: a dig into the client's real systems and processes to find where money is leaking. (3) Proposal & execution: a scoped plan with clear pricing and milestones, then build, ship, and stay until it works. Booking link: https://app.apollo.io/#/meet/david_strausse"}];


// ---------------------------------------------------------------- models ---
const MODEL = "@cf/meta/llama-3.1-8b-instruct-fp8"; // Workers AI free tier (2026-10-01: non-fp8 id retired by CF; fp8 verified live)
const APOLLO_LINK = "https://app.apollo.io/#/meet/david_strausser_175";
const AVAIL_TTL_S = 15 * 60;
const AVAIL_STALE_TTL_S = 24 * 3600;
const SESSION_TTL_S = 2 * 3600;
const SYNC_LOOKBACK_DAYS = 2;

// --------------------------------------------------------------- personas ---
const PERSONAS = [
  { name: "Nova", style: "Warm, upbeat, genuinely friendly — like a great host. Greets like a friend waving you over, uses the visitor's name once known. Short opener, one question at a time, always closes with a helpful follow-up." },
  { name: "Ruby", style: "Friendly and straight-shooting with professional warmth — never cold, never stiff. Gets to the point but makes it feel easy. Respects the visitor's time and always checks the answer actually helped." },
  { name: "Skye", style: "Curious, warm, conversational — like talking to a sharp friend. Asks open-ended questions, remembers details, keeps things personal — while never claiming to be human." },
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

// --------------------------------------- KV-safe helpers (never 500) -------
const memSessions = new Map(); // fallback when DB_CACHE binding is absent

async function kvGet(env, binding, key) {
  try { const ns = env[binding]; return ns ? await ns.get(key) : null; }
  catch { return null; }
}
async function kvPut(env, binding, key, value, ttl) {
  try {
    const ns = env[binding];
    if (!ns) return false;
    await ns.put(key, value, ttl ? { expirationTtl: ttl } : undefined);
    return true;
  } catch { return false; }
}

// --------------------------------------------------------------- utilities ---
function corsHeaders(env, req) {
  const origins = (env.ALLOWED_ORIGINS || "https://deadbrands.co,https://www.deadbrands.co").split(",").map(s => s.trim());
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
const todayUTC = () => nowISO().slice(0, 10);

// ------------------------------------------- knowledge retrieval (free) ----
/** Keyword match the visitor's message against bundled knowledge entries. */
function findKnowledge(message, maxEntries = 2) {
  const words = String(message).toLowerCase().split(/[^a-z0-9+]+/).filter(w => w.length > 2);
  if (!words.length) return [];
  const scored = KNOWLEDGE.map(e => {
    const hay = (e.key + " " + e.title + " " + e.keywords.join(" ") + " " + e.body).toLowerCase();
    let score = 0;
    for (const w of words) {
      if (e.keywords.includes(w)) score += 4;
      else if (e.title.toLowerCase().includes(w)) score += 3;
      else if (hay.includes(w)) score += 1;
    }
    return { e, score };
  }).filter(x => x.score > 0).sort((a, b) => b.score - a.score);
  return scored.slice(0, maxEntries).map(x => x.e);
}

function knowledgeBlock(entries) {
  if (!entries.length) return "";
  return "\n\nSITE KNOWLEDGE (ground your answers in this — quote or paraphrase, never invent):\n" +
    entries.map(e => `- [${e.title}] ${e.body}`).join("\n");
}

// --------------------------------------------------- availability adapter ---
async function getAvailability(env) {
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
        await kvPut(env, "DB_CACHE", "cache:availability", JSON.stringify(data), AVAIL_STALE_TTL_S);
        return { source: "live", stale: false, ...data };
      }
    } catch { /* fall through to cache */ }
  }
  const cached = await kvGet(env, "DB_CACHE", "cache:availability");
  if (cached) {
    const data = JSON.parse(cached);
    const age = Date.now() - Date.parse(data.cached_at || 0);
    if (!Number.isNaN(age) && age < AVAIL_TTL_S * 1000) return { source: "cache", stale: false, ...data };
    return { source: "cache", stale: true, ...data };
  }
  return null;
}

// ------------------------------------------------------- lead capture -------
async function storeLead(env, lead) {
  const record = {
    id: lead.id || uuid(),
    name: lead.name || null,
    firstName: lead.firstName || null, lastName: lead.lastName || null,
    email: lead.email || null, phone: lead.phone || null,
    company: lead.company || null,
    need: lead.need || null,
    serviceInterest: lead.serviceInterest || null,
    mailingList: lead.mailingList === true || lead.mailingList === "yes",
    pageUrl: lead.pageUrl || null, persona: lead.persona || null,
    summary: lead.summary || null, conversation: lead.conversation || null,
    ts: nowISO(), synced: false, attempts: 0, lastAttempt: null, type: "lead",
  };
  const ok = await kvPut(env, "DB_LEADS", `outbox:${todayUTC()}:${record.id}`, JSON.stringify(record));
  await kvPut(env, "DB_LEADS", `lead:${record.id}`, JSON.stringify(record));
  // Mailing-list bucket: separate key prefix so the list is pullable on its own.
  if (record.mailingList) {
    await kvPut(env, "DB_LEADS", `mailinglist:${record.id}`, JSON.stringify({
      id: record.id, name: record.name, firstName: record.firstName,
      lastName: record.lastName, email: record.email, phone: record.phone,
      serviceInterest: record.serviceInterest, ts: record.ts,
    }));
  }
  record._persisted = ok;
  return record;
}

async function storeHold(env, hold) {
  const record = {
    id: hold.id || uuid(),
    name: hold.name || null, email: hold.email || null,
    requestedTime: hold.requestedTime || null, slot: hold.slot || null,
    pageUrl: hold.pageUrl || null, persona: hold.persona || null,
    summary: hold.summary || null, ts: nowISO(),
    synced: false, attempts: 0, lastAttempt: null,
    type: "tentative_hold", status: "tentative",
  };
  await kvPut(env, "DB_LEADS", `outbox:${todayUTC()}:${record.id}`, JSON.stringify(record));
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
  if (!env.DB_LEADS) return { skipped: "DB_LEADS binding missing" };
  const results = { delivered: 0, failed: 0, skipped: 0 };
  for (let i = 0; i < SYNC_LOOKBACK_DAYS; i++) {
    const day = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    let cursor = undefined;
    do {
      const page = await env.DB_LEADS.list({ prefix: `outbox:${day}:`, cursor });
      for (const { name } of page.keys) {
        const raw = await env.DB_LEADS.get(name);
        if (!raw) continue;
        const lead = JSON.parse(raw);
        if (lead.synced || !backoffDue(lead)) { results.skipped++; continue; }
        lead.attempts = (lead.attempts || 0) + 1;
        lead.lastAttempt = nowISO();
        try {
          const ctrl = new AbortController();
          const t = setTimeout(() => ctrl.abort(), 15000);
          const r = await fetch(intake, {
            method: "POST",
            headers: { "content-type": "application/json", Authorization: `Bearer ${env.CRM_API_KEY || ""}` },
            body: JSON.stringify(lead), signal: ctrl.signal,
          });
          clearTimeout(t);
          if (r.status >= 200 && r.status < 300) {
            lead.synced = true;
            await env.DB_LEADS.put(name, JSON.stringify(lead));
            await env.DB_LEADS.put(`lead:${lead.id}`, JSON.stringify(lead));
            results.delivered++;
          } else { await env.DB_LEADS.put(name, JSON.stringify(lead)); results.failed++; }
        } catch { await env.DB_LEADS.put(name, JSON.stringify(lead)); results.failed++; }
      }
      cursor = page.list_complete ? undefined : page.cursor;
    } while (cursor);
  }
  return results;
}

// ---------------------------------------------------------- chat handling ---
// NOTE (2026-10-01): Workers AI function-calling ("tools") was REMOVED.
// The fp8 Llama-3.1 quant cannot do tool calls reliably — it emitted
// meta-chatter about "tool call responses" instead of conversing, and even
// tried capture_lead with garbage args ("name": "Hello, my name is").
// Lead capture is now a parseable [[LEAD_CAPTURE ...]] tag the model appends;
// the server strips it, validates it, and stores the lead. The tag carries
// firstName/lastName/email/phone/company/need/serviceInterest/mailingList.
// If the model re-emits the tag with updated details (added phone, mailing-list
// answer), the server MERGES into the existing record — never duplicates.
// Consented mailing-list signups also land under a mailinglist: key prefix
// (the mailing-list bucket). A reply sanitizer catches any residual tool-call
// meta-talk and substitutes a clean greeting.

async function getPersona(env, sessionId) {
  const skey = `session:${sessionId}`;
  const existing = (await kvGet(env, "DB_CACHE", skey)) || memSessions.get(skey);
  if (existing) {
    const s = JSON.parse(existing);
    return { persona: PERSONAS[s.personaIdx] || PERSONAS[0], newSession: false, skey, s };
  }
  let n = parseInt((await kvGet(env, "DB_CACHE", "persona:counter")) || "0", 10) || 0;
  n += 1;
  const kvOk = await kvPut(env, "DB_CACHE", "persona:counter", String(n));
  if (!kvOk) { // in-memory fallback: rotate within this isolate
    const cur = (memSessions.get("__counter") || 0) + 1;
    memSessions.set("__counter", cur);
    n = cur;
  }
  const personaIdx = n % PERSONAS.length;
  const s = { personaIdx, createdAt: nowISO(), turns: [] };
  const saved = await kvPut(env, "DB_CACHE", skey, JSON.stringify(s), SESSION_TTL_S);
  if (!saved) memSessions.set(skey, JSON.stringify(s));
  return { persona: PERSONAS[personaIdx], newSession: true, skey, s };
}

function systemPrompt(persona, avail, pageUrl, knowledge) {
  let availNote;
  if (avail && avail.slots && avail.slots.length) {
    const labels = avail.slots.slice(0, 6).map(s => s.label || s.start).join("; ");
    availNote = (avail.stale ? "(Note: these slots are from a cached calendar — offer them, and if the visitor picks one, save it as a TENTATIVE hold.) " : "") +
      `David's open times right now: ${labels}. You may offer these.`;
  } else if (avail && avail.stale) {
    availNote = "The calendar is temporarily offline, so no live slots are visible. Offer the self-serve booking link below.";
  } else {
    availNote = "No calendar slots are available right now. Offer the self-serve booking link below.";
  }
  return [
    `You are ${persona.name}, an AI virtual assistant for Dead Brands, LLC — never a human, never David, never a sales rep. Say so if asked.`,
    `Personality: ${persona.style}`,
    `FIRST MESSAGE RULE: on the very first message of a conversation, begin your reply by introducing yourself, e.g. "Hey! I'm ${persona.name}, an AI assistant here at Dead Brands." Then answer naturally.`,
    `KNOWLEDGE IS YOUR SOURCE OF TRUTH: the knowledge block below contains verified facts about Dead Brands' services, pricing policy, booking, and contact info. When a knowledge entry covers the visitor's question, base your answer on it. NEVER deflect a visitor to a third-party/vendor website when a knowledge entry answers the question.`,
    `PRICING RULE: Dead Brands does not publish fixed pricing — every engagement is scoped. When asked about pricing or cost, say so plainly and point to the free consult booking link. Never invent a price and never send visitors to vendor sites for pricing.`,
    `Company context: ${SERVICES_BLURB}`,
    `Team hand-off: the warm sales rep is "Deacon from our team" — route warm hand-offs to him by name and role.`,
    `Self-serve booking link (always works): ${APOLLO_LINK} — offer it freely whenever someone wants time with David.`,
    `Availability: ${availNote}`,
    `BOOKING HONESTY RULE (critical): you may NEVER fake-confirm a booking. If the visitor gives you a specific date/time they want, note it in the LEAD tag's need field and say: "I've held [time] for you — David's team will confirm it shortly." If they did NOT give a specific time, never claim anything was held or booked — just offer the booking link.`,
    `EMERGENCY RULE: if the visitor describes something URGENT — their system is down, production is halted, they say emergency / ASAP / crisis / critical / "need help now" — skip the booking link and give them David's direct line immediately: "You can call or text David directly at +1 (619) 779-2842 — he's typically available for texts until 7 PM ET daily." Urgent people get the number, not a form.`,
    `ANSWER FIRST: always answer the visitor's question helpfully BEFORE asking anything else. Never demand contact details before being useful. Ask conversationally, one question at a time.`,
    `PERSONALITY: you are the friendly face of Dead Brands — warm, personable, a little playful, never stiff or robotic. Use the visitor's first name once you know it. Keep replies short and conversational — 1-3 short sentences, never walls of text. Talk like a helpful friend, not a form.`,
    `FOLLOW-UPS: after answering a question, always close with a natural follow-up so the conversation keeps flowing — e.g. "Does that help, or do you want me to dig deeper?", "Want me to go into more detail on any of that?", "Anything else I can help with on this?"`,
    `GETTING TO KNOW THEM (gradual, never an interrogation): your goal is to learn the visitor's first name, last name, email, and phone number — but you EARN each detail by being useful first. Ask one thing at a time, in natural moments: after answering their question ("By the way, I'm ${persona.name} — what's your name?"), when offering to send info ("I can send you the details — what's the best email?"), when booking ("What's the best number in case we need to reach you?"). If they dodge a question, let it go and try again later — never badger.`,
    `MAILING LIST: once you have their email, ask if they'd like to join the Dead Brands mailing list — ERP tips, Odoo and SAP Business One news, new Shark Bite Biz podcast episodes. Record mailingList="yes" or mailingList="no" in the lead tag. Never assume consent from the email alone.`,
    `SERVICE INTEREST: notice what the conversation is really about and record it in the lead tag's serviceInterest field. Use one of: odoo, sap-business-one, erp-selection, erp-implementation, ai-automation, sales, marketing, business-development, podcast, merch, general. Pick the closest match.`,
    `LEAD CAPTURE PROTOCOL (the ONLY way you record contact details — there are no tools or function calls):`,
    `When the visitor has actually told you their name AND email address, append this tag on its own line at the very end of your reply:`,
    `[[LEAD_CAPTURE firstName="their first name" lastName="their last name" name="their full name" email="their@email.com" phone="their phone number" company="their company" need="what they need in 1-2 sentences" serviceInterest="odoo|sap-business-one|..." mailingList="yes|no"]]`,
    `Rules: use ONLY details they really shared (leave unknown fields empty, e.g. phone=""). NEVER emit the tag with an empty name or email. If they update a detail later (new email, added phone, mailing list answer), emit the tag again with the corrected fields — the server merges it. Emit it at most once per conversation unless details changed. NEVER talk about tools, function calls, tool responses, or JSON in your visible reply — just converse naturally; the tag is machine-readable and will be stripped before the visitor sees it.`,
    `Guardrails: NEVER invent prices, timelines, client names, statistics, or David's credentials. If the site knowledge below doesn't answer it, offer the free consult booking link (${APOLLO_LINK}) or Deacon's follow-up. Keep replies short and conversational — 1-3 short sentences, never walls of text.`,
    pageUrl ? `The visitor is on: ${pageUrl}` : "",
    knowledge,
  ].join("\n");
}

// Strip the machine-readable [[LEAD_CAPTURE ...]] tag; validate its fields.
// The tag is stripped EVERYWHERE it appears (not just at the end) — a leaked
// tag in user-visible chat is a hard failure.
function parseLeadTag(text) {
  const t = String(text || "");
  const re = /\[\[LEAD_CAPTURE\s+([^\]]*)\]\]/g;
  let m, last = null;
  while ((m = re.exec(t))) last = m;
  if (!last) return { clean: t, attrs: null };
  const attrs = {};
  const attrRe = /(\w+)="([^"]*)"/g;
  let am;
  while ((am = attrRe.exec(last[1]))) attrs[am[1]] = am[2];
  const clean = t.replace(/\[\[LEAD_CAPTURE\s+[^\]]*\]\]/g, "").replace(/[ \t]+/g, " ").trim();
  return { clean, attrs };
}
function validLead(a) {
  return !!a && !!a.name && a.name.trim().length > 1 &&
    !!a.email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(a.email.trim());
}
// Deterministic server-side lead extraction — fallback for when the model
// doesn't emit the [[LEAD_CAPTURE]] tag. Scans the VISITOR's own message
// only; never the model's output.
const EMAIL_RE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
const PHONE_RE = /(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}/;
const NAME_PATTERNS = [
  /(?:my name is|i am|i'm|this is|call me)\s+([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){0,2})/i,
  /(?:^|[\s,])name\s*[:=]\s*([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){0,2})/i,
];
const COMPANY_RE = /(?:company(?:\s+is)?|work for|work at|with)\s+([A-Z][\w&'.-]+(?:\s+[\w&'.-]+){0,2})/i;
function splitName(full) {
  const parts = String(full || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length <= 1) return { firstName: parts[0] || "", lastName: "" };
  return { firstName: parts[0], lastName: parts.slice(1).join(" ") };
}
function extractLeadFromUserText(text) {
  const t = String(text || "");
  const em = t.match(EMAIL_RE);
  if (!em) return null;
  let name = null;
  for (const re of NAME_PATTERNS) {
    const m = t.match(re);
    if (m && m[1] && m[1].trim().length > 1) { name = m[1].trim(); break; }
  }
  if (!name) return null;
  // Guard against capturing the email local-part as a name.
  if (name.toLowerCase().replace(/[^a-z]/g, "") === em[0].split("@")[0].toLowerCase().replace(/[^a-z]/g, "")) return null;
  const cm = t.match(COMPANY_RE);
  const pm = t.match(PHONE_RE);
  const { firstName, lastName } = splitName(name);
  return {
    name, firstName, lastName, email: em[0].trim(),
    phone: pm ? pm[0].trim() : "",
    company: cm && cm[1] ? cm[1].trim() : "",
  };
}

// Merge corrected/added details into an already-captured lead (the model may
// re-emit the tag when the visitor adds a phone number or mailing-list answer).
// Never creates a duplicate record for the same session lead.
async function mergeLead(env, id, fields) {
  const raw = await kvGet(env, "DB_LEADS", `lead:${id}`);
  if (!raw) return null;
  const rec = JSON.parse(raw);
  const setIf = (k, v) => { if (v !== undefined && v !== null && String(v).trim() !== "") rec[k] = String(v).trim(); };
  setIf("name", fields.name); setIf("firstName", fields.firstName);
  setIf("lastName", fields.lastName); setIf("email", fields.email);
  setIf("phone", fields.phone); setIf("company", fields.company);
  setIf("need", fields.need); setIf("serviceInterest", fields.serviceInterest);
  if (fields.mailingList === "yes") rec.mailingList = true;
  else if (fields.mailingList === "no") rec.mailingList = false;
  if (!rec.firstName && rec.name) { const p = splitName(rec.name); rec.firstName = p.firstName; rec.lastName = rec.lastName || p.lastName; }
  const body = JSON.stringify(rec);
  await kvPut(env, "DB_LEADS", `lead:${id}`, body);
  await kvPut(env, "DB_LEADS", `outbox:${rec.ts.slice(0, 10)}:${id}`, body);
  if (rec.mailingList) {
    await kvPut(env, "DB_LEADS", `mailinglist:${id}`, JSON.stringify({
      id: rec.id, name: rec.name, firstName: rec.firstName,
      lastName: rec.lastName, email: rec.email, phone: rec.phone,
      serviceInterest: rec.serviceInterest, ts: rec.ts,
    }));
  }
  return rec;
}

function tagToLeadFields(attrs) {
  const a = attrs || {};
  const fields = {
    name: (a.name || "").trim(), email: (a.email || "").trim(),
    firstName: (a.firstName || "").trim(), lastName: (a.lastName || "").trim(),
    phone: (a.phone || "").trim(), company: (a.company || "").trim(),
    need: (a.need || "").trim() || null,
    serviceInterest: (a.serviceInterest || "").trim() || null,
    mailingList: (a.mailingList || "").trim().toLowerCase() || null,
  };
  if (!fields.firstName && fields.name) {
    const p = splitName(fields.name);
    fields.firstName = p.firstName; fields.lastName = fields.lastName || p.lastName;
  }
  return fields;
}

function appendLeadConfirmation(reply, fields) {
  const who = fields.firstName || fields.name || "there";
  const ack = `Thanks, ${who} — I've got your details down and David's team will follow up!`;
  const base = String(reply || "").trim();
  if (!base) return ack;
  const low = base.toLowerCase();
  if (low.includes("follow up") || low.includes("got your details") || low.includes("got it")) return base;
  return base + " " + ack;
}

// The fp8 model occasionally emits meta-chatter about tool/function calls
// instead of a real reply. Never let that reach a visitor.
function looksBroken(reply) {
  if (!reply || !String(reply).trim()) return true;
  const t = String(reply);
  return /tool[\s_-]*calls?/i.test(t) && /json|function|format|provide|response/i.test(t);
}

async function handleChat(env, req, body) {
  const { sessionId, message, pageUrl } = body || {};
  if (!sessionId || !message) return json(env, req, { error: "sessionId and message required" }, 400);
  if (String(message).length > 4000) return json(env, req, { error: "message too long" }, 400);
  if (!env.AI) return json(env, req, {
    reply: "I'm having a quick technical moment — want to grab time directly? Here's David's booking link: " + APOLLO_LINK,
    persona: "Nova", fallback: true, error: "AI binding missing",
  });

  const { persona, skey, s } = await getPersona(env, String(sessionId));
  const avail = await getAvailability(env);
  const knowledge = knowledgeBlock(findKnowledge(message));

  const history = (s.turns || []).slice(-8).flatMap(t => [
    { role: "user", content: t.u },
    { role: "assistant", content: t.a },
  ]);
  const messages = [
    { role: "system", content: systemPrompt(persona, avail, pageUrl, knowledge) },
    ...history,
    { role: "user", content: String(message) },
  ];

  let ai;
  try {
    ai = await env.AI.run(MODEL, { messages, max_tokens: 300, temperature: 0.7 });
  } catch (e) {
    return json(env, req, {
      reply: "I'm having a quick technical moment — want to grab time directly? Here's David's booking link: " + APOLLO_LINK,
      persona: persona.name, fallback: true,
    });
  }

  let reply = "";
  const actions = [];
  const raw = ai && ai.response ? String(ai.response) : "";
  const isFirstTurn = !(s.turns && s.turns.length);
  let leadCapturedId = s.leadCaptured || null;
  const convForLead = () => [...history, { role: "user", content: String(message) }]
    .map(m => `${m.role}: ${m.content}`).join("\n").slice(-3000);
  if (looksBroken(raw)) {
    // Model emitted tool-call meta-chatter (or nothing) — substitute a clean,
    // in-character greeting instead of leaking internals to the visitor.
    reply = `Hey! I'm ${persona.name}, one of the AI assistants here at Dead Brands. What can I help you with today?`;
  } else {
    const { clean, attrs } = parseLeadTag(raw);
    reply = clean || `Hey! I'm ${persona.name}, one of the AI assistants here at Dead Brands. What can I help you with today?`;
    if (attrs && validLead(attrs)) {
      const fields = tagToLeadFields(attrs);
      if (leadCapturedId) {
        // Visitor updated details (added phone, answered mailing list, etc.)
        // — merge into the existing record, never duplicate.
        const updated = await mergeLead(env, leadCapturedId, fields);
        if (updated) actions.push({ type: "lead_updated", leadId: leadCapturedId, persisted: true });
      } else {
        const lead = await storeLead(env, {
          ...fields,
          mailingList: fields.mailingList === "yes",
          pageUrl: pageUrl || null, persona: persona.name,
          summary: fields.need, conversation: convForLead(),
        });
        leadCapturedId = lead.id;
        reply = appendLeadConfirmation(reply, fields);
        actions.push({ type: "lead_captured", leadId: lead.id, persisted: lead._persisted });
      }
    } else if (!leadCapturedId) {
      // Deterministic fallback: the visitor may have typed their name+email
      // even though the model didn't emit the tag. Scan the visitor's own
      // message — never trust the model for this.
      const fb = extractLeadFromUserText(message);
      if (fb && validLead(fb)) {
        const firstTopic = (s.turns && s.turns[0] && s.turns[0].u) || String(message);
        const lead = await storeLead(env, {
          name: fb.name, firstName: fb.firstName, lastName: fb.lastName,
          email: fb.email, phone: fb.phone || null,
          company: fb.company || null,
          need: firstTopic.slice(0, 200),
          pageUrl: pageUrl || null, persona: persona.name,
          summary: firstTopic.slice(0, 200), conversation: convForLead(),
        });
        leadCapturedId = lead.id;
        actions.push({ type: "lead_captured", leadId: lead.id, persisted: lead._persisted, via: "server_fallback" });
      }
    }
    // Invalid/empty tag and no fallback match: no lead stored, conversation continues.
  }

  // First-turn identity: make sure the visitor hears the persona's name.
  if (isFirstTurn && !new RegExp(persona.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i").test(reply)) {
    reply = `Hey! I'm ${persona.name}, an AI assistant here at Dead Brands. ` + reply;
  }

  if (leadCapturedId) s.leadCaptured = leadCapturedId;

  s.turns = [...(s.turns || []), { u: String(message).slice(0, 500), a: reply.slice(0, 500) }].slice(-10);
  const saved = await kvPut(env, "DB_CACHE", skey, JSON.stringify(s), SESSION_TTL_S);
  if (!saved) memSessions.set(skey, JSON.stringify(s));

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
        ok: true, service: "deadbrands-chatbot", model: MODEL,
        knowledge_entries: KNOWLEDGE.length,
        kv_leads: !!env.DB_LEADS, kv_cache: !!env.DB_CACHE, ai: !!env.AI,
        crm_intake_configured: !!env.CRM_LEAD_INTAKE_URL,
        availability_configured: !!env.CRM_AVAILABILITY_URL,
        ts: nowISO(),
      });
    }
    if (req.method === "POST" && url.pathname === "/chat") {
      let body;
      try { body = await req.json(); }
      catch { return json(env, req, { error: "invalid JSON" }, 400); }
      return handleChat(env, req, body);
    }
    if (req.method === "POST" && url.pathname === "/lead") {
      let body;
      try { body = await req.json(); }
      catch { return json(env, req, { error: "invalid JSON" }, 400); }
      if (!body.name || !body.email) return json(env, req, { error: "name and email required" }, 400);
      const lead = await storeLead(env, body);
      return json(env, req, { ok: true, leadId: lead.id, persisted: lead._persisted });
    }
    if (req.method === "POST" && url.pathname === "/hold") {
      let body;
      try { body = await req.json(); }
      catch { return json(env, req, { error: "invalid JSON" }, 400); }
      if (!body.requestedTime) return json(env, req, { error: "requestedTime required" }, 400);
      const hold = await storeHold(env, body);
      return json(env, req, { ok: true, holdId: hold.id, status: "tentative", message: "Held tentatively — the team will confirm shortly." });
    }
    return json(env, req, { error: "not found" }, 404);
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(syncOutbox(env));
  },
};
