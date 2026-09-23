// Dead Brands backend v2 — mailing list + first-party pageview analytics.
// Paste this into the Google Apps Script project bound to the sheet,
// then Deploy > Manage deployments > New version (same web app URL).
// After deploying, run setupDashboard() once from the editor.

// ---------------------------------------------------------------- routing
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var action = String(data.action || "subscribe");
    if (action === "pageview") return logPageview(data);
    return subscribe(data); // default: mailing-list signup (unchanged)
  } catch (err) {
    return json({ ok: false, error: "server" });
  }
}

// ------------------------------------------------- read API for the CRM
// GET {exec}?action=kpis&key=READ_KEY  -> {ok, pageviews_total, pageviews_today,
//   by_source:[[src,n]...], signups_total}
// Set READ_KEY below to a long random string (same value goes in the CRM config).
var READ_KEY = "SET_ME_IN_EDITOR";

function doGet(e) {
  try {
    var p = (e && e.parameter) || {};
    if (String(p.action) !== "kpis" || String(p.key || "") !== READ_KEY || READ_KEY === "SET_ME_IN_EDITOR") {
      return json({ ok: false, error: "forbidden" });
    }
    var pv = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Pageviews");
    var total = 0, today = 0, bySource = {};
    if (pv && pv.getLastRow() > 1) {
      var rows = pv.getRange(2, 1, pv.getLastRow() - 1, 5).getValues();
      total = rows.length;
      var start = new Date(); start.setHours(0, 0, 0, 0);
      for (var i = 0; i < rows.length; i++) {
        if (rows[i][0] && new Date(rows[i][0]) >= start) today++;
        var s = String(rows[i][3] || "direct").slice(0, 60) || "direct";
        bySource[s] = (bySource[s] || 0) + 1;
      }
    }
    var sub = firstDataSheet();
    var signups = (sub && sub.getLastRow() > 1) ? sub.getLastRow() - 1 : 0;
    var srcArr = [];
    for (var k in bySource) srcArr.push([k, bySource[k]]);
    srcArr.sort(function (a, b) { return b[1] - a[1]; });
    return json({ ok: true, pageviews_total: total, pageviews_today: today,
                  by_source: srcArr, signups_total: signups });
  } catch (err) {
    return json({ ok: false, error: "server" });
  }
}

// ------------------------------------------------------------- pageviews
function logPageview(data) {
  var sheet = ensureTab("Pageviews",
    ["Timestamp", "Page", "Referrer", "utm_source", "utm_medium", "utm_campaign", "Session"]);
  sheet.appendRow([
    new Date(),
    String(data.page || "").slice(0, 300),
    String(data.referrer || "").slice(0, 300),
    String(data.utm_source || "").slice(0, 60),
    String(data.utm_medium || "").slice(0, 60),
    String(data.utm_campaign || "").slice(0, 120),
    String(data.sid || "").slice(0, 40)
  ]);
  return json({ ok: true });
}

// ---------------------------------------------------------- mailing list
// UNCHANGED from v1 — writes to the sheet's active (first) tab.
function subscribe(data) {
  var first = String(data.firstName || "").trim().slice(0, 80);
  var last = String(data.lastName || "").trim().slice(0, 80);
  var email = String(data.email || "").trim().slice(0, 160);

  if (!first || !last || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return json({ ok: false, error: "invalid" });
  }

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(["Timestamp", "First name", "Last name", "Email"]);
  }
  sheet.appendRow([new Date(), first, last, email]);
  return json({ ok: true });
}

// --------------------------------------------------------------- helpers
function ensureTab(name, headers) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(headers);
  } else if (sheet.getLastRow() === 0) {
    sheet.appendRow(headers);
  }
  return sheet;
}

function firstDataSheet() {
  var sheets = SpreadsheetApp.getActiveSpreadsheet().getSheets();
  for (var i = 0; i < sheets.length; i++) {
    var n = sheets[i].getName();
    if (n !== "Pageviews" && n !== "Dashboard") return sheets[i];
  }
  return null;
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// -------------------------------------------------------------- dashboard
// Run ONCE from the script editor after deploying v2. Builds a live
// "Dashboard" tab: traffic by source/campaign/page + mailing-list signups.
// UTM convention (must match the social drafter): utm_source=<platform>,
// utm_medium=social, utm_campaign=<post-slug>.
function setupDashboard() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var old = ss.getSheetByName("Dashboard");
  if (old) ss.deleteSheet(old);
  var d = ss.insertSheet("Dashboard");
  var sub = firstDataSheet();
  var subName = sub ? sub.getName() : "Sheet1";

  var rows = [
    ["Dead Brands — ROI Dashboard", ""],
    ["Last updated", "=NOW()"],
    ["", ""],
    ["WEBSITE TRAFFIC (Pageviews tab)", ""],
    ["Total pageviews", "=COUNTA(Pageviews!A2:A)"],
    ["Pageviews today", "=COUNTIFS(Pageviews!A2:A,\">=\"&TODAY(),Pageviews!A2:A,\"<\"&(TODAY()+1))"],
    ["", ""],
    ["Views by source", "Views"],
    ["=QUERY(Pageviews!A2:G,\"select D, count(A) where D <> '' group by D order by count(A) desc label D 'Source', count(A) 'Views'\",1)", ""],
    ["", ""],
    ["Views by campaign", "Views"],
    ["=QUERY(Pageviews!A2:G,\"select F, count(A) where F <> '' group by F order by count(A) desc label F 'Campaign', count(A) 'Views'\",1)", ""],
    ["", ""],
    ["Top pages", "Views"],
    ["=QUERY(Pageviews!A2:G,\"select B, count(A) group by B order by count(A) desc limit 10 label B 'Page', count(A) 'Views'\",1)", ""],
    ["", ""],
    ["MAILING LIST (" + subName + " tab)", ""],
    ["Total signups", "=COUNTA('" + subName + "'!A2:A)"],
    ["Signups today", "=COUNTIFS('" + subName + "'!A2:A,\">=\"&TODAY(),'" + subName + "'!A2:A,\"<\"&(TODAY()+1))"],
    ["", ""],
    ["FUNNEL", ""],
    ["Visitor -> signup rate", "=IF(B5>0,B20/B5,0)"],
    ["", ""],
    ["Notes: traffic with utm_source=<platform>&utm_medium=social comes from social posts.",
     "Campaign slug = the post. CRM portal reads the same data via doGet?action=kpis."]
  ];
  d.getRange(1, 1, rows.length, 2).setValues(rows);
  d.setColumnWidth(1, 320);
  d.setColumnWidth(2, 140);
}
