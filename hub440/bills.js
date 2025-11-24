function processAllBills() {
  // Configuration
  const LABEL_NAME = 'Bills Anthropic';
  const SPREADSHEET_ID = '1my3him8rFe6g9GYReOjKUCi1Ua2MtQM364DbCTowONE';
  const SHEET_NAME = 'anthropic';
  const DRIVE_FOLDER_ID = '13wGFkzVVjtFAb6iwIGgVBtWxzjMWoAjA'; // Summary reports folder
  const DRIVE_FOLDER_ID_ATTACHMENTS = '1jIjJpNG4enG8lv4tCBMm2w_qL-a5m0sm'; // Attachments folder
  const MAX_EMAILS = 50;
  
  try {
    // Get Gmail label
    const label = GmailApp.getUserLabelByName(LABEL_NAME);
    if (!label) {
      Logger.log(`Label "${LABEL_NAME}" not found`);
      return;
    }
    
    // Get spreadsheet
    const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = spreadsheet.getSheetByName(SHEET_NAME);
    if (!sheet) {
      Logger.log(`Sheet "${SHEET_NAME}" not found`);
      return;
    }
    
    // Get Drive folders
    const folder = DriveApp.getFolderById(DRIVE_FOLDER_ID);
    const attachmentsFolder = DriveApp.getFolderById(DRIVE_FOLDER_ID_ATTACHMENTS);
    
    // Get existing data to avoid duplicates - check both receipt number and subject
    const existingData = sheet.getDataRange().getValues();
    const existingEntries = new Set();
    
    // Create unique keys using receipt number + subject for better duplicate detection
    for (let i = 1; i < existingData.length; i++) {
      if (existingData[i][1] && existingData[i][9]) { // Receipt (col B) + Subject (col J)
        const uniqueKey = `${existingData[i][1]}|${existingData[i][9]}`;
        existingEntries.add(uniqueKey);
      }
    }
    
    // Get email threads
    const threads = label.getThreads(0, MAX_EMAILS);
    Logger.log(`Found ${threads.length} email threads`);
    
    let processedEmails = [];
    let newSpreadsheetEntries = [];
    let totalAttachmentsSaved = 0;
    
    // Process each thread
    threads.forEach((thread, index) => {
      const messages = thread.getMessages();
      const latestMessage = messages[messages.length - 1];
      
      const subject = thread.getFirstMessageSubject();
      const body = latestMessage.getPlainBody();
      const date = latestMessage.getDate();
      const sender = latestMessage.getFrom();
      
      // Parse the standardized bill data
      const parsedData = parseAnthropicBill(subject, body, date);
      
      if (parsedData && parsedData.receiptNumber) {
        // Save attachments for this message
        let attachmentCount = 0;
        let attachmentLinks = [];
        
        try {
          const attachments = latestMessage.getAttachments();
          if (attachments && attachments.length > 0) {
            attachments.forEach((attachment, attIndex) => {
              try {
                const attachmentName = attachment.getName();
                const attachmentBlob = attachment.copyBlob();
                
                // Create filename: Date_Receipt#_OriginalName.ext
                const fileExtension = attachmentName.substring(attachmentName.lastIndexOf('.'));
                const baseName = attachmentName.substring(0, attachmentName.lastIndexOf('.')) || attachmentName;
                const newFileName = `${parsedData.date}_${parsedData.receiptNumber}_${baseName}${fileExtension}`;
                
                // Check if file already exists to avoid duplicates
                const existingFiles = attachmentsFolder.getFilesByName(newFileName);
                let savedFile;
                
                if (existingFiles.hasNext()) {
                  // File already exists, get its URL
                  savedFile = existingFiles.next();
                  Logger.log(`Attachment already exists: ${newFileName}`);
                } else {
                  // Save new file
                  savedFile = attachmentsFolder.createFile(attachmentBlob);
                  savedFile.setName(newFileName);
                  totalAttachmentsSaved++;
                  Logger.log(`Saved new attachment: ${newFileName}`);
                }
                
                attachmentCount++;
                attachmentLinks.push(savedFile.getUrl());
                
              } catch (e) {
                Logger.log(`Error saving attachment: ${e.toString()}`);
              }
            });
          }
        } catch (e) {
          Logger.log(`Error processing attachments for email ${index + 1}: ${e.toString()}`);
        }
        
        // Add attachment data to parsedData so it's available for the spreadsheet
        parsedData.attachmentCount = attachmentCount;
        parsedData.attachmentLinks = attachmentLinks.join(', ');
        
        // Add to processed emails for summary report
        processedEmails.push({
          index: index + 1,
          subject: subject,
          sender: sender,
          senderEmail: extractEmailFromSender(sender),
          date: parsedData.date,
          parsedData: parsedData,
          attachmentCount: parsedData.attachmentCount || 0,
          attachmentLinks: parsedData.attachmentLinks || '',
          rawContent: body.substring(0, 1000) // Truncate for summary
        });
        
        // Add to spreadsheet if not duplicate
        const uniqueKey = `${parsedData.receiptNumber}|${subject}`;
        if (!existingEntries.has(uniqueKey)) {
          newSpreadsheetEntries.push([
            parsedData.date,
            parsedData.receiptNumber,
            parsedData.company,
            parsedData.amount,
            parsedData.description,
            parsedData.paymentMethod,
            parsedData.invoiceNumber,
            parsedData.billingPeriod,
            parsedData.category,
            subject,  // Column J: Subject
            extractEmailFromSender(sender),  // Column K: Sender Email
            parsedData.attachmentCount || 0,  // Column L: Attachment Count
            parsedData.attachmentLinks || ''  // Column M: Attachment Links
          ]);
        }
      }
    });
    
    // Create and save summary report to Drive
    const summaryReport = createSummaryReport(processedEmails, LABEL_NAME, totalAttachmentsSaved);
    const fileName = `Email_Summary_${LABEL_NAME.replace(/\s+/g, '_')}_${Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd')}.txt`;
    folder.createFile(fileName, summaryReport, MimeType.PLAIN_TEXT);
    Logger.log(`Summary report saved to Drive: ${fileName}`);
    
    // Add new entries to spreadsheet
    if (newSpreadsheetEntries.length > 0) {
      const lastRow = sheet.getLastRow();
      // Write to columns A-L first (without links)
      const entriesWithoutLinks = newSpreadsheetEntries.map(row => row.slice(0, 12));
      sheet.getRange(lastRow + 1, 1, newSpreadsheetEntries.length, 12)
           .setValues(entriesWithoutLinks);
      
      // Now add hyperlinks in column M
      newSpreadsheetEntries.forEach((entry, index) => {
        const attachmentLinks = entry[12]; // Column M data (index 12)
        if (attachmentLinks && attachmentLinks.length > 0) {
          const urls = attachmentLinks.split(', ');
          if (urls.length === 1) {
            // Single link - use setRichTextValue for clickable link
            const richText = SpreadsheetApp.newRichTextValue()
              .setText("View Attachment")
              .setLinkUrl("View Attachment", urls[0])
              .build();
            sheet.getRange(lastRow + 1 + index, 13).setRichTextValue(richText);
          } else {
            // Multiple links - create text with each part linked
            let displayText = [];
            let linkRanges = [];
            let currentPos = 0;
            
            urls.forEach((url, urlIndex) => {
              const linkText = `File ${urlIndex + 1}`;
              if (urlIndex > 0) {
                displayText.push(', ');
                currentPos += 2;
              }
              displayText.push(linkText);
              linkRanges.push({
                start: currentPos,
                end: currentPos + linkText.length,
                url: url
              });
              currentPos += linkText.length;
            });
            
            const fullText = displayText.join('');
            const richTextBuilder = SpreadsheetApp.newRichTextValue().setText(fullText);
            linkRanges.forEach(range => {
              richTextBuilder.setLinkUrl(range.start, range.end, range.url);
            });
            sheet.getRange(lastRow + 1 + index, 13).setRichTextValue(richTextBuilder.build());
          }
        }
      });
      
      Logger.log(`Added ${newSpreadsheetEntries.length} new entries to spreadsheet (columns A-M)`);
    } else {
      Logger.log('No new entries to add to spreadsheet');
    }
    
    Logger.log(`Processing complete. Total emails processed: ${processedEmails.length}`);
    Logger.log(`Total attachments saved: ${totalAttachmentsSaved}`);
    
  } catch (error) {
    Logger.log(`Error: ${error.toString()}`);
    throw error; // Re-throw for automated error handling
  }
}

