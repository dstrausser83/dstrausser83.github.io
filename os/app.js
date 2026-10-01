/* Dead Brands Business OS — shared admin shell.
   Provides OS.page(id, title, render), OS.api(method, path, body), OS.toast,
   OS.esc, OS.field helpers. Token gate: ADMIN_TOKEN in sessionStorage. */
(function () {
  "use strict";
  var API = localStorage.getItem("os_api_base") || "https://deadbrands-os.dstrausser83.workers.dev";

  var NAV = [
    ["index.html", "Dashboard", "home"],
    ["crm.html", "CRM", "crm"],
    ["email.html", "Email", "email"],
    ["prospect.html", "Prospecting", "prospect"],
    ["cms.html", "Content", "cms"],
    ["settings.html", "Settings", "settings"],
  ];

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function token() { return sessionStorage.getItem("os_token") || ""; }

  async function api(method, path, body) {
    var headers = { "content-type": "application/json" };
    var t = token();
    if (t) headers["authorization"] = "Bearer " + t;
    var res = await fetch(API + path, {
      method: method,
      headers: headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (res.status === 401) {
      sessionStorage.removeItem("os_token");
      location.reload();
      throw new Error("signed out");
    }
    var data = null;
    try { data = await res.json(); } catch (e) { throw new Error("bad response"); }
    if (!data.ok) throw new Error(data.error || "request failed");
    return data;
  }

  function toast(msg, isErr) {
    var el = document.getElementById("toast");
    el.textContent = msg;
    el.className = "toast show" + (isErr ? " err" : "");
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.className = "toast"; }, 3200);
  }

  function shell(activeId, title) {
    var links = NAV.map(function (n) {
      return '<a href="' + n[0] + '"' + (n[2] === activeId ? ' class="active"' : "") + ">" + n[1] + "</a>";
    }).join("");
    document.body.innerHTML =
      '<div class="os-top"><button class="os-burger" id="burger" aria-label="menu">☰</button>' +
      '<div class="brand">DEAD BRANDS <span>OS</span></div><div class="spacer"></div>' +
      '<button class="btn small ghost" id="lockbtn" style="color:#fff;border-color:#ffffff44">lock</button></div>' +
      '<nav class="os-nav" id="osnav">' + links + "</nav>" +
      '<div class="os-wrap"><h1>' + esc(title) + '</h1><div id="view"></div></div>' +
      '<div class="toast" id="toast"></div>';
    document.getElementById("burger").onclick = function () {
      document.getElementById("osnav").classList.toggle("open");
    };
    document.getElementById("lockbtn").onclick = function () {
      sessionStorage.removeItem("os_token");
      location.reload();
    };
  }

  function gate() {
    document.body.innerHTML =
      '<div class="os-wrap"><div class="gate card">' +
      "<h2>Dead Brands OS</h2>" +
      '<p class="muted">Paste your OS admin token to unlock. (Set once as the <b>ADMIN_TOKEN</b> secret on the deadbrands-os worker.)</p>' +
      '<div class="field"><input id="t" type="password" autocomplete="off" placeholder="admin token"></div>' +
      '<button class="btn" id="go">Unlock</button>' +
      '<p class="hint small muted">Kept only in this tab\u2019s memory — never saved to disk.</p>' +
      "</div></div>" + '<div class="toast" id="toast"></div>';
    document.getElementById("go").onclick = async function () {
      var v = document.getElementById("t").value.trim();
      if (!v) return;
      sessionStorage.setItem("os_token", v);
      try {
        await api("GET", "/api/stats");
        location.reload();
      } catch (e) {
        sessionStorage.removeItem("os_token");
        toast("That token didn't work.", true);
      }
    };
  }

  function field(label, inner, hint) {
    return '<div class="field"><label>' + esc(label) + "</label>" + inner +
      (hint ? '<div class="hint">' + esc(hint) + "</div>" : "") + "</div>";
  }
  function input(name, val, type, attrs) {
    return '<input name="' + name + '" type="' + (type || "text") + '" value="' + esc(val || "") + '"' + (attrs || "") + ">";
  }
  function textarea(name, val, attrs) {
    return '<textarea name="' + name + '"' + (attrs || "") + ">" + esc(val || "") + "</textarea>";
  }
  function select(name, val, options) {
    var o = options.map(function (x) {
      var v = Array.isArray(x) ? x[0] : x, l = Array.isArray(x) ? x[1] : x;
      return '<option value="' + esc(v) + '"' + (String(v) === String(val) ? " selected" : "") + ">" + esc(l) + "</option>";
    }).join("");
    return '<select name="' + name + '">' + o + "</select>";
  }

  async function page(id, title, render) {
    if (!token()) { gate(); return; }
    shell(id, title);
    var view = document.getElementById("view");
    try {
      await render(view);
    } catch (e) {
      view.innerHTML = '<div class="card"><p><b>Something broke loading this page.</b></p><p class="muted">' + esc(e.message) + "</p></div>";
    }
  }

  window.OS = {
    api: api, page: page, toast: toast, esc: esc,
    field: field, input: input, textarea: textarea, select: select,
    apiBase: function () { return API; },
  };
})();
