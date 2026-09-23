/* Dead Brands Quaint outbound click tracker — v1 (2026-09-23).
 *
 * Loaded ONLY by consent.js enableTracking() — this file never runs unless
 * the visitor clicked "Accept" on the cookie banner. We promised no tracking
 * without consent; this file is the proof.
 *
 * Listens for clicks on any quaintbusiness.com link and reports them to our
 * first-party Apps Script beacon as action:"quaint_click" with:
 *   eid (unique event id — the server dedupes on it, so retries and the
 *        sendBeacon duplicate can never double-count a click),
 *   page, link_url, utm_content/utm_source/utm_medium/utm_campaign parsed
 *   from the link, and a random per-tab session id. No PII, ever.
 *
 * Delivery: navigator.sendBeacon fires immediately (survives the navigation
 * to quaintbusiness.com); a localStorage buffer covers failures and flushes
 * on the next consenting page load. Nothing is lost, nothing is doubled.
 */
(function () {
  "use strict";
  var ENDPOINT = "https://script.google.com/macros/s/AKfycbwnOSosh68et8uOajfznNiDPSvVFFJjE-EZ0yNvNTr_uPsWjP_jj0ZNJnJfDJzb6gMm/exec";
  var BUF_KEY = "dsa_qcbuf";
  var MAX_BUF = 200;

  function param(url, k) {
    var m = new RegExp("[?&]" + k + "=([^&#]*)").exec(url);
    return m ? decodeURIComponent(m[1].replace(/\+/g, " ")) : "";
  }

  function sid() {
    try {
      var s = window.sessionStorage.getItem("dsa_sid");
      if (!s) {
        s = Math.random().toString(36).slice(2) + Date.now().toString(36);
        window.sessionStorage.setItem("dsa_sid", s);
      }
      return String(s).slice(0, 40);
    } catch (e) { return "nosession"; }
  }

  function eid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  function loadBuf() {
    try {
      var b = JSON.parse(window.localStorage.getItem(BUF_KEY) || "[]");
      return Array.isArray(b) ? b : [];
    } catch (e) { return []; }
  }
  function saveBuf(b) {
    try { window.localStorage.setItem(BUF_KEY, JSON.stringify(b)); } catch (e) {}
  }

  function beacon(ev) {
    // Fire-and-forget: survives page unload. The server dedupes on eid.
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(ENDPOINT,
          new Blob([JSON.stringify(ev)], { type: "text/plain;charset=utf-8" }));
      }
    } catch (e) {}
  }

  function flush() {
    var buf = loadBuf();
    if (!buf.length) return;
    var ev = buf[0];
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("POST", ENDPOINT, true);
      xhr.setRequestHeader("Content-Type", "text/plain;charset=utf-8");
      xhr.timeout = 8000;
      var done = false;
      var next = function (ok) {
        if (done) return; done = true;
        var b = loadBuf();
        // Remove only if it's still the event we just sent (a newer click
        // may have been buffered while the request was in flight).
        if (ok && b.length && b[0].eid === ev.eid) b.shift();
        saveBuf(b);
        if (b.length) setTimeout(flush, 500);
      };
      xhr.onload = function () { next(xhr.status >= 200 && xhr.status < 300); };
      xhr.onerror = function () { next(false); };
      xhr.ontimeout = function () { next(false); };
      xhr.send(JSON.stringify(ev));
    } catch (e) { /* stays buffered for next time */ }
  }

  function trackClick(a) {
    var href = a.getAttribute("href") || "";
    if (href.indexOf("quaintbusiness.com") === -1) return;
    var ev = {
      action: "quaint_click",
      eid: eid(),
      page: window.location.pathname.slice(0, 300),
      link_url: href.slice(0, 500),
      utm_content: param(href, "utm_content").slice(0, 120),
      utm_source: param(href, "utm_source").slice(0, 60),
      utm_medium: param(href, "utm_medium").slice(0, 60),
      utm_campaign: param(href, "utm_campaign").slice(0, 120),
      sid: sid()
    };
    var b = loadBuf();
    b.push(ev);
    while (b.length > MAX_BUF) b.shift();
    saveBuf(b);
    beacon(ev);   // immediate attempt — survives navigation away
    flush();      // opportunistic XHR for anything older in the buffer
  }

  document.addEventListener("click", function (e) {
    var t = e.target;
    var a = (t && t.closest) ? t.closest('a[href*="quaintbusiness.com"]') : null;
    if (a) { try { trackClick(a); } catch (err) {} }
  }, true);

  // Consent was already granted when this file loaded — flush any backlog.
  flush();
})();