function parseAnthropicBill(subject, body, emailDate) {
  const cleanBody = body.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();
  
  let parsedData = {
    date: Utilities.formatDate(emailDate, Session.getScriptTimeZone(), 'yyyy-MM-dd'),
    receiptNumber: '',
    company: 'Anthropic, PBC',
    amount: '',
    description: '',
    paymentMethod: '',
    invoiceNumber: '',
    billingPeriod: '',
    category: ''
  };
  
  // Extract receipt number from subject (most reliable)
  const receiptMatch = subject.match(/#(\d{4}-\d{4}-\d{4})/);
  if (receiptMatch) {
    parsedData.receiptNumber = receiptMatch[1];
  }
  
  // Extract invoice number
  const invoiceMatch = cleanBody.match(/Invoice number ([A-Z0-9-]+)/i);
  if (invoiceMatch) {
    parsedData.invoiceNumber = invoiceMatch[1];
  }
  
  // Extract amount - look for "Total" or "Amount paid"
  const amountMatches = [
    cleanBody.match(/Total\s+(\d+\.\s*\d+)/i),
    cleanBody.match(/Amount paid\s+(\d+\.\s*\d+)/i),
    cleanBody.match(/(\d+\.\s*\d+)\s+Paid/i)
  ];
  
  for (let match of amountMatches) {
    if (match && match[1]) {
      // Remove spaces from amount (e.g., "180. 00" -> "180.00")
      const cleanAmount = match[1].replace(/\s+/g, '');
      parsedData.amount = parseFloat(cleanAmount);
      break;
    }
  }
  
  // Extract payment method (last 4 digits)
  const paymentMatch = cleanBody.match(/Payment method[:\s-]*\*?(\d{4})/i);
  if (paymentMatch) {
    parsedData.paymentMethod = `****${paymentMatch[1]}`;
  }
  
  // Determine bill type and extract relevant info
  if (cleanBody.includes('Max plan')) {
    parsedData.description = 'Max Plan Subscription';
    parsedData.category = 'Subscription';
    
    // Extract billing period for subscriptions
    const periodMatch = cleanBody.match(/(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2},?\s+\d{4})/);
    if (periodMatch) {
      parsedData.billingPeriod = `${periodMatch[1]} - ${periodMatch[2]}`;
    }
  } 
  else if (cleanBody.includes('Auto-recharge credits')) {
    parsedData.description = 'Auto-recharge Credits';
    parsedData.category = 'Credits';
  }
  else if (cleanBody.includes('One-time credit purchase')) {
    parsedData.description = 'One-time Credit Purchase';
    parsedData.category = 'Credits';
  }
  else {
    parsedData.description = 'Anthropic Service';
    parsedData.category = 'Other';
  }
  
  return parsedData;
}

