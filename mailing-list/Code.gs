// Dead Brands website backend — v2 (2026-09-23).
// Paste into the Apps Script project, then:
//   1. Project Settings > Script properties > add READ_KEY = <long random string>
//      (same value goes in the CRM portal config as the sheet read key).
//   2. In the editor, run setupDashboard() once (authorizes on first run).
//   3. Deploy > Manage deployments > edit the Web app deployment > New version.
//      The /exec URL stays the same.
//
// Tabs:  <mailing list>  — the tab the signup path writes to. Its name is
//        detected automatically (the v1 header row) and remembered in the
//        MAIL_SHEET_NAME script property — never depends on which tab is
//        active in the UI. Override it manually in Script properties if needed.
//        Pageviews       — one row per pageview from assets/js/analytics.js.
//        Dashboard       — live KPI tab built by setupDashboard().
//
// doPost: action="pageview" -> Pageviews tab; anything else -> mailing-list
//         signup path (v1 fields and validation, explicit sheet lookup).
// doGet:  ?action=kpis&key=READ_KEY -> JSON KPIs for the CRM portal.

var PV_SHEET = "Pageviews";
var DASH_SHEET = "Dashboard";
var MAIL_SHEET_PROP = "MAIL_SHEET_NAME";
var PV_HEADER = ["Timestamp", "Page", "Referrer", "utm_source", "utm_medium", "utm_campaign", "Session"];
var MAIL_HEADER = ["Timestamp", "First name", "Last name", "Email"];

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);

    // ---- pageview path (assets/js/analytics.js) ----
    if (data.action === "pageview") {
      var pv = sheet_(PV_SHEET, PV_HEADER);
      pv.appendRow([
        new Date(),
        str_(data.page, 300),
        str_(data.referrer, 300),
        str_(data.utm_source, 60),
        str_(data.utm_medium, 60),
        str_(data.utm_campaign, 120),
        str_(data.sid, 40)
      ]);
      return json({ ok: true });
    }

    // ---- mailing-list path (v1 fields + validation, explicit sheet) ----
    var first = String(data.firstName || "").trim().slice(0, 80);
    var last = String(data.lastName || "").trim().slice(0, 80);
    var email = String(data.email || "").trim().slice(0, 160);

    if (!first || !last || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return json({ ok: false, error: "invalid" });
    }

    var sheet = mailSheet_();
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(MAIL_HEADER);
    }
    sheet.appendRow([new Date(), first, last, email]);
    return json({ ok: true });
  } catch (err) {
    return json({ ok: false, error: "server" });
  }
}

function doGet(e) {
  try {
    var p = (e && e.parameter) || {};
    if (p.action !== "kpis") return json({ ok: false, error: "unknown_action" });
    var want = String(p.key || "");
    var have = PropertiesService.getScriptProperties().getProperty("READ_KEY") || "";
    if (!have || want !== have) {
      return json({ ok: false, error: "forbidden" });
    }
    return json(kpis_());
  } catch (err) {
    return json({ ok: false, error: "server" });
  }
}

// ---- Mailing-list sheet lookup. Never uses the active tab. ----
// 1. MAIL_SHEET_NAME script property, if set and valid.
// 2. The tab carrying the v1 signup header row (auto-detect, then remembered).
// 3. Fallback: the first tab holding data that isn't Pageviews/Dashboard.
function mailSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var props = PropertiesService.getScriptProperties();

  var name = props.getProperty(MAIL_SHEET_PROP);
  var pinned = name ? ss.getSheetByName(name) : null;
  if (pinned) return pinned;

  var found = null, firstData = null, i, j;
  var sheets = ss.getSheets();
  for (i = 0; i < sheets.length; i++) {
    var s = sheets[i];
    var n = s.getName();
    if (n === PV_SHEET || n === DASH_SHEET) continue;
    if (!firstData && s.getLastRow() > 0) firstData = s;
    if (s.getLastRow() === 0) continue;
    var head = s.getRange(1, 1, 1, MAIL_HEADER.length).getValues()[0];
    var match = true;
    for (j = 0; j < MAIL_HEADER.length; j++) {
      if (String(head[j] || "").trim() !== MAIL_HEADER[j]) { match = false; break; }
    }
    if (match) { found = s; break; }
  }
  if (!found) found = firstData || sheets[0];
  props.setProperty(MAIL_SHEET_PROP, found.getName());
  return found;
}

