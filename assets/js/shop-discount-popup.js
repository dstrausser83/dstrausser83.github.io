// Dead Brands shop discount popup — /merch/ only.
//
// Offers 10% off (universal code BITE10) for joining the mailing list.
//   - Shows 8s after page load on the shop page.
//   - Once per visitor (localStorage).
//   - On submit: first name + email + cell -> Apps Script logs the lead
//     and emails the visitor their code instantly.
//   - The code is also shown on-screen immediately so checkout never waits.

(function () {
  "use strict";

  var MAILING_LIST_ENDPOINT = "https://script.google.com/macros/s/AKfycbwnOSosh68et8uOajfznNiDPSvVFFJjE-EZ0yNvNTr_uPsWjP_jj0ZNJnJfDJzb6gMm/exec";
  var DISCOUNT_CODE = "BITE10";
  var SHOW_DELAY_MS = 8000;
  var LS_SEEN = "db_shop_discount_seen";

  var overlay = document.getElementById("shop-discount-popup");
  if (!overlay) return;
  var form = document.getElementById("shop-discount-form");
  var closeBtn = document.getElementById("shop-discount-close");
  var statusEl = document.getElementById("shop-discount-status");
  var card = overlay.querySelector(".popup-card");
  var preview = /[?&]preview=discount\b/.test(window.location.search);

  function open() {
    overlay.hidden = false;
    void overlay.offsetWidth;
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
    var first = form.querySelector('input[name="firstName"]');
    if (first) first.focus({ preventScroll: true });
  }

  function close() {
    overlay.classList.remove("open");
    document.body.style.overflow = "";
    setTimeout(function () { overlay.hidden = true; }, 380);
  }

  function dismiss() {
    try { localStorage.setItem(LS_SEEN, "1"); } catch (e) {}
    close();
  }

  function setStatus(msg, kind) {
    statusEl.textContent = msg;
    statusEl.className = "popup-status" + (kind ? " " + kind : "");
  }

  function validEmail(v) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  }

  closeBtn.addEventListener("click", dismiss);
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) dismiss();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !overlay.hidden) dismiss();
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var first = form.firstName.value.trim();
    var email = form.email.value.trim();
    var phone = form.phone.value.trim();
    var ok = true;

    if (!first) { form.firstName.classList.add("invalid"); ok = false; }
    else form.firstName.classList.remove("invalid");
    if (!validEmail(email)) { form.email.classList.add("invalid"); ok = false; }
    else form.email.classList.remove("invalid");
    if (!ok) { setStatus("Please add your name and a valid email.", "error"); return; }

    var btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    setStatus("Sending your code...");

    fetch(MAILING_LIST_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify({ action: "discount_code", firstName: first, email: email, phone: phone })
    }).catch(function () {});

    try { localStorage.setItem(LS_SEEN, "1"); } catch (e) {}
    card.classList.add("success-state");
    form.innerHTML = "";
    card.querySelector(".popup-sub").textContent =
      "Thanks, " + first + " - your code is on its way to " + email + ".";
    setStatus("Your 10% off code: " + DISCOUNT_CODE, "success");
    setTimeout(close, 6000);
  });

  if (preview) { open(); return; }
  if (!MAILING_LIST_ENDPOINT) return;

  var seen = false;
  try { seen = localStorage.getItem(LS_SEEN) === "1"; } catch (e) {}
  if (seen) return;

  setTimeout(open, SHOW_DELAY_MS);
})();