function extractEmailFromSender(senderString) {
  // Extract email from sender string like "'Anthropic, PBC' via Projekty" <projekty@hub440.cz>
  const emailMatch = senderString.match(/<([^>]+)>/);
  if (emailMatch) {
    return emailMatch[1];
  }
  
  // If no angle brackets, check if the string itself is an email
  const directEmailMatch = senderString.match(/[\w.-]+@[\w.-]+\.\w+/);
  if (directEmailMatch) {
    return directEmailMatch[0];
  }
  
  return senderString; // Return original if no email pattern found
}

function createSummaryReport(processedEmails, labelName, totalAttachments) {
  let report = `EMAIL SUMMARY REPORT\n`;
  report += `Label: ${labelName}\n`;
  report += `Generated: ${Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss')}\n`;
  report += `Total emails processed: ${processedEmails.length}\n`;
  report += `Total attachments saved: ${totalAttachments}\n\n`;
  report += '='.repeat(50) + '\n\n';
  
  // Summary statistics
  const stats = calculateBillStatistics(processedEmails);
  report += `SUMMARY STATISTICS:\n`;
  report += `Total Amount: $${stats.totalAmount.toFixed(2)}\n`;
  report += `Average Amount: $${stats.averageAmount.toFixed(2)}\n`;
  report += `Bills by Category:\n`;
  Object.entries(stats.byCategory).forEach(([category, data]) => {
    report += `  ${category}: ${data.count} bills, $${data.total.toFixed(2)}\n`;
  });
  report += `\n${'='.repeat(50)}\n\n`;
  
  // Individual bill details
  processedEmails.forEach((email) => {
    const data = email.parsedData;
    report += `${email.index}. ${email.subject}\n`;
    report += `From: ${email.sender}\n`;
    report += `Email: ${email.senderEmail}\n`;
    report += `Date: ${email.date}\n`;
    report += `Receipt: ${data.receiptNumber}\n`;
    report += `Amount: $${data.amount}\n`;
    report += `Type: ${data.description} (${data.category})\n`;
    report += `Invoice: ${data.invoiceNumber}\n`;
    if (data.billingPeriod) {
      report += `Period: ${data.billingPeriod}\n`;
    }
    report += `Payment: ${data.paymentMethod}\n`;
    if (email.attachmentCount > 0) {
      report += `Attachments: ${email.attachmentCount} file(s)\n`;
      report += `Links: ${email.attachmentLinks}\n`;
    }
    report += '-'.repeat(30) + '\n\n';
  });
  
  return report;
}

