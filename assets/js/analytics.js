/* Dead Brands first-party pageview analytics — v1 (2026-09-23).
 * Zero third parties, zero cookies, zero accounts. We own the data.
 * POSTs {action:"pageview", page, referrer, utm_*, sid} to our own Google
 * Apps Script web app. If the endpoint isn't updated yet (or is offline),
 * pageviews buffer in localStorage and flush on a later visit — no data lost.
 * sid = random per-tab session id (sessionStorage), no PII collected. */
(function () {
  "use strict";
  var ENDPOINT = "https://script.google.com/macros/s/AKfycbwnOSosh68et8uOajfznNiDPSvVFFJjE-EZ0yNvNTr_uPsWjP_jj0ZNJnJfDJzb6gMm/exec";
  var BUF_KEY = "dsa_pvbuf";
  var MAX_BUF = 100;

  function qs(k) {
    var m = new RegExp("[?&]" + k + "=([^&#]*)").exec(window.location.search);
    return m ? decodeURIComponent(m[1].replace(/\+/g, " ")) : "";
  }

  var sid;
  try {
    sid = window.sessionStorage.getItem("dsa_sid");
    if (!sid) {
      sid = Math.random().toString(36).slice(2) + Date.now().toString(36);
      window.sessionStorage.setItem("dsa_sid", sid);
    }
  } catch (e) { sid = "nosession"; }

  var pv = {
    action: "pageview",
    page: window.location.pathname.slice(0, 300),
    referrer: (window.document.referrer || "").slice(0, 300),
    utm_source: qs("utm_source").slice(0, 60),
    utm_medium: qs("utm_medium").slice(0, 60),
    utm_campaign: qs("utm_campaign").slice(0, 120),
    sid: String(sid).slice(0, 40)
  };

  function send(payload, cb) {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("POST", ENDPOINT, true);
      /* text/plain avoids a CORS preflight against the Apps Script web app. */
      xhr.setRequestHeader("Content-Type", "text/plain;charset=utf-8");
      xhr.timeout = 8000;
      xhr.onload = function () { cb(xhr.status >= 200 && xhr.status < 300); };
      xhr.onerror = function () { cb(false); };
      xhr.ontimeout = function () { cb(false); };
      xhr.send(JSON.stringify(payload));
    } catch (e) { cb(false); }
  }

  var buf = [];
  try { buf = JSON.parse(window.localStorage.getItem(BUF_KEY) || "[]"); } catch (e) { buf = []; }
  if (!Array.isArray(buf)) buf = [];
  buf.push(pv);
  while (buf.length > MAX_BUF) buf.shift();

  function persist() {
    try { window.localStorage.setItem(BUF_KEY, JSON.stringify(buf)); } catch (e) {}
  }

  /* Flush oldest-first; failures stay buffered for the next visit. */
  (function flush(i) {
    if (i >= buf.length) { persist(); return; }
    send(buf[i], function (ok) {
      if (ok) { buf.splice(i, 1); flush(i); }
      else { flush(i + 1); }
    });
  })(0);
})();
