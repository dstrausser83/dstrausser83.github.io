/* Dead Brands lead-chatbot widget — v1 (2026-09-24).
 *
 * Embeddable chat widget for deadbrands.co. Calls the Cloudflare Worker
 * (workers/chatbot/). All lead storage and AI happen at the edge — this file
 * is pure UI.
 *
 * The parent deploy step adds:
 *   <link rel="stylesheet" href="/assets/css/chat.css">
 *   <script src="/assets/js/chat-widget.js" defer></script>
 * to the site template.
 */
(function () {
  "use strict";

  /* ------------------------------ config ------------------------------ */
  // TODO(parent): set to the deployed worker URL, e.g.
  // "https://deadbrands-chatbot.<account>.workers.dev"
  var WORKER_URL = ""; // <-- CONFIGURE ME

  var PROACTIVE_DELAY_MS = 60 * 1000; // greet after ~60 s on page
  var DISMISS_KEY = "db_chat_dismissed"; // sessionStorage — per-session dismissal

  /* ------------------------------ helpers ------------------------------ */
  function $(sel, root) {
    return (root || document).querySelector(sel);
  }
  function el(tag, cls, text) {
    var d = document.createElement(tag);
    if (cls) d.className = cls;
    if (text != null) d.textContent = text;
    return d;
  }
  function sessionId() {
    var s = null;
    try {
      s = sessionStorage.getItem("db_chat_sid");
    } catch (e) {}
    if (!s) {
      s =
        "s-" +
        Date.now().toString(36) +
        "-" +
        Math.random().toString(36).slice(2, 10);
      try {
        sessionStorage.setItem("db_chat_sid", s);
      } catch (e) {}
    }
    return s;
  }
  function dismissed() {
    try {
      return sessionStorage.getItem(DISMISS_KEY) === "1";
    } catch (e) {
      return false;
    }
  }
  function markDismissed() {
    try {
      sessionStorage.setItem(DISMISS_KEY, "1");
    } catch (e) {}
  }

  /* Linkify http(s) URLs + the Apollo booking link in bot replies. */
  function linkify(text) {
    var frag = document.createDocumentFragment();
    var re = /(https?:\/\/[^\s<>"')]+)/g;
    var last = 0,
      m;
    while ((m = re.exec(text))) {
      if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      var a = document.createElement("a");
      a.href = m[1];
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = /apollo\.io/.test(m[1]) ? "Book a free consult" : m[1];
      frag.appendChild(a);
      last = m.index + m[1].length;
    }
    frag.appendChild(document.createTextNode(text.slice(last)));
    return frag;
  }

  /* ------------------------------ widget ------------------------------ */
  if (!WORKER_URL) {
    // Worker not wired yet — stay silent, never break the page.
    return;
  }

  var state = { open: false, greeted: false, persona: null, busy: false };

  var launcher = el("button", "db-chat-launcher", "");
  launcher.setAttribute("aria-label", "Chat with our virtual assistant");
  launcher.innerHTML =
    '<svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">' +
    '<path fill="currentColor" d="M12 2C6.5 2 2 6 2 11c0 1.9.6 3.6 1.7 5L2 21l5.2-1.6c1.4.8 3 1.2 4.8 1.2 5.5 0 10-4 10-9S17.5 2 12 2z"/>' +
    "</svg>";
  document.body.appendChild(launcher);

  var panel = el("div", "db-chat-panel");
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "Chat with Dead Brands");
  panel.innerHTML =
    '<div class="db-chat-header">' +
    '<div class="db-chat-avatar" aria-hidden="true">AI</div>' +
    '<div class="db-chat-who"><strong class="db-chat-name">…</strong>' +
    '<span class="db-chat-sub">AI virtual assistant · Dead Brands</span></div>' +
    '<button class="db-chat-close" aria-label="Close chat">×</button>' +
    "</div>" +
    '<div class="db-chat-log" aria-live="polite"></div>' +
    '<div class="db-chat-typing" hidden><span></span><span></span><span></span></div>' +
    '<form class="db-chat-form">' +
    '<input class="db-chat-input" type="text" placeholder="Type your message…" ' +
    'aria-label="Type your message" autocomplete="off" maxlength="4000">' +
    '<button class="db-chat-send" type="submit" aria-label="Send">➤</button>' +
    "</form>";
  document.body.appendChild(panel);

  var log = $(".db-chat-log", panel);
  var typing = $(".db-chat-typing", panel);
  var form = $(".db-chat-form", panel);
  var input = $(".db-chat-input", panel);

  function scrollDown() {
    log.scrollTop = log.scrollHeight;
  }
  function addMsg(who, text) {
    var row = el("div", "db-chat-msg db-chat-" + who);
    var bubble = el("div", "db-chat-bubble");
    if (who === "bot") bubble.appendChild(linkify(text));
    else bubble.textContent = text;
    row.appendChild(bubble);
    log.appendChild(row);
    scrollDown();
  }
  function setPersona(name) {
    if (name && name !== state.persona) {
      state.persona = name;
      $(".db-chat-name", panel).textContent = name;
    }
  }

  async function sendToWorker(text) {
    var res = await fetch(WORKER_URL + "/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        sessionId: sessionId(),
        message: text,
        pageUrl: location.href,
      }),
    });
    if (!res.ok) throw new Error("worker " + res.status);
    return res.json();
  }

  async function botTurn(text) {
    if (state.busy) return;
    state.busy = true;
    typing.hidden = false;
    try {
      var data = await sendToWorker(text);
      typing.hidden = true;
      setPersona(data.persona);
      addMsg("bot", data.reply || "How can I help?");
    } catch (e) {
      typing.hidden = true;
      addMsg(
        "bot",
        "I'm having a quick technical moment — want to grab time directly? " +
          "https://app.apollo.io/#/meet/david_strausser_175"
      );
    }
    state.busy = false;
    scrollDown();
  }

  function open() {
    state.open = true;
    panel.classList.add("db-chat-open");
    launcher.classList.add("db-chat-hidden");
    if (!state.greeted) {
      state.greeted = true;
      botTurn("Please greet me and introduce yourself as my virtual assistant.");
    } else {
      input.focus();
    }
  }
  function close() {
    state.open = false;
    panel.classList.remove("db-chat-open");
    launcher.classList.remove("db-chat-hidden");
  }

  launcher.addEventListener("click", open);
  $(".db-chat-close", panel).addEventListener("click", function () {
    markDismissed();
    close();
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var v = input.value.trim();
    if (!v) return;
    input.value = "";
    addMsg("user", v);
    botTurn(v);
  });

  /* Proactive greeting: ~60 s after load, once per session, dismissible. */
  setTimeout(function () {
    if (!dismissed() && !state.open && !state.greeted) open();
  }, PROACTIVE_DELAY_MS);

  /* Keep clear of the cookie banner when it is visible. */
  function dodgeBanner() {
    var banner = document.getElementById("db-cookie-banner");
    var extra = 0;
    if (banner && banner.offsetParent !== null) {
      extra = banner.getBoundingClientRect().height + 12;
    }
    document.documentElement.style.setProperty(
      "--db-chat-bottom-offset",
      extra + "px"
    );
  }
  dodgeBanner();
  setInterval(dodgeBanner, 1500);
})();
