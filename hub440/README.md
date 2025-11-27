# Multi-Vendor Bills Processor

Automated bill processing system for Anthropic, AWS, and Google Workspace invoices. Extracts data from emails, parses PDF attachments, and populates Google Sheets with complete invoice details.

## 🎯 Features

- ✅ **Automatic PDF Parsing**: Extracts amounts from AWS/Google PDF invoices using OCR
- ✅ **Multi-Vendor Support**: Anthropic, AWS, Google Workspace
- ✅ **Multiple Document Types**: Invoices, Credit Notes, Marketplace invoices
- ✅ **Duplicate Detection**: Prevents reprocessing based on receipt number + subject
- ✅ **Smart Attachment Management**: Structured filenames with hyperlinked spreadsheet entries
- ✅ **Multi-Language**: Handles Czech and English invoices
- ✅ **Automated Processing**: Optional weekly triggers

## 📄 Supported Document Types

| Vendor | Type | Subject Contains | Category |
|--------|------|------------------|----------|
| **Anthropic** | Receipt | `Your receipt from Anthropic, PBC #` | Subscription/Credits |
| **Anthropic** | Credit Note | `Credit note from Anthropic, PBC` | Credit Note (negative) |
| **Anthropic** | Refund | `Your refund from Anthropic` | ⚠️ SKIPPED (duplicate) |
| **AWS** | Invoice | `Amazon Web Services Invoice Available` | Cloud Services |
| **AWS** | Tax Invoice | `Amazon Web Services Tax Invoice Available` | AWS Marketplace |
| **Google** | Invoice | `Google Workspace: Your invoice` | Subscription |

## 📋 Quick Start

### 1. Enable Drive API (REQUIRED)

**This is critical for PDF parsing!**

1. Open Apps Script Editor → Left sidebar
2. Click **"Services"** (+ icon)
3. Find **"Drive API"** → Select version **"v2"** → Click **"Add"**
4. Verify "Drive" appears under Services

**Without this: "Drive is not defined" errors**

### 2. Create Gmail Labels

Create these exact labels in Gmail:
- `Bills Anthropic`
- `Bills AWS`
- `Bills Google`

Apply labels to respective vendor emails.

### 3. Configure Settings

Edit `bills.js` CONFIG section:

```javascript
const CONFIG = {
  SPREADSHEET_ID: 'your-spreadsheet-id-here',
  SHEET_NAME: 'anthropic',  // Your sheet name
  DRIVE_FOLDER_ID: 'your-reports-folder-id',
  DRIVE_FOLDER_ID_ATTACHMENTS: 'your-attachments-folder-id',
  MAX_EMAILS: 50
};
```

### 4. Initialize & Run

```javascript
// First time setup
setupSpreadsheetHeaders()  // Creates column headers

// Process bills
processAllBills()  // Processes all labeled emails

// Optional: Automation
createWeeklyTrigger()  // Auto-run every Monday
```

## 🏗️ Architecture

### File Structure

```
bills.js                    # Main script (1116 lines)
├── Configuration           # Lines 31-46
├── Main Processing         # Lines 48-163
├── Label Processing        # Lines 165-327
├── Vendor Parsers          # Lines 329-633
│   ├── parseAnthropicBill  # Lines 329-388
│   ├── parseAWSBill        # Lines 391-522
│   └── parseGoogleBill     # Lines 525-633
├── PDF Extraction          # Lines 635-770
│   ├── extractTextFromPDF  # Lines 661-705 (Drive OCR)
│   └── extractAmountFromPDFText  # Lines 713-770
├── Helper Functions        # Lines 772-838
├── Test Functions          # Lines 884-966
└── Automation Setup        # Lines 968-1061

README.md                   # This file
```

### Data Flow

```
Gmail Labels
    ↓
processAllBills()
    ↓
processLabelEmails() (per vendor)
    ↓
├─→ Parse email body (vendor-specific parser)
├─→ Extract invoice number from email/PDF filename
├─→ Check for duplicates
└─→ Process attachments
    ├─→ Save PDFs to Drive
    └─→ If amount missing:
        ├─→ extractTextFromPDF() [Drive OCR]
        └─→ extractAmountFromPDFText()
    ↓
Update Spreadsheet
├─→ Write data (columns A-L)
└─→ Add hyperlinked filenames (column M)
```

### Spreadsheet Columns

| Column | Name | Description |
|--------|------|-------------|
| A | Date | Invoice date (YYYY-MM-DD) |
| B | Receipt Number | Unique invoice/receipt ID |
| C | Company | Vendor name (Anthropic, AWS, Google) |
| D | Amount | Invoice amount (EUR) |
| E | Description | Service description |
| F | Payment Method | Payment account or card (****XXXX) |
| G | Invoice Number | Official invoice number |
| H | Billing Period | Service period |
| I | Category | Credits/Subscription/Cloud Services |
| J | Subject | Email subject line |
| K | Sender Email | Vendor email address |
| L | Attachments | Number of attachments |
| M | Attachment Names | Hyperlinked PDF filenames |