// ---- KPI computation for the CRM portal ----
function kpis_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var pv = ss.getSheetByName(PV_SHEET);
  var mail = mailSheet_(); // explicit lookup — active tab is irrelevant

  var pvRows = (pv && pv.getLastRow() > 1)
    ? pv.getRange(2, 1, pv.getLastRow() - 1, PV_HEADER.length).getValues() : [];
  var mailRows = (mail && mail.getLastRow() > 1)
    ? mail.getRange(2, 1, mail.getLastRow() - 1, MAIL_HEADER.length).getValues() : [];

  var today = new Date();
  today.setHours(0, 0, 0, 0);

  var bySource = {}, byCampaign = {}, byPage = {};
  var pvToday = 0, i, r;
  for (i = 0; i < pvRows.length; i++) {
    r = pvRows[i];
    if (r[0] instanceof Date && r[0] >= today) pvToday++;
    var s = String(r[3] || "").toLowerCase() || "(direct)";
    var c = String(r[5] || "") || "(none)";
    var pg = String(r[1] || "") || "/";
    bySource[s] = (bySource[s] || 0) + 1;
    byCampaign[c] = (byCampaign[c] || 0) + 1;
    byPage[pg] = (byPage[pg] || 0) + 1;
  }

  var mailToday = 0, j;
  for (j = 0; j < mailRows.length; j++) {
    if (mailRows[j][0] instanceof Date && mailRows[j][0] >= today) mailToday++;
  }

  return {
    ok: true,
    generated_at: new Date().toISOString(),
    // Nested shape matches what the CRM portal dashboard expects:
    //   website: {pageviews, pageviews_today, by_source, by_campaign, top_pages}
    //   mailing_list: {signups, signups_today, conversion_pct}
    website: {
      pageviews: pvRows.length,
      pageviews_today: pvToday,
      by_source: top_(bySource, 10),
      by_campaign: top_(byCampaign, 10),
      top_pages: top_(byPage, 10)
    },
    mailing_list: {
      signups: mailRows.length,
      signups_today: mailToday,
      conversion_pct: pvRows.length > 0
        ? Math.round(mailRows.length / pvRows.length * 10000) / 100 : 0
    }
  };
}

function top_(obj, n) {
  var arr = [];
  for (var k in obj) arr.push([k, obj[k]]);
  arr.sort(function (a, b) { return b[1] - a[1]; });
  return arr.slice(0, n);
}

// ---- one-time dashboard tab builder: run setupDashboard() in the editor ----
// The mailing-list tab is found with mailSheet_(), so it does not matter
// which tab is active when this runs. Nothing here changes the signup path.
function setupDashboard() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  sheet_(PV_SHEET, PV_HEADER); // make sure the tab exists
  var dash = ss.getSheetByName(DASH_SHEET);
  if (!dash) dash = ss.insertSheet(DASH_SHEET);
  dash.clear();

  var mailName = mailSheet_().getName(); // explicit lookup, not the active tab
  var PV = "'" + PV_SHEET + "'";
  var ML = "'" + mailName.replace(/'/g, "") + "'";

  var cells = [
    ["Dead Brands — Website Dashboard", ""],
    ["Live numbers. The CRM portal reads the same data via ?action=kpis.", ""],
    ["", ""],
    ["Pageviews (total)", "=COUNTA(" + PV + "!A2:A)"],
    ["Pageviews (today)", "=COUNTIFS(" + PV + "!A2:A,\">=\"&TODAY()," + PV + "!A2:A,\"<\"&TODAY()+1)"],
    ["Signups (total)", "=COUNTA(" + ML + "!A2:A)"],
    ["Signups (today)", "=COUNTIFS(" + ML + "!A2:A,\">=\"&TODAY()," + ML + "!A2:A,\"<\"&TODAY()+1)"],
    ["Visitor → signup %", "=IF(B4>0,B6/B4,0)"],
    ["", ""],
    ["Views by source (top 10)", ""],
    ["=QUERY(" + PV + "!A2:G,\"select D,count(A) where A is not null group by D order by count(A) desc limit 10 label D 'Source', count(A) 'Views'\",0)", ""],
    ["", ""],
    ["Views by campaign (top 10)", ""],
    ["=QUERY(" + PV + "!A2:G,\"select F,count(A) where A is not null group by F order by count(A) desc limit 10 label F 'Campaign', count(A) 'Views'\",0)", ""],
    ["", ""],
    ["Top pages (top 10)", ""],
    ["=QUERY(" + PV + "!A2:G,\"select B,count(A) where A is not null group by B order by count(A) desc limit 10 label B 'Page', count(A) 'Views'\",0)", ""]
  ];

  dash.getRange(1, 1, cells.length, 2).setValues(cells);
  // Turn the "=" strings into real formulas.
  for (var i = 0; i < cells.length; i++) {
    var f = cells[i][1];
    if (typeof f === "string" && f.charAt(0) === "=") {
      dash.getRange(i + 1, 2).setFormula(f);
    }
    var a0 = cells[i][0];
    if (typeof a0 === "string" && a0.charAt(0) === "=") {
      dash.getRange(i + 1, 1).setFormula(a0);
    }
  }

  dash.getRange("A1").setFontWeight("bold").setFontSize(14);
  dash.getRange("A4:A8").setFontWeight("bold");
  dash.getRange("A10").setFontWeight("bold");
  dash.getRange("A13").setFontWeight("bold");
  dash.getRange("A16").setFontWeight("bold");
  dash.getRange("B8").setNumberFormat("0.00%");
  dash.setColumnWidth(1, 280);
  dash.setColumnWidth(2, 220);
  dash.setFrozenRows(3);
  return "Dashboard tab ready.";
}

function sheet_(name, header) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    if (header) sh.appendRow(header);
  } else if (header && sh.getLastRow() === 0) {
    sh.appendRow(header);
  }
  return sh;
}

function str_(v, n) {
  return String(v == null ? "" : v).slice(0, n);
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
