// Dead Brands shop carousel — no frameworks.
//
//   - Loads /assets/data/products.json (ranked by sales_rank).
//   - Renders product cards in a horizontal scroll-snap carousel.
//   - Prev/next buttons scroll by one card. Touch swipe works natively.
//   - As products publish and sell, update products.json — the homepage
//     carousel repopulates automatically, hottest sellers first.

(function () {
  "use strict";

  var PRODUCTS_URL = "/assets/data/products.json";

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
})();