## 🔍 How It Works

### Email Processing

1. **Reads labeled emails** from Gmail (up to MAX_EMAILS per label)
2. **Extracts metadata** from latest message in thread
3. **Parses vendor-specific data** using custom parsers
4. **Checks for duplicates** using receipt number + subject

### PDF Parsing (Key Innovation)

When amounts are missing from email body (common for AWS/Google):

1. **Save PDF temporarily** to Google Drive
2. **Convert to Google Doc** with OCR enabled (Drive API)
3. **Extract text** using DocumentApp
4. **Parse amount** using vendor-specific regex patterns
5. **Clean up** temporary files

### Duplicate Detection

```javascript
uniqueKey = `${receiptNumber}|${subject}`
```

Prevents reprocessing by tracking receipt number + subject combinations.

## 🛠️ Development Guide

### Adding a New Vendor

1. **Add label to CONFIG**:
```javascript
LABELS: {
  ANTHROPIC: 'Bills Anthropic',
  AWS: 'Bills AWS',
  GOOGLE: 'Bills Google',
  NEWVENDOR: 'Bills NewVendor'  // Add this
}
```

2. **Create parser function**:
```javascript
function parseNewVendorBill(subject, body, emailDate) {
  const cleanBody = body.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();

  let parsedData = {
    date: Utilities.formatDate(emailDate, Session.getScriptTimeZone(), 'yyyy-MM-dd'),
    receiptNumber: '',
    company: 'NewVendor Name',
    amount: '',
    description: '',
    paymentMethod: '',
    invoiceNumber: '',
    billingPeriod: '',
    category: 'Category Name'
  };

  // Add extraction patterns here
  // ...

  return parsedData;
}
```

3. **Add to switch statement** (bills.js:176-189):
```javascript
case 'NEWVENDOR':
  parsedData = parseNewVendorBill(subject, body, date);
  break;
```

4. **Add PDF patterns** (if needed) in `extractAmountFromPDFText()`:
```javascript
else if (vendor === 'NEWVENDOR') {
  amountPatterns = [
    // Add vendor-specific patterns
  ];
}
```

5. **Update PDF extraction trigger** (bills.js:278):
```javascript
if (!parsedData.amount && firstPdfBlob &&
    (vendorKey === 'AWS' || vendorKey === 'GOOGLE' || vendorKey === 'NEWVENDOR')) {
```

### Adding a New Document Type to Existing Vendor

This is needed when a vendor sends a different email format (e.g., credit notes, marketplace invoices).

**Example: Adding Anthropic Credit Notes**

1. **Identify the email pattern**:
   - Get sample email subject: `"Credit note from Anthropic, PBC for invoice #1YDHSHFS-0001"`
   - Get sample PDF attachment: `CreditNote-1YDHSHFS-0001-CN-01.pdf`
   - Note unique identifiers (receipt number format, keywords)

2. **Update the vendor parser** (e.g., `parseAnthropicBill()`):
   ```javascript
   // Add detection at the start of parser
   const isCreditNote = subject.toLowerCase().includes('credit note from anthropic');

   if (isCreditNote) {
     // Extract credit note number from body
     const creditNoteMatch = cleanBody.match(/Credit Note[:\s]*([A-Z0-9]+-\d+-CN-\d+)/i);
     if (creditNoteMatch) {
       parsedData.receiptNumber = creditNoteMatch[1];
     }

     // Extract amount (negative for credits)
     const amountMatch = cleanBody.match(/\$\s*([\d,.]+)\s*refunded/i);
     if (amountMatch) {
       parsedData.amount = -parseFloat(amountMatch[1]); // Negative!
     }

     parsedData.description = 'Credit Note';
     parsedData.category = 'Credit Note';
     return parsedData;
   }

   // ... rest of regular invoice parsing
   ```

3. **Add attachment filename extraction** in `processLabelEmails()` (~line 240):
   ```javascript
   // If credit note has no receipt number, extract from PDF filename
   if (vendorKey === 'ANTHROPIC' && parsedData && !parsedData.receiptNumber &&
       subject.toLowerCase().includes('credit note')) {
     try {
       const attachments = latestMessage.getAttachments();
       for (let attachment of attachments) {
         const attachmentName = attachment.getName();
         // Pattern: CreditNote-1YDHSHFS-0001-CN-01.pdf
         const match = attachmentName.match(/CreditNote-([A-Z0-9]+-\d+-CN-\d+)/i);
         if (match) {
           parsedData.receiptNumber = match[1];
           break;
         }
       }
     } catch (e) {
       Logger.log(`Error extracting from attachment: ${e.toString()}`);
     }
   }
   ```