function calculateBillStatistics(processedEmails) {
  let totalAmount = 0;
  let byCategory = {};
  
  processedEmails.forEach(email => {
    const data = email.parsedData;
    const amount = parseFloat(data.amount) || 0;
    const category = data.category || 'Other';
    
    totalAmount += amount;
    
    if (!byCategory[category]) {
      byCategory[category] = { count: 0, total: 0 };
    }
    byCategory[category].count++;
    byCategory[category].total += amount;
  });
  
  return {
    totalAmount: totalAmount,
    averageAmount: processedEmails.length > 0 ? totalAmount / processedEmails.length : 0,
    byCategory: byCategory
  };
}

function setupSpreadsheetHeaders() {
  const SPREADSHEET_ID = '1my3him8rFe6g9GYReOjKUCi1Ua2MtQM364DbCTowONE';
  const SHEET_NAME = 'anthropic';
  
  const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = spreadsheet.getSheetByName(SHEET_NAME);
  
  const headers = [
    'Date', 'Receipt Number', 'Company', 'Amount', 'Description', 
    'Payment Method', 'Invoice Number', 'Billing Period', 'Category', 
    'Subject', 'Sender Email', 'Attachments', 'Attachment Links'
  ];
  
  // Set headers in columns A through M (1-13)
  sheet.getRange(1, 1, 1, 13).setValues([headers]);
  sheet.getRange(1, 1, 1, 13).setFontWeight('bold');
  sheet.autoResizeColumns(1, 13);
  
  Logger.log('Headers added to spreadsheet (columns A-M reserved for auto-parsing)');
}

// ===== AUTOMATION FUNCTIONS =====

function createWeeklyTrigger() {
  // Delete any existing triggers first to avoid duplicates
  deleteAllTriggers();
  
  // Create a weekly trigger that runs every Monday at 9:00 AM
  ScriptApp.newTrigger('processAllBillsWithLogging')
    .timeBased()
    .everyWeeks(1)
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(6)
    .create();
  
  Logger.log('Weekly trigger created: Every Monday at 6:00 AM');
  Logger.log('The script will automatically process bills weekly');
}

function createDailyTrigger() {
  // Alternative: Create a daily trigger (runs every day at 8:00 AM)
  deleteAllTriggers();
  
  ScriptApp.newTrigger('processAllBillsWithLogging')
    .timeBased()
    .everyDays(1)
    .atHour(8)
    .create();
  
  Logger.log('Daily trigger created: Every day at 8:00 AM');
}

