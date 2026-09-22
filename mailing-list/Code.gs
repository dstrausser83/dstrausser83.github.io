// Dead Brands mailing list → Google Sheet
// Paste this into a Google Apps Script project bound to your sheet (see SETUP.md).

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
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
  } catch (err) {
    return json({ ok: false, error: "server" });
  }
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