4. **Add test case** in `testAllParsers()`:
   ```javascript
   {
     name: "Credit Note",
     subject: "Credit note from Anthropic, PBC for invoice #1YDHSHFS-0001",
     body: "Credit Note 1YDHSHFS-0001-CN-01 $1.05 refunded...",
     date: new Date('2025-10-15')
   }
   ```

5. **Handle duplicate emails** (if vendor sends multiple emails for same transaction):
   ```javascript
   // Skip refund emails - they duplicate credit notes
   const isRefund = subject.toLowerCase().includes('refund from anthropic');
   if (isRefund) {
     Logger.log(`Skipping duplicate: ${subject}`);
     return parsedData; // Empty receiptNumber = skipped
   }
   ```

**Key patterns used in this codebase:**

| Vendor | Document Type | Subject Pattern | Receipt Number Source |
|--------|--------------|-----------------|----------------------|
| Anthropic | Receipt | `Your receipt from Anthropic, PBC #XXXX-XXXX-XXXX` | Subject |
| Anthropic | Credit Note | `Credit note from Anthropic, PBC for invoice...` | PDF filename |
| Anthropic | Refund | `Your refund from Anthropic, PBC #XXXX-XXXX` | SKIPPED (duplicate) |
| AWS | Invoice | `Amazon Web Services Invoice Available [Invoice ID: EUINCZ25-...]` | Subject |
| AWS | Tax Invoice | `Amazon Web Services Tax Invoice Available` | PDF filename |
| Google | Invoice | `Google Workspace: Your invoice is available...` | PDF filename |

### Modifying Parsing Logic

**Email Body Parsing:**
- Edit vendor-specific parser functions
- Use regex patterns on `cleanBody` variable
- Test with `testAllParsers()` function

**PDF Parsing:**
- Update patterns in `extractAmountFromPDFText()`
- Add debug logging to see extracted text:
  ```javascript
  Logger.log(`PDF text: ${cleanText}`);
  ```

### Testing

```javascript
// Test individual parsers
testAllParsers()

// Test specific vendor
processAnthropicBills()
processAWSBills()
processGoogleBills()

// Full test
processAllBills()
```

Check logs: `View > Logs` or `Ctrl+Enter`

## ⚠️ Common Pitfalls & Solutions

### 1. Drive API Not Enabled
**Error**: `ReferenceError: Drive is not defined`