function createCustomTrigger() {
  // Custom option: Twice per week (Monday and Friday at 10:00 AM)
  deleteAllTriggers();
  
  // Monday trigger
  ScriptApp.newTrigger('processAllBillsWithLogging')
    .timeBased()
    .everyWeeks(1)
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(10)
    .create();
  
  // Friday trigger  
  ScriptApp.newTrigger('processAllBillsWithLogging')
    .timeBased()
    .everyWeeks(1)
    .onWeekDay(ScriptApp.WeekDay.FRIDAY)
    .atHour(10)
    .create();
  
  Logger.log('Custom triggers created: Monday and Friday at 10:00 AM');
}

function deleteAllTriggers() {
  // Clean up existing triggers to avoid duplicates
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'processAllBillsWithLogging') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  Logger.log('Existing triggers deleted');
}

function listActiveTriggers() {
  // Check what triggers are currently active
  const triggers = ScriptApp.getProjectTriggers();
  Logger.log(`Active triggers (${triggers.length} total):`);
  
  triggers.forEach((trigger, index) => {
    const functionName = trigger.getHandlerFunction();
    const source = trigger.getTriggerSource();
    const eventType = trigger.getEventType();
    
    Logger.log(`${index + 1}. Function: ${functionName}`);
    Logger.log(`   Source: ${source}`);
    Logger.log(`   Event: ${eventType}`);
    
    if (source === ScriptApp.TriggerSource.CLOCK) {
      Logger.log(`   Schedule: ${trigger.getTriggerSourceId()}`);
    }
  });
}

function processAllBillsWithLogging() {
  // Enhanced version with better logging for automated runs
  try {
    Logger.log(`=== AUTOMATED RUN STARTED: ${new Date()} ===`);
    
    processAllBills();
    
    Logger.log(`=== AUTOMATED RUN COMPLETED: ${new Date()} ===`);
    
    // Optional: Send notification email on completion
    sendCompletionNotification();
    
  } catch (error) {
    Logger.log(`ERROR in automated run: ${error.toString()}`);
    
    // Optional: Send error notification
    sendErrorNotification(error);
  }
}

function sendCompletionNotification() {
  // Optional: Email notification when processing completes
  const email = Session.getActiveUser().getEmail();
  const subject = 'Bills Processing Complete';
  const body = `Your weekly bill processing has completed successfully at ${new Date()}.
  
Check your Google Sheets and Drive folders for updated data.

- Spreadsheet: https://docs.google.com/spreadsheets/d/1my3him8rFe6g9GYReOjKUCi1Ua2MtQM364DbCTowONE
- Summary folder: https://drive.google.com/drive/folders/13wGFkzVVjtFAb6iwIGgVBtWxzjMWoAjA
- Attachments folder: https://drive.google.com/drive/folders/1jIjJpNG4enG8lv4tCBMm2w_qL-a5m0sm`;
  
  try {
    GmailApp.sendEmail(email, subject, body);
    Logger.log('Completion notification sent');
  } catch (error) {
    Logger.log(`Failed to send notification: ${error.toString()}`);
  }
}

function sendErrorNotification(error) {
  // Optional: Email notification when errors occur
  const email = Session.getActiveUser().getEmail();
  const subject = 'Bills Processing Error';
  const body = `There was an error in your automated bill processing:
  
Error: ${error.toString()}
Time: ${new Date()}

Please check your Apps Script logs for more details.
Project: https://script.google.com`;
  
  try {
    GmailApp.sendEmail(email, subject, body);
    Logger.log('Error notification sent');
  } catch (error) {
    Logger.log(`Failed to send error notification: ${error.toString()}`);
  }
}

// ===== TESTING FUNCTIONS =====

