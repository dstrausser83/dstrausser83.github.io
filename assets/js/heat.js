/* Dead Brands first-party heatmap tracker — v1 (2026-09-26).
 * Loaded ONLY after cookie consent (see consent.js enableTracking()).
 * Records anonymous click positions + scroll depth per page and beacons
 * them to our own Cloudflare Worker. No cookies, no fingerprinting,
 * no personal data — aggregate behavior only, powers the Portal heatmap. */
(function () {
  "use strict";
  var ENDPOINT = "https://db-heat.dstrausser83.workers.dev/collect";
  var queue = [];
  var maxDepth = 0;
  var flushed = false;

  function docHeight() {
    return Math.max(
      document.documentElement.scrollHeight,
      document.body ? document.body.scrollHeight : 0,
      1
    );
  }

  function describe(el) {
    if (!el || !el.tagName) return "?";
    var tag = el.tagName.toLowerCase();
    var parts = [tag];
    if (el.id) parts.push("#" + el.id);
    else if (el.className && typeof el.className === "string") {
      var cls = el.className.trim().split(/\s+/).slice(0, 2).join(".");
      if (cls) parts.push("." + cls);
    }
    var text = (el.innerText || el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 40);
    if (text && !/^[<>]/.test(text)) parts.push('"' + text + '"');
    if (tag === "a" && el.getAttribute("href")) {
      var href = el.getAttribute("href");
      if (/^(https?:|mailto:)/.test(href)) parts.push("-> " + href.slice(0, 60));
      else parts.push("-> " + href.slice(0, 40));
    }
    return parts.join("");
  }

  function flush() {
    if (flushed || !queue.length) return;
    flushed = true;
    var payload = JSON.stringify({
      page: location.pathname,
      events: queue.splice(0, queue.length),
      scroll: maxDepth
    });
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(ENDPOINT, payload);
      } else {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", ENDPOINT, true);
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.send(payload);
      }
    } catch (e) { /* tracker must never break the page */ }
    flushed = false;
  }

  document.addEventListener("click", function (e) {
    try {
      var t = e.target;
      var el = (t && t.closest) ? (t.closest("a,button") || t) : t;
      queue.push({
        t: "c",
        x: Math.min(1, Math.max(0, e.clientX / window.innerWidth)),
        y: Math.min(1, Math.max(0, (e.clientY + window.scrollY) / docHeight())),
        el: describe(el)
      });
      if (queue.length >= 12) flush();
    } catch (err) { /* ignore */ }
  }, { passive: true });

  var ticking = false;
  window.addEventListener("scroll", function () {
    if (ticking) return;
    ticking = true;
    setTimeout(function () {
      ticking = false;
      try {
        var depth = (window.scrollY + window.innerHeight) / docHeight();
        if (depth > maxDepth) maxDepth = Math.min(1, depth);
      } catch (e) { /* ignore */ }
    }, 300);
  }, { passive: true });

  window.addEventListener("pagehide", flush);
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") flush();
  });
  setInterval(flush, 15000);
})();
