/* Dead Brands cookie consent — v1 (2026-09-23).
 * No tracking loads until the visitor accepts. Choice is stored in
 * localStorage ("db_cookie_consent" = "accepted" | "declined").
 * Accept -> loads GA4 (gtag.js) + our first-party pageview beacon.
 * Decline -> neither loads. The banner can be re-opened any time via
 * window.DBConsent.show() (footer "Cookie settings" link).
 * No cookies are set by this file itself beyond the visitor's own choice. */
(function () {
  "use strict";
  var KEY = "db_cookie_consent";
  var GA_ID = "G-LDWNV8CVJ4";
  /* Microsoft Clarity (free heatmaps + session recordings).
   * Project: Dead Brands / deadbrands.co — consent-gated, loads only
   * after the visitor accepts the cookie banner. */
  var CLARITY_ID = "yohr5k9nr4";
  /* RB2B visitor identification (free tier: 7-day full trial, then 150
   * company-level resolutions/mo). Loads only after cookie accept.
   * Pixel verbatim from RB2B signup 2026-09-26. Alerts -> #website-visitors. */
  var RB2B_KEY = "LNKLDHJ3V3OJ";
  /* Leadfeeder (Dealfront) company identification — free Lite plan
   * (last 100 companies/mo, 7-day history). Consent-gated like the rest. */
  var LEADFEEDER_KEY = "p1e024B0Vx98GB6d";

  function loadClarity() {
    if (!CLARITY_ID || CLARITY_ID.indexOf("REPLACE_WITH") === 0) return;
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1; t.src = "https://www.clarity.ms/tag/" + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
    })(window, document, "clarity", "script", CLARITY_ID);
  }

  function loadRB2B() {
    if (!RB2B_KEY) return;
    (function (key) {
      if (window.reb2b) return;
      window.reb2b = { loaded: true };
      var s = document.createElement("script");
      s.async = true;
      s.src = "https://ddwl4m2hdecbv.cloudfront.net/b/" + key + "/" + key + ".js.gz";
      var first = document.getElementsByTagName("script")[0];
      if (first && first.parentNode) first.parentNode.insertBefore(s, first);
      else document.head.appendChild(s);
    })(RB2B_KEY);
  }

  function loadLeadfeeder() {
    if (!LEADFEEDER_KEY) return;
    (function (ss, ex) {
      window.ldfdr = window.ldfdr || function () { (ldfdr._q = ldfdr._q || []).push([].slice.call(arguments)); };
      (function (d, s) {
        var fs = d.getElementsByTagName(s)[0];
        function ce(src) { var cs = d.createElement(s); cs.src = src; cs.async = 1; fs.parentNode.insertBefore(cs, fs); }
        ce("https://sc.lfeeder.com/lftracker_v1_" + ss + (ex ? "_" + ex : "") + ".js");
      })(document, "script");
    })(LEADFEEDER_KEY, null);
  }

  function getChoice() {
    try { return window.localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function setChoice(v) {
    try { window.localStorage.setItem(KEY, v); } catch (e) { /* storage blocked */ }
  }
  function siteRoot() {
    // consent.js lives in assets/js/ — derive the beacon URL from our own src
    // so this works at any page depth (/, /blog/, /blog/posts/).
    var src = "";
    try {
      var el = document.currentScript ||
        document.querySelector('script[src*="consent.js"]');
      src = el ? el.getAttribute("src") || "" : "";
    } catch (e) { /* ignore */ }
    return src.replace(/consent\.js.*$/, "");
  }
  function loadScript(url) {
    var s = document.createElement("script");
    s.src = url;
    s.async = true;
    document.head.appendChild(s);
  }

  function enableTracking() {
    // GA4 — consent mode already defaulted to denied in <head>; grant now.
    loadScript("https://www.googletagmanager.com/gtag/js?id=" + GA_ID);
    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag("js", new Date());
    gtag("consent", "update", {
      ad_storage: "granted",
      analytics_storage: "granted",
      ad_user_data: "granted",
      ad_personalization: "granted"
    });
    gtag("config", GA_ID);
    // First-party pageview beacon (our own Apps Script endpoint).
    loadScript(siteRoot() + "analytics.js");
    // Quaint outbound click tracker — same consent gate, same endpoint.
    loadScript(siteRoot() + "quaint-clicks.js");
    // Microsoft Clarity heatmaps — consent-gated like everything else.
    loadClarity();
    // First-party click/scroll heatmap tracker -> our own Cloudflare Worker.
    // Same consent gate: only loads after the visitor accepts.
    loadScript(siteRoot() + "heat.js");
    // B2B visitor identification: RB2B (Slack alerts) + Leadfeeder.
    // Consent-gated like everything else: nothing loads on Decline.
    loadRB2B();
    loadLeadfeeder();
  }

  function hideBanner() {
    var b = document.getElementById("db-cookie-banner");
    if (b && b.parentNode) b.parentNode.removeChild(b);
  }

  function choose(value) {
    setChoice(value);
    hideBanner();
    if (value === "accepted") enableTracking();
  }

  function cookiePolicyUrl() {
    // cookies.html lives at the site root.
    var root = siteRoot().replace(/assets\/js\/$/, "");
    return root + "cookies.html";
  }

  function showBanner() {
    if (document.getElementById("db-cookie-banner")) return;
    if (getChoice()) return; // already decided; use Cookie settings to change
    var bar = document.createElement("div");
    bar.id = "db-cookie-banner";
    bar.setAttribute("role", "dialog");
    bar.setAttribute("aria-live", "polite");
    bar.setAttribute("aria-label", "Cookie consent");
    bar.style.cssText = [
      "position:fixed", "left:0", "right:0", "bottom:0", "z-index:9999",
      "background:#141414", "color:#f5f5f5",
      "border-top:3px solid #e8b400",
      "padding:14px 18px", "font-family:inherit", "font-size:14px",
      "line-height:1.5", "box-shadow:0 -4px 24px rgba(0,0,0,.35)"
    ].join(";");
    var inner = document.createElement("div");
    inner.style.cssText = "max-width:960px;margin:0 auto;display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;";
    var msg = document.createElement("p");
    msg.style.cssText = "margin:0;flex:1 1 280px;";
    msg.innerHTML = "We use cookies to measure traffic and make the site better. " +
      'Accept for analytics, or decline and browse without tracking. <a id="db-cookie-link" href="' +
      cookiePolicyUrl() + '" style="color:#e8b400;text-decoration:underline;">Cookie policy</a>';
    var btns = document.createElement("div");
    btns.style.cssText = "display:flex;gap:10px;flex:0 0 auto;";
    var accept = document.createElement("button");
    accept.textContent = "Accept";
    accept.style.cssText = "background:#e8b400;color:#141414;border:none;border-radius:6px;padding:10px 22px;font-weight:700;cursor:pointer;font-size:14px;";
    accept.onclick = function () { choose("accepted"); };
    var decline = document.createElement("button");
    decline.textContent = "Decline";
    decline.style.cssText = "background:transparent;color:#f5f5f5;border:1px solid #777;border-radius:6px;padding:10px 22px;cursor:pointer;font-size:14px;";
    decline.onclick = function () { choose("declined"); };
    btns.appendChild(accept);
    btns.appendChild(decline);
    inner.appendChild(msg);
    inner.appendChild(btns);
    bar.appendChild(inner);
    document.body.appendChild(bar);
  }

  // Public API for the footer "Cookie settings" link.
  window.DBConsent = {
    show: function () {
      try { window.localStorage.removeItem(KEY); } catch (e) { /* ignore */ }
      showBanner();
    },
    choice: getChoice
  };

  function init() {
    if (getChoice() === "accepted") {
      enableTracking(); // returning visitor who already opted in
    } else if (!getChoice()) {
      showBanner();
    }
    // declined -> do nothing: no tracking scripts load at all
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