function testAnthropicParsing() {
  // Test with your actual email data
  const testCases = [
    {
      subject: "Your receipt from Anthropic, PBC #2200-5755-9758",
      body: "Receipt number 2200-5755-9758 Invoice number DBBYCVSC-0002 Payment method - 3708 Sep 14 Oct 14, 2025 Max plan - 20x Qty 1 180. 00 Total 180. 00 Amount paid 180. 00",
      sender: "'Anthropic, PBC' via Projekty <projekty@hub440.cz>",
      date: new Date('2025-09-14')
    },
    {
      subject: "Your receipt from Anthropic, PBC #2918-5547-7290", 
      body: "Receipt number 2918-5547-7290 Invoice number 74EU1YAA-0013 Payment method - 3708 Auto-recharge credits Qty 1 40. 66 Total 40. 66 Amount paid 40. 66",
      sender: "'Anthropic, PBC' via Projekty <projekty@hub440.cz>",
      date: new Date('2025-09-07')
    },
    {
      subject: "Your receipt from Anthropic, PBC #2126-0850-1152",
      body: "Receipt number 2126-0850-1152 Invoice number 2U9SPF2N-0006 Payment method - 3708 One-time credit purchase Qty 1 25. 00 Total excluding tax 25. 00 Total 25. 00 Amount paid 25. 00",
      sender: "'Anthropic, PBC' via Projekty <projekty@hub440.cz>",
      date: new Date('2025-08-15')
    }
  ];
  
  testCases.forEach((testCase, index) => {
    Logger.log(`\nTest Case ${index + 1} (Date: ${Utilities.formatDate(testCase.date, Session.getScriptTimeZone(), 'yyyy-MM-dd')}):`);
    const result = parseAnthropicBill(testCase.subject, testCase.body, testCase.date);
    const extractedEmail = extractEmailFromSender(testCase.sender);
    Logger.log(`Parsed Data: ${JSON.stringify(result, null, 2)}`);
    Logger.log(`Extracted Email: ${extractedEmail}`);
    Logger.log(`Formatted Date: ${result.date}`);
  });
}

function createDriveFolder() {
  // Helper function to create the folder if it doesn't exist
  const folderName = 'Bills_Email_Summaries';
  const folder = DriveApp.createFolder(folderName);
  Logger.log(`Created folder: ${folderName}`);
  Logger.log(`Folder ID: ${folder.getId()}`);
  Logger.log(`Folder URL: ${folder.getUrl()}`);
}

function setup() {
  Logger.log('=== STANDARDIZED BILLS PARSER SETUP WITH ATTACHMENTS ===');
  Logger.log('1. Update configuration variables if needed');
  Logger.log('2. Run setupSpreadsheetHeaders() to add column headers');
  Logger.log('3. Run testAnthropicParsing() to verify parsing logic');
  Logger.log('4. Run processAllBills() to process emails manually');
  Logger.log('5. Run createWeeklyTrigger() to set up automatic weekly processing');
  Logger.log('');
  Logger.log('AUTOMATION OPTIONS:');
  Logger.log('• createWeeklyTrigger() - Every Monday at 9:00 AM');
  Logger.log('• createDailyTrigger() - Every day at 8:00 AM');
  Logger.log('• createCustomTrigger() - Monday and Friday at 10:00 AM');
  Logger.log('• listActiveTriggers() - Show current automated schedules');
  Logger.log('• deleteAllTriggers() - Remove all automation');
  Logger.log('');
  Logger.log('Features:');
  Logger.log('• Standardized parsing for Max plan, Auto-recharge, One-time purchases');
  Logger.log('• Automatic categorization and statistics');
  Logger.log('• Duplicate prevention in spreadsheet');
  Logger.log('• Summary reports saved to Google Drive');
  Logger.log('• Structured data extraction for all Anthropic bill types');
  Logger.log('• Sender email extraction and tracking');
  Logger.log('• Automated weekly processing with notifications');
  Logger.log('• NEW: Attachment saving to Drive folder');
  Logger.log('');
  Logger.log('Expected spreadsheet columns (A-M reserved for auto-parsing):');
  Logger.log('A: Date, B: Receipt#, C: Company, D: Amount, E: Description');
  Logger.log('F: Payment Method, G: Invoice#, H: Billing Period, I: Category');
  Logger.log('J: Subject, K: Sender Email, L: Attachment Count, M: Attachment Names');
  Logger.log('');
  Logger.log('IMPORTANT: Columns N onwards are free for manual edits - they will not be overwritten');
}