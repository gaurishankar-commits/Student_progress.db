/**
 * Google Apps Script for Student Academic Progression & Portfolio DBMS Sync
 * Supports dynamic spreadsheet_id or defaults to colleague's sheet.
 */

function testSync() {
  var targetId = "1O2rglXTUP5a1iDUYqXT7fn0HGuFzGxNuGkOfEO2e40c";
  var ss;
  try {
    ss = SpreadsheetApp.openById(targetId);
  } catch (e) {
    ss = SpreadsheetApp.getActiveSpreadsheet();
  }
  var sheet = ss.getSheetByName("Students") || ss.insertSheet("Students");
  Logger.log("Successfully connected to sheet: " + ss.getName());
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    if (data.action === "sync_all_tables" && data.tables) {
      var targetId = data.spreadsheet_id || "1O2rglXTUP5a1iDUYqXT7fn0HGuFzGxNuGkOfEO2e40c";
      var ss;
      try {
        ss = SpreadsheetApp.openById(targetId);
      } catch (errOpen) {
        ss = SpreadsheetApp.getActiveSpreadsheet();
      }
      
      for (var tableName in data.tables) {
        var rows = data.tables[tableName];
        var sheet = ss.getSheetByName(tableName) || ss.insertSheet(tableName);
        sheet.clear();
        
        if (rows && rows.length > 0) {
          var headers = Object.keys(rows[0]);
          var values = [headers];
          for (var i = 0; i < rows.length; i++) {
            var row = [];
            for (var j = 0; j < headers.length; j++) {
              var val = rows[i][headers[j]];
              row.push(val === null || val === undefined ? "" : val);
            }
            values.push(row);
          }
          sheet.getRange(1, 1, values.length, headers.length).setValues(values);
          sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold").setBackground("#e2e8f0");
          sheet.autoResizeColumns(1, headers.length);
        }
      }
      return ContentService.createTextOutput(JSON.stringify({status: "SUCCESS", message: "All tables synchronized"})).setMimeType(ContentService.MimeType.JSON);
    }
    return ContentService.createTextOutput(JSON.stringify({status: "SUCCESS"})).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({status: "ERROR", error: err.toString()})).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({status: "SUCCESS", app: "Student Progression Sync Webhook"})).setMimeType(ContentService.MimeType.JSON);
}
