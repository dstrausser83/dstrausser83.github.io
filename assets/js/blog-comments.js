/**
 * Dead Brands gated blog comments.
 * David's rule: COMMENT = "I WANT IN." Posting a comment IS the marketing
 * opt-in — the gate says so plainly. No separate newsletter checkbox.
 *
 * Mount: <section id="db-comments"></section> on blog post pages.
 * Slug is derived from the URL: /blog/posts/<slug>.html
 */
(function () {
  "use strict";
  var API = "https://comment-gate.dstrausser83.workers.dev";

  function $(sel, el) { return (el || document).querySelector(sel); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function slugFromUrl() {
    var m = location.pathname.match(/\/blog\/posts\/([a-z0-9][a-z0-9-]{0,79})\.html/);
    return m ? m[1] : null;
  }
  function fmtDate(iso) {
    try {
      return new Date(iso).toLocaleDateString("en-US", {
        month: "short", day: "numeric", year: "numeric",
      });
    } catch (e) { return ""; }
  }
  function api(path, opts) {
    opts = opts || {};
    opts.credentials = "include";
    opts.headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    return fetch(API + path, opts).then(function (r) {
      return r.json().then(function (j) { return { status: r.status, body: j }; });
    });
  }

  function renderComments(mount, comments) {
    var html = "<h2>Comments (" + comments.length + ")</h2>";
    if (!comments.length) {
      html += '<p class="dbc-empty">No comments yet — be the first. That\'s the whole point of this section.</p>';
    } else {
      html += '<ul class="dbc-list">' + comments.map(function (c) {
        return '<li class="dbc-comment"><div class="dbc-comment-head">' +
          '<span class="dbc-comment-name">' + esc(c.name) + "</span>" +
          '<span class="dbc-comment-date">' + esc(fmtDate(c.at)) + "</span></div>" +
          "<p>" + esc(c.text).replace(/\n/g, "<br>") + "</p></li>";
      }).join("") + "</ul>";
    }
    var list = document.createElement("div");
    list.innerHTML = html;
    mount.appendChild(list);
  }

  function consentBlock() {
    return '<div class="dbc-consent"><strong>Here\'s the deal: COMMENT = I WANT IN.</strong><br>' +
      "By commenting, you're joining the Dead Brands mailing list. You'll get marketing emails " +
      "from Dead Brands, LLC — unsubscribe anytime with one click.</div>";
  }

  function renderGate(mount, slug, cfg) {
    var wrap = document.createElement("div");
    wrap.className = "dbc-gate";
    var oauthBtns = "";
    var providers = [];
    if (cfg.oauth) {
      if (cfg.oauth.google) providers.push(["google", "Google"]);
      if (cfg.oauth.facebook) providers.push(["facebook", "Facebook"]);
      if (cfg.oauth.x) providers.push(["x", "X"]);
    }
    if (providers.length) {
      oauthBtns = '<div class="dbc-oauth">' + providers.map(function (p) {
        var href = API + "/oauth/" + p[0] + "?redirect=" + encodeURIComponent(location.href);
        return '<a href="' + esc(href) + '">Continue with ' + esc(p[1]) + "</a>";
      }).join("") + "</div>";
    }
    wrap.innerHTML =
      "<h3>Join the conversation</h3>" +
      "<p>Comments are for subscribers. Drop your email (or sign in below) and you're in — then say your piece.</p>" +
      consentBlock() +
      '<div class="dbc-row">' +
      '<input type="text" id="dbc-name" placeholder="Your name" maxlength="60" autocomplete="name">' +
      '<input type="email" id="dbc-email" placeholder="you@example.com" maxlength="120" autocomplete="email">' +
      "</div>" +
      '<input type="text" id="dbc-hp" class="dbc-hp" tabindex="-1" autocomplete="off" aria-hidden="true">' +
      '<button class="dbc-btn" id="dbc-join">Join &amp; Comment</button>' +
      '<p class="dbc-msg" id="dbc-gate-msg" role="status"></p>' +
      (oauthBtns ? '<div class="dbc-or">— or —</div>' + oauthBtns : "");
    mount.appendChild(wrap);

    $("#dbc-join", wrap).addEventListener("click", function () {
      var btn = this;
      var msg = $("#dbc-gate-msg", wrap);
      var name = $("#dbc-name", wrap).value.trim();
      var email = $("#dbc-email", wrap).value.trim();
      var hp = $("#dbc-hp", wrap).value;
      msg.className = "dbc-msg";
      msg.textContent = "";
      if (!name) { msg.classList.add("err"); msg.textContent = "Give us a name — even a nickname."; return; }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
        msg.classList.add("err"); msg.textContent = "That email doesn't look right."; return;
      }
      btn.disabled = true;
      btn.textContent = "Joining…";
      api("/api/subscribe", {
        method: "POST",
        body: JSON.stringify({ name: name, email: email, website: hp }),
      }).then(function (res) {
        if (res.status === 200 && res.body.ok) {
          loadForm(mount, slug, { name: name });
        } else {
          msg.classList.add("err");
          msg.textContent = res.body.error || "Something broke — try again.";
          btn.disabled = false;
          btn.textContent = "Join & Comment";
        }
      }).catch(function () {
        msg.classList.add("err");
        msg.textContent = "Couldn't reach the server — check your connection.";
        btn.disabled = false;
        btn.textContent = "Join & Comment";
      });
    });
  }

  function renderNeedEmail(mount, slug, me) {
    var wrap = document.createElement("div");
    wrap.className = "dbc-gate";
    wrap.innerHTML =
      "<h3>One more step</h3>" +
      "<p>You're signed in as <b>" + esc(me.name) + "</b>, but your sign-in didn't share an email. " +
      "Add it to join the list and comment:</p>" +
      consentBlock() +
      '<div class="dbc-row"><input type="email" id="dbc-email2" placeholder="you@example.com" maxlength="120"></div>' +
      '<input type="text" id="dbc-hp2" class="dbc-hp" tabindex="-1" autocomplete="off" aria-hidden="true">' +
      '<button class="dbc-btn" id="dbc-addemail">Add email &amp; Comment</button>' +
      '<p class="dbc-msg" id="dbc-email-msg" role="status"></p>';
    mount.appendChild(wrap);
    $("#dbc-addemail", wrap).addEventListener("click", function () {
      var btn = this, msg = $("#dbc-email-msg", wrap);
      var email = $("#dbc-email2", wrap).value.trim();
      msg.className = "dbc-msg"; msg.textContent = "";
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
        msg.classList.add("err"); msg.textContent = "That email doesn't look right."; return;
      }
      btn.disabled = true;
      api("/api/subscribe-email", {
        method: "POST",
        body: JSON.stringify({ email: email, website: $("#dbc-hp2", wrap).value }),
      }).then(function (res) {
        if (res.status === 200 && res.body.ok) loadForm(mount, slug, me);
        else {
          msg.classList.add("err");
          msg.textContent = res.body.error || "Something broke — try again.";
          btn.disabled = false;
        }
      });
    });
  }

  function loadForm(mount, slug, me) {
    // remove any existing gate/form
    var olds = mount.querySelectorAll(".dbc-gate, .dbc-form-wrap");
    for (var i = 0; i < olds.length; i++) olds[i].remove();
    var wrap = document.createElement("div");
    wrap.className = "dbc-form-wrap";
    wrap.innerHTML =
      '<div class="dbc-signedin"><span>Commenting as <b>' + esc(me.name) + "</b></span>" +
      '<a href="' + esc(API + "/logout?redirect=" + encodeURIComponent(location.href)) + '">Not you? Sign out</a></div>' +
      '<div class="dbc-form"><textarea id="dbc-text" maxlength="2000" placeholder="Say something worth reading…"></textarea></div>' +
      '<input type="text" id="dbc-hp3" class="dbc-hp" tabindex="-1" autocomplete="off" aria-hidden="true">' +
      '<div class="dbc-row"><button class="dbc-btn" id="dbc-post">Post comment</button></div>' +
      '<p class="dbc-msg" id="dbc-form-msg" role="status"></p>';
    mount.appendChild(wrap);
    $("#dbc-post", wrap).addEventListener("click", function () {
      var btn = this, msg = $("#dbc-form-msg", wrap);
      var text = $("#dbc-text", wrap).value.trim();
      msg.className = "dbc-msg"; msg.textContent = "";
      if (text.length < 2) { msg.classList.add("err"); msg.textContent = "Write a little more than that."; return; }
      btn.disabled = true;
      btn.textContent = "Posting…";
      api("/api/comment", {
        method: "POST",
        body: JSON.stringify({ slug: slug, text: text, website: $("#dbc-hp3", wrap).value }),
      }).then(function (res) {
        if (res.status === 200 && res.body.ok) {
          msg.classList.add("ok");
          msg.textContent = "You're in! Your comment is in the moderation queue and will show up once approved.";
          $("#dbc-text", wrap).value = "";
        } else if (res.status === 401) {
          msg.classList.add("err");
          msg.textContent = "Your session expired — refresh and join again.";
        } else {
          msg.classList.add("err");
          msg.textContent = res.body.error || "Something broke — try again.";
        }
        btn.disabled = false;
        btn.textContent = "Post comment";
      }).catch(function () {
        msg.classList.add("err");
        msg.textContent = "Couldn't reach the server — check your connection.";
        btn.disabled = false;
        btn.textContent = "Post comment";
      });
    });
  }

  function init() {
    var mount = document.getElementById("db-comments");
    if (!mount) return;
    var slug = slugFromUrl();
    if (!slug) return;
    Promise.all([
      api("/api/config"),
      api("/api/me"),
      api("/api/comments?slug=" + encodeURIComponent(slug)),
    ]).then(function (rs) {
      var cfg = rs[0].body || {};
      var me = rs[1].body || {};
      var comments = (rs[2].body && rs[2].body.comments) || [];
      renderComments(mount, comments);
      if (me.loggedIn) {
        if (me.needEmail) renderNeedEmail(mount, slug, me);
        else loadForm(mount, slug, me);
      } else {
        renderGate(mount, slug, cfg);
      }
    }).catch(function () {
      mount.innerHTML = "<h2>Comments</h2><p class='dbc-empty'>Comments are temporarily unavailable.</p>";
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
