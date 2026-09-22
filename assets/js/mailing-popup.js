// Dead Brands mailing list popup — no frameworks.
//
// Behavior:
//   - Shows 5s after page load, auto-dismisses 10s later (10s visible),
//     unless the visitor interacts with it.
//   - Shows once per visitor (localStorage flag — not a cookie).
//   - Never shows again after a successful signup.
//   - ?preview=popup forces it open for design preview.
//
// Wiring:
//   1. David creates the Google Sheet + Apps Script web app (see mailing-list/SETUP.md).
//   2. Paste the web app URL into MAILING_LIST_ENDPOINT below.
//   3. Push. The popup activates on the next deploy.

(function () {
  "use strict";

  // >>> PASTE THE GOOGLE APPS SCRIPT WEB APP URL HERE <<<
  var MAILING_LIST_ENDPOINT = "https://script.google.com/macros/s/AKfycbwnOSosh68et8uOajfznNiDPSvVFFJjE-EZ0yNvNTr_uPsWjP_jj0ZNJnJfDJzb6gMm/exec";

  var SHOW_DELAY_MS = 5000;    // delay after landing before the popup appears
  var VISIBLE_MS = 10000;      // how long it stays up before auto-dismiss
  var LS_DISMISSED = "db_mailing_dismissed";
  var LS_SUBSCRIBED = "db_mailing_subscribed";

  var overlay = document.getElementById("mailing-popup");
  if (!overlay) return;
  var card = overlay.querySelector(".popup-card");
  var form = document.getElementById("popup-form");
  var closeBtn = document.getElementById("popup-close");
  var statusEl = document.getElementById("popup-status");
  var submitBtn = form.querySelector('button[type="submit"]');
  var preview = /[?&]preview=popup\b/.test(window.location.search);

  var interacted = false;
  var autoHideTimer = null;
  var lastFocused = null;

  function markInteracted() { interacted = true; }

  function open() {
    lastFocused = document.activeElement;
    overlay.hidden = false;
    // Force reflow so the transition plays.
    void overlay.offsetWidth;
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
    var first = form.querySelector('input[name="firstName"]');
    if (first) first.focus({ preventScroll: true });
    if (!preview) {
      autoHideTimer = setTimeout(function () {
        if (!interacted) dismiss();
      }, VISIBLE_MS);
    }
  }

  function close() {
    overlay.classList.remove("open");
    document.body.style.overflow = "";
    setTimeout(function () { overlay.hidden = true; }, 380);
    if (autoHideTimer) { clearTimeout(autoHideTimer); autoHideTimer = null; }
    if (lastFocused && lastFocused.focus) lastFocused.focus({ preventScroll: true });
  }

  function dismiss() {
    try { localStorage.setItem(LS_DISMISSED, "1"); } catch (e) {}
    close();
  }

  function setStatus(msg, kind) {
    statusEl.textContent = msg;
    statusEl.className = "popup-status" + (kind ? " " + kind : "");
  }

  function validEmail(v) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  }

  // Any interaction cancels the auto-dismiss.
  form.addEventListener("focusin", markInteracted);
  form.addEventListener("input", markInteracted);

  closeBtn.addEventListener("click", function () { markInteracted(); dismiss(); });
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) { markInteracted(); dismiss(); }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !overlay.hidden) { markInteracted(); dismiss(); }
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    markInteracted();

    var first = form.firstName.value.trim();
    var last = form.lastName.value.trim();
    var email = form.email.value.trim();
    var ok = true;

    [form.firstName, form.lastName].forEach(function (input) {
      var bad = !input.value.trim();
      input.classList.toggle("invalid", bad);
      if (bad) ok = false;
    });
    var emailBad = !validEmail(email);
    form.email.classList.toggle("invalid", emailBad);
    if (emailBad) ok = false;

    if (!ok) {
      setStatus("Please fill in your name and a valid email.", "error");
      return;
    }

    if (!MAILING_LIST_ENDPOINT) {
      setStatus("Preview mode — connect the mailing list sheet to activate signups.", "error");
      return;
    }

    submitBtn.disabled = true;
    setStatus("Joining…");

    // text/plain avoids a CORS preflight against the Apps Script web app.
    fetch(MAILING_LIST_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify({ firstName: first, lastName: last, email: email })
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data && data.ok) {
          try { localStorage.setItem(LS_SUBSCRIBED, "1"); } catch (e) {}
          card.classList.add("success-state");
          form.innerHTML = "";
          setStatus("You're in. Welcome to the loud side.", "success");
          card.querySelector(".popup-sub").textContent =
            "Thanks, " + first + " — you'll hear from us when there's something worth your inbox.";
          setTimeout(close, 3500);
        } else {
          throw new Error("rejected");
        }
      })
      .catch(function () {
        submitBtn.disabled = false;
        setStatus("Something hiccuped — try again in a moment.", "error");
      });
  });

  if (preview) {
    open();
    return;
  }

  // Dormant until David wires the sheet endpoint.
  if (!MAILING_LIST_ENDPOINT) return;

  var skip = false;
  try {
    skip = localStorage.getItem(LS_DISMISSED) === "1" ||
           localStorage.getItem(LS_SUBSCRIBED) === "1";
  } catch (e) {}
  if (skip) return;

  setTimeout(open, SHOW_DELAY_MS);
})();
