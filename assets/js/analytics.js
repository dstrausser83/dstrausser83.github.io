/* Dead Brands first-party pageview beacon — v1 (2026-10-01).
 *
 * Loaded ONLY by consent.js enableTracking() — this file never runs unless
 * the visitor clicked "Accept" on the cookie banner. We promised no tracking
 * without consent; this file is the proof.
 *
 * Sends one action:"pageview" event per page load to our first-party
 * Apps Script beacon endpoint with:
 *   eid (unique event id — the server dedupes on it),
 *   page, referrer, and a random per-tab session id. No PII, ever.
 *
 * Delivery: navigator.sendBeacon (fire-and-forget, survives unload).
 * This resolves the dead analytics.js reference in consent.js.
 */
(function () {
  "use strict";
  var ENDPOINT = "https://script.google.com/macros/s/AKfycbwnOSosh68et8uOajfznNiDPSvVFFJjE-EZ0yNvNTr_uPsWjP_jj0ZNJnJfDJzb6gMm/exec";

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

  var ev = {
    action: "pageview",
    eid: eid(),
    page: window.location.pathname.slice(0, 300),
    referrer: (document.referrer || "").slice(0, 500),
    sid: sid()
  };

  try {
    if (navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT,
        new Blob([JSON.stringify(ev)], { type: "text/plain;charset=utf-8" }));
    }
  } catch (e) { /* fire-and-forget */ }
})();