**Solution**: Add Drive API service (see Quick Start #1)

### 2. Blob Handling Issues
**Error**: `Cannot read properties of undefined (reading 'copyBlob')`

**Issue**: `attachment.copyBlob()` returns a Blob, not an Attachment

**Solution**:
```javascript
const pdfBlob = attachment.copyBlob();  // Already a Blob
pdfBlob.setName('filename.pdf');        // Use directly
// NOT: pdfBlob.copyBlob().setName()    // ❌ Wrong
```

### 3. setName Returns Blob (Not Void)
**Issue**: `setName()` modifies AND returns the blob

**Correct**:
```javascript
const namedBlob = pdfBlob.setName('file.pdf');  // Returns blob
```

### 4. Drive API Method Confusion
**Wrong**: `Drive.Files.insert()` (doesn't work in v2)

**Correct**: `Drive.Files.copy()` for PDF→Doc conversion

### 5. Duplicate Key Uniqueness
**Issue**: Receipt number alone may not be unique

**Solution**: Use compound key `receiptNumber|subject`

### 6. Attachment Links vs Names
**Issue**: Column M shows "File 1, File 2" instead of actual names

**Solution**: Store `{name, url}` objects in `attachmentData` array (lines 228-266)

### 7. Amount Parsing Edge Cases
**Issues**:
- European format: `10,53 €` vs US format: `$10.53`
- Thousands separator: `1,234.56` vs `1 234,56`

**Solution**: Normalize before parsing (lines 750-757)
```javascript
let amount = match[1].replace(/\s/g, '');
if (amount.includes(',') && !amount.includes('.')) {
  amount = amount.replace(',', '.');  // EU format
}
```

### 8. PDF OCR Quality
**Issue**: Some PDFs have poor text extraction

**Solutions**:
- Check PDF text in logs: `Logger.log(cleanText)`
- Add more lenient patterns
- Fall back to manual entry if needed

### 9. Performance & Quotas
**Drive API quota**: 1000 requests/100 seconds

**Solution**:
- Script processes ~5-10 invoices per run (well within limits)
- Each PDF = 2 Drive API calls (create file + convert)
- Use `MAX_EMAILS` to limit batch size

### 10. Deprecated MimeType
**Warning**: `MimeType.PLAIN_TEXT` deprecated

**Solution**: Use string directly: `'text/plain'`

## 🐛 Debugging Tips

### Enable Detailed Logging

Add to extraction functions:
```javascript
Logger.log(`Processing: ${subject}`);
Logger.log(`Parsed amount: ${parsedData.amount}`);
Logger.log(`PDF text: ${pdfText.substring(0, 500)}`);
```

### Check Execution Logs

1. Apps Script Editor → View → Logs
2. Or use `Ctrl+Enter` after execution
3. Look for:
   - "Extracted amount from PDF: X"
   - "Successfully extracted amount"
   - Error messages with stack traces

### Test Individual Components

```javascript
// Test email parsing only
const testSubject = "Your receipt from Anthropic #1234-5678-9012";
const testBody = "Receipt number 1234-5678-9012 Amount paid 180.00";
const result = parseAnthropicBill(testSubject, testBody, new Date());
Logger.log(JSON.stringify(result, null, 2));

// Test PDF extraction only
const blob = DriveApp.getFileById('pdf-file-id').getBlob();
const text = extractTextFromPDF(blob, 'test.pdf');
Logger.log(text);
```

### Verify Drive API

```javascript
// Check if Drive API is available
Logger.log(typeof Drive);  // Should be "object", not "undefined"
```

## 📊 Performance Notes

### Execution Times (Typical)

- Email processing: ~1-2 seconds per email
- PDF OCR: ~5-7 seconds per PDF
- Total per invoice with PDF: ~8-10 seconds

### Optimization Tips

1. **Reduce MAX_EMAILS** for faster testing
2. **Process one vendor at a time** during development
3. **Reuse parsed data** - don't re-parse duplicates
4. **Clean up temp files** to avoid Drive clutter

## 🔄 Maintenance

### Regular Tasks

- **Check logs weekly** for extraction errors
- **Monitor Drive folders** for temp file buildup
- **Review failed extractions** and update patterns
- **Test with new invoice formats** as vendors change

### Updating Patterns

When vendor changes invoice format:

1. Get sample email → Apply label
2. Run `processAllBills()`
3. Check logs for "No amount pattern matched"
4. Find PDF text sample in logs
5. Update regex patterns in parser
6. Test with `testAllParsers()`

## 📚 Resources

### Google Apps Script APIs

- [DriveApp](https://developers.google.com/apps-script/reference/drive)
- [GmailApp](https://developers.google.com/apps-script/reference/gmail)
- [SpreadsheetApp](https://developers.google.com/apps-script/reference/spreadsheet)
- [Drive API v2](https://developers.google.com/drive/api/v2/reference)

### Regex Testing

- [regex101.com](https://regex101.com/) - Test patterns
- Choose "JavaScript" flavor

## 🚀 Future Enhancements

### Potential Improvements

1. **Multi-currency support** - Handle USD, GBP, etc.
2. **Email notifications** - Alert on failed extractions
3. **Dashboard** - Summary stats in separate sheet
4. **Custom fields** - Project codes, cost centers
5. **Batch OCR** - Process multiple PDFs in parallel
6. **Archive old bills** - Move processed emails to Archive label
7. **Export formats** - CSV, JSON for accounting software
8. **Vendor auto-detection** - Classify by sender email

### Code Improvements

1. **Modularize parsers** - Separate files per vendor
2. **Add unit tests** - Test parsers independently
3. **Error handling** - Retry logic for Drive API
4. **Configuration UI** - HTML sidebar for settings
5. **Logging framework** - Structured logs with levels

## 🤝 Contributing

### Code Style

- Use 2-space indentation
- Add JSDoc comments for functions
- Log important operations
- Clean up temp files
- Validate parsed data before returning

### Testing Changes

1. Test with small MAX_EMAILS (5-10)
2. Check logs for errors
3. Verify spreadsheet output
4. Test duplicate detection
5. Check Drive folder for proper file naming

---

## 📝 Version History

- **v1.0** - Initial multi-vendor support (Anthropic, AWS, Google)
- **v1.1** - Added PDF OCR extraction using Drive API
- **v1.2** - Fixed blob handling and improved error handling
- **v1.3** - Added hyperlinked attachment names
- **v1.4** - Enhanced debugging and pattern matching
- **v1.5** - Added Anthropic Credit Notes and AWS Marketplace Tax Invoices
  - New document types: Credit Notes (negative amounts), Marketplace Tax Invoices
  - Attachment filename extraction for receipt numbers
  - Skip duplicate refund emails

---

**Last Updated**: 2025-11-27
**Status**: ✅ Fully Operational
