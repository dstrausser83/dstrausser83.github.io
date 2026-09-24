// David Strausser site — small interactions, no frameworks.

(function () {
  "use strict";

  // Footer year
  var yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // Header shadow on scroll
  var header = document.getElementById("site-header");
  var onScroll = function () {
    if (header) header.classList.toggle("scrolled", window.scrollY > 12);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Mobile nav
  var toggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) {
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Open menu");
      }
    });
  }

  // Reveal on scroll
  var revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && revealEls.length) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("visible"); });
  }

  // Active nav link
  var sections = ["about", "career", "work", "podcast", "life", "shop", "faq", "contact"]
    .map(function (id) { return document.getElementById(id); })
    .filter(Boolean);
  var navLinks = nav ? Array.prototype.slice.call(nav.querySelectorAll('a[href^="#"]')) : [];
  if ("IntersectionObserver" in window && sections.length && navLinks.length) {
    var navIO = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            var id = entry.target.id;
            navLinks.forEach(function (a) {
              a.classList.toggle("active", a.getAttribute("href") === "#" + id);
            });
          }
        });
      },
      { rootMargin: "-40% 0px -55% 0px" }
    );
    sections.forEach(function (s) { navIO.observe(s); });
  }

  // Services dropdown: touch/keyboard toggle (desktop hover handled in CSS).
  // First tap opens the submenu; the toggle link still navigates on second tap
  // via the "All services" item. Escape closes.
  var drops = document.querySelectorAll(".nav-drop");
  drops.forEach(function (drop) {
    var toggle = drop.querySelector(".nav-drop-toggle");
    if (!toggle) return;
    toggle.addEventListener("click", function (e) {
      var isTouch = window.matchMedia("(hover: none)").matches;
      var narrow = window.innerWidth <= 860;
      if (isTouch || narrow) {
        if (!drop.classList.contains("open")) {
          e.preventDefault();
          drops.forEach(function (d) {
            d.classList.remove("open");
            var t = d.querySelector(".nav-drop-toggle");
            if (t) t.setAttribute("aria-expanded", "false");
          });
          drop.classList.add("open");
          toggle.setAttribute("aria-expanded", "true");
        }
      }
    });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      drops.forEach(function (d) {
        d.classList.remove("open");
        var t = d.querySelector(".nav-drop-toggle");
        if (t) t.setAttribute("aria-expanded", "false");
      });
    }
  });
})();
