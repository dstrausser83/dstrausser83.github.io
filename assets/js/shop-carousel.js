// Dead Brands shop carousel + 10% discount code — no frameworks.
//
// Carousel:
//   - Loads /assets/data/products.json (ranked by sales_rank).
//   - Renders product cards in a horizontal scroll-snap carousel.
//   - Prev/next buttons scroll by one card. Touch swipe works natively.
//   - As products publish and sell, update products.json — the homepage
//     carousel repopulates automatically, hottest sellers first.
//
// Discount:
//   - Visitor enters email + cell → gets a one-time 10% off code.
//   - Code format: BITE10-XXXXXX (unique per visitor, stored in localStorage).
//   - Email/phone are POSTed to the mailing list endpoint for lead capture.
//   - David must create a matching 10% discount in Printify for codes to redeem.

(function () {
  "use strict";

  var PRODUCTS_URL = "/assets/data/products.json";
  var MAILING_LIST_ENDPOINT = "https://script.google.com/macros/s/AKfycbwnOSosh68et8uOajfznNiDPSvVFFJjE-EZ0yNvNTr_uPsWjP_jj0ZNJnJfDJzb6gMm/exec";
  var LS_DISCOUNT_CODE = "db_discount_code";

  // ---------- Carousel ----------

  var carousel = document.getElementById("shop-carousel");
  var prevBtn = document.getElementById("carousel-prev");
  var nextBtn = document.getElementById("carousel-next");

  function money(n) {
    return "$" + n.toFixed(2);
  }

  function cardHTML(p) {
    return (
      '<article class="shop-card">' +
        '<a href="' + p.url + '" tabindex="-1" aria-hidden="true">' +
          '<img src="' + p.image + '" alt="' + p.alt + '" width="400" height="470" loading="lazy" />' +
        '</a>' +
        '<div class="shop-card-body">' +
          '<h3>' + p.name + '</h3>' +
          '<p class="shop-card-price">' + money(p.price) + '</p>' +
          '<a class="btn btn-sm" href="' + p.url + '">Shop Now</a>' +
        '</div>' +
      '</article>'
    );
  }

  function renderCarousel(products) {
    if (!carousel || !products || !products.length) return;
    // Sort by sales_rank ascending (1 = hottest seller).
    products.sort(function (a, b) { return a.sales_rank - b.sales_rank; });
    carousel.innerHTML = products.map(cardHTML).join("");
  }

  function scrollByCard(dir) {
    if (!carousel) return;
    var card = carousel.querySelector(".shop-card");
    if (!card) return;
    var gap = 16;
    var amount = card.offsetWidth + gap;
    carousel.scrollBy({ left: dir * amount, behavior: "smooth" });
  }

  if (prevBtn) prevBtn.addEventListener("click", function () { scrollByCard(-1); });
  if (nextBtn) nextBtn.addEventListener("click", function () { scrollByCard(1); });

  fetch(PRODUCTS_URL)
    .then(function (res) { return res.json(); })
    .then(function (data) { renderCarousel(data.products); })
    .catch(function () {
      // Fallback: static cards if the JSON fails to load.
      if (carousel) {
        carousel.innerHTML =
          cardHTML({ name: "Shark Bite Biz Tee", price: 26.99, url: "/merch/",
            image: "/assets/img/merch/sharkbite-tee-black.webp",
            alt: "Shark Bite Biz tee — black shirt with the official Shark Bite Biz logo" }) +
          cardHTML({ name: "Shark Bite Biz Hoodie", price: 44.99, url: "/merch/",
            image: "/assets/img/merch/sharkbite-hoodie-black.webp",
            alt: "Shark Bite Biz hoodie — black pullover hoodie with the official Shark Bite Biz logo" });
      }
    });

  // ---------- 10% discount code ----------

  var form = document.getElementById("discount-form");
  var statusEl = document.getElementById("discount-status");
  if (!form) return;

  function setStatus(msg, isError) {
    statusEl.textContent = msg;
    statusEl.className = "discount-status" + (isError ? " error" : " success");
  }

  function makeCode() {
    var chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    var suffix = "";
    for (var i = 0; i < 6; i++) {
      suffix += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return "BITE10-" + suffix;
  }

  function validEmail(v) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  }

  function validPhone(v) {
    return /^[+\d][\d\s\-().]{6,}$/.test(v);
  }

  // If they already got a code, show it instead of the form.
  try {
    var existing = localStorage.getItem(LS_DISCOUNT_CODE);
    if (existing) {
      form.innerHTML = "";
      setStatus("Your 10% off code: " + existing + " — one-time use at checkout.", false);
      return;
    }
  } catch (e) {}

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = form.email.value.trim();
    var phone = form.phone.value.trim();

    if (!validEmail(email)) {
      setStatus("Please enter a valid email.", true);
      return;
    }
    if (!validPhone(phone)) {
      setStatus("Please enter a valid cell phone number.", true);
      return;
    }

    var code = makeCode();
    try { localStorage.setItem(LS_DISCOUNT_CODE, code); } catch (e) {}

    // Capture the lead (email + phone) for David's list.
    if (MAILING_LIST_ENDPOINT) {
      fetch(MAILING_LIST_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "text/plain;charset=utf-8" },
        body: JSON.stringify({ email: email, phone: phone, source: "discount-10pct", discountCode: code })
      }).catch(function () { /* lead capture is best-effort */ });
    }

    form.innerHTML = "";
    setStatus("Your 10% off code: " + code + " — one-time use at checkout. We texted the details to " + phone + ".", false);
  });
})();
