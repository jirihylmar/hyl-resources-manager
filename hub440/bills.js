/**
 * MULTI-VENDOR BILLS PROCESSOR
 * Processes bills from: Anthropic, AWS, Google Workspace
 *
 * Gmail Labels: "Bills Anthropic", "Bills AWS", "Bills Google"
 * All data goes to the same spreadsheet with Company column distinguishing vendors
 *
 * SUPPORTED DOCUMENT TYPES:
 * - Anthropic: Regular receipts (#XXXX-XXXX-XXXX) and Credit Notes (CN-XX)
 *   Note: Refund emails are skipped (duplicates of credit notes)
 * - AWS: Regular invoices (EUINCZ25-...) and Marketplace Tax Invoices (IINCZ25-...)
 * - Google: Workspace invoices
 *
 * FEATURES:
 * - Automatic extraction of invoice details from emails
 * - PDF parsing using Drive OCR to extract amounts when missing from email body
 * - Duplicate detection to prevent reprocessing
 * - Automatic attachment saving to Google Drive with structured filenames
 * - Hyperlinked attachment names in spreadsheet
 * - Credit note handling (negative amounts)
 *
 * ⚠️ CRITICAL SETUP REQUIREMENT ⚠️
 *
 * To enable PDF parsing, you MUST add the Drive API service:
 * 1. In Apps Script Editor left sidebar, click "Services" (+ icon)
 * 2. Find "Drive API" in the list
 * 3. Select version "v2"
 * 4. Click "Add"
 *
 * Without this, you'll get "Drive is not defined" errors!
 * See README.md for complete setup and development guide.
 *
 * OTHER REQUIREMENTS:
 * - Gmail labels: "Bills Anthropic", "Bills AWS", "Bills Google"
 * - Google Drive folders configured in CONFIG
 */

// ===== CONFIGURATION =====
const CONFIG = {
  SPREADSHEET_ID: '1my3him8rFe6g9GYReOjKUCi1Ua2MtQM364DbCTowONE',
  SHEET_NAME: 'anthropic', // Consider renaming to 'all_bills' for clarity
  DRIVE_FOLDER_ID: '13wGFkzVVjtFAb6iwIGgVBtWxzjMWoAjA', // Summary reports folder
  DRIVE_FOLDER_ID_ATTACHMENTS: '1jIjJpNG4enG8lv4tCBMm2w_qL-a5m0sm', // Attachments folder
  MAX_EMAILS: 50,
  
  // Labels configuration
  LABELS: {
    ANTHROPIC: 'Bills Anthropic',
    AWS: 'Bills AWS',
    GOOGLE: 'Bills Google'
  }
};

// ===== MAIN PROCESSING FUNCTION =====

function processAllBills() {
  try {
    // Get spreadsheet
    const spreadsheet = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
    const sheet = spreadsheet.getSheetByName(CONFIG.SHEET_NAME);
    if (!sheet) {
      Logger.log(`Sheet "${CONFIG.SHEET_NAME}" not found`);
      return;
    }
    
    // Get Drive folders
    const folder = DriveApp.getFolderById(CONFIG.DRIVE_FOLDER_ID);
    const attachmentsFolder = DriveApp.getFolderById(CONFIG.DRIVE_FOLDER_ID_ATTACHMENTS);
    
    // Get existing data to avoid duplicates
    const existingData = sheet.getDataRange().getValues();
    const existingEntries = new Set();
    
    for (let i = 1; i < existingData.length; i++) {
      if (existingData[i][1] && existingData[i][9]) {
        const uniqueKey = `${existingData[i][1]}|${existingData[i][9]}`;
        existingEntries.add(uniqueKey);
      }
    }
    
    let allProcessedEmails = [];
    let allNewSpreadsheetEntries = [];
    let totalAttachmentsSaved = 0;
    
    // Process each label
    for (const [vendorKey, labelName] of Object.entries(CONFIG.LABELS)) {
      Logger.log(`\n=== Processing ${vendorKey} bills (Label: ${labelName}) ===`);
      
      const result = processLabelEmails(
        labelName, 
        vendorKey, 
        existingEntries, 
        attachmentsFolder
      );
      
      if (result) {
        allProcessedEmails = allProcessedEmails.concat(result.processedEmails);
        allNewSpreadsheetEntries = allNewSpreadsheetEntries.concat(result.newEntries);
        totalAttachmentsSaved += result.attachmentsSaved;
        
        // Add new entries to existing set to prevent duplicates across labels
        result.newEntries.forEach(entry => {
          const uniqueKey = `${entry[1]}|${entry[9]}`;
          existingEntries.add(uniqueKey);
        });
      }
    }
    
    // Create and save summary report to Drive
    const summaryReport = createSummaryReport(allProcessedEmails, 'All Vendors', totalAttachmentsSaved);
    const fileName = `Email_Summary_All_Vendors_${Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd')}.txt`;
    folder.createFile(fileName, summaryReport, 'text/plain');
    Logger.log(`Summary report saved to Drive: ${fileName}`);
    
    // Add new entries to spreadsheet
    if (allNewSpreadsheetEntries.length > 0) {
      const lastRow = sheet.getLastRow();
      const entriesWithoutLinks = allNewSpreadsheetEntries.map(row => row.slice(0, 12));
      sheet.getRange(lastRow + 1, 1, allNewSpreadsheetEntries.length, 12)
           .setValues(entriesWithoutLinks);
      
      // Add hyperlinks in column M
      allNewSpreadsheetEntries.forEach((entry, index) => {
        const attachmentData = entry[12]; // Array of {name, url} objects
        if (attachmentData && attachmentData.length > 0) {
          if (attachmentData.length === 1) {
            // Single attachment - use filename as link text
            const richText = SpreadsheetApp.newRichTextValue()
              .setText(attachmentData[0].name)
              .setLinkUrl(attachmentData[0].url)
              .build();
            sheet.getRange(lastRow + 1 + index, 13).setRichTextValue(richText);
          } else {
            // Multiple attachments - create comma-separated links with actual filenames
            let displayText = [];
            let linkRanges = [];
            let currentPos = 0;

            attachmentData.forEach((attachment, attIndex) => {
              const linkText = attachment.name;
              if (attIndex > 0) {
                displayText.push(', ');
                currentPos += 2;
              }
              displayText.push(linkText);
              linkRanges.push({
                start: currentPos,
                end: currentPos + linkText.length,
                url: attachment.url
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
      
      Logger.log(`Added ${allNewSpreadsheetEntries.length} new entries to spreadsheet`);
    } else {
      Logger.log('No new entries to add to spreadsheet');
    }
    
    Logger.log(`\n=== PROCESSING COMPLETE ===`);
    Logger.log(`Total emails processed: ${allProcessedEmails.length}`);
    Logger.log(`Total attachments saved: ${totalAttachmentsSaved}`);
    
  } catch (error) {
    Logger.log(`Error: ${error.toString()}`);
    throw error;
  }
}

function processLabelEmails(labelName, vendorKey, existingEntries, attachmentsFolder) {
  const label = GmailApp.getUserLabelByName(labelName);
  if (!label) {
    Logger.log(`Label "${labelName}" not found - skipping`);
    return null;
  }
  
  const threads = label.getThreads(0, CONFIG.MAX_EMAILS);
  Logger.log(`Found ${threads.length} email threads for ${labelName}`);
  
  let processedEmails = [];
  let newEntries = [];
  let attachmentsSaved = 0;
  let skippedCount = 0;
  
  threads.forEach((thread, index) => {
    const messages = thread.getMessages();
    const latestMessage = messages[messages.length - 1];
    
    const subject = thread.getFirstMessageSubject();
    const body = latestMessage.getPlainBody();
    const date = latestMessage.getDate();
    const sender = latestMessage.getFrom();
    
    // Parse based on vendor type
    let parsedData;
    switch (vendorKey) {
      case 'ANTHROPIC':
        parsedData = parseAnthropicBill(subject, body, date);
        break;
      case 'AWS':
        parsedData = parseAWSBill(subject, body, date);
        break;
      case 'GOOGLE':
        parsedData = parseGoogleBill(subject, body, date);
        break;
      default:
        Logger.log(`Unknown vendor: ${vendorKey}`);
        return;
    }

    // If Google bill has no receipt number, try to extract from PDF attachment
    if (vendorKey === 'GOOGLE' && parsedData && !parsedData.receiptNumber) {
      try {
        const attachments = latestMessage.getAttachments();
        if (attachments && attachments.length > 0) {
          for (let attachment of attachments) {
            const attachmentName = attachment.getName();
            // Extract number from PDF filename (e.g., "5396779091.pdf")
            const numberMatch = attachmentName.match(/(\d{8,})/);
            if (numberMatch) {
              parsedData.receiptNumber = numberMatch[1];
              parsedData.invoiceNumber = numberMatch[1];
              Logger.log(`Extracted invoice from filename: ${numberMatch[1]}`);
              break;
            }
          }
        }
      } catch (e) {
        Logger.log(`Error extracting invoice from attachment: ${e.toString()}`);
      }
    }

    // If Anthropic credit note has no receipt number, extract from PDF attachment filename
    // PDF filename pattern: CreditNote-1YDHSHFS-0001-CN-01.pdf
    if (vendorKey === 'ANTHROPIC' && parsedData && !parsedData.receiptNumber &&
        subject.toLowerCase().includes('credit note')) {
      try {
        const attachments = latestMessage.getAttachments();
        if (attachments && attachments.length > 0) {
          for (let attachment of attachments) {
            const attachmentName = attachment.getName();
            // Extract credit note number from filename (e.g., "CreditNote-1YDHSHFS-0001-CN-01.pdf")
            const creditNoteMatch = attachmentName.match(/CreditNote-([A-Z0-9]+-\d+-CN-\d+)/i);
            if (creditNoteMatch) {
              parsedData.receiptNumber = creditNoteMatch[1];
              Logger.log(`Extracted credit note from filename: ${creditNoteMatch[1]}`);
              break;
            }
          }
        }
      } catch (e) {
        Logger.log(`Error extracting credit note from attachment: ${e.toString()}`);
      }
    }

    // If AWS tax invoice has no receipt number, extract from PDF attachment filename
    // PDF filename pattern: IINCZ25-1376.pdf
    if (vendorKey === 'AWS' && parsedData && !parsedData.receiptNumber) {
      try {
        const attachments = latestMessage.getAttachments();
        if (attachments && attachments.length > 0) {
          for (let attachment of attachments) {
            const attachmentName = attachment.getName();
            // Extract invoice number from filename (e.g., "IINCZ25-1376.pdf" or "EUINCZ25-174255.pdf")
            const invoiceMatch = attachmentName.match(/([A-Z]{1,2}INCZ\d{2}-\d+)/i);
            if (invoiceMatch) {
              parsedData.receiptNumber = invoiceMatch[1];
              parsedData.invoiceNumber = invoiceMatch[1];
              Logger.log(`Extracted AWS invoice from filename: ${invoiceMatch[1]}`);
              break;
            }
          }
        }
      } catch (e) {
        Logger.log(`Error extracting AWS invoice from attachment: ${e.toString()}`);
      }
    }

    if (parsedData && parsedData.receiptNumber) {
      // CHECK FOR DUPLICATE FIRST - skip entire processing if already exists
      const uniqueKey = `${parsedData.receiptNumber}|${subject}`;
      if (existingEntries.has(uniqueKey)) {
        skippedCount++;
        return; // Skip this email entirely - already processed
      }

      // Only process attachments for NEW entries
      let attachmentCount = 0;
      let attachmentData = []; // Store objects with {name, url}
      let firstPdfBlob = null; // Store first PDF for amount extraction if needed

      try {
        const attachments = latestMessage.getAttachments();
        if (attachments && attachments.length > 0) {
          attachments.forEach((attachment) => {
            try {
              const attachmentName = attachment.getName();
              const attachmentBlob = attachment.copyBlob();

              // Keep first PDF for amount extraction if needed
              if (!firstPdfBlob && attachmentName.toLowerCase().endsWith('.pdf')) {
                firstPdfBlob = attachmentBlob;
              }

              // KEEP ORIGINAL NAMING CONVENTION (no vendor prefix)
              const fileExtension = attachmentName.substring(attachmentName.lastIndexOf('.'));
              const baseName = attachmentName.substring(0, attachmentName.lastIndexOf('.')) || attachmentName;
              const newFileName = `${parsedData.date}_${parsedData.receiptNumber}_${baseName}${fileExtension}`;

              const existingFiles = attachmentsFolder.getFilesByName(newFileName);
              let savedFile;

              if (existingFiles.hasNext()) {
                savedFile = existingFiles.next();
                Logger.log(`Attachment already exists: ${newFileName}`);
              } else {
                savedFile = attachmentsFolder.createFile(attachmentBlob);
                savedFile.setName(newFileName);
                attachmentsSaved++;
                Logger.log(`Saved new attachment: ${newFileName}`);
              }

              attachmentCount++;
              attachmentData.push({
                name: newFileName,
                url: savedFile.getUrl()
              });

            } catch (e) {
              Logger.log(`Error saving attachment: ${e.toString()}`);
            }
          });
        }
      } catch (e) {
        Logger.log(`Error processing attachments for email ${index + 1}: ${e.toString()}`);
      }

      // If amount is missing and we have a PDF, try to extract from PDF
      if (!parsedData.amount && firstPdfBlob && (vendorKey === 'AWS' || vendorKey === 'GOOGLE')) {
        Logger.log(`Attempting to extract amount from PDF for ${vendorKey} invoice ${parsedData.receiptNumber}`);
        try {
          const pdfText = extractTextFromPDF(firstPdfBlob, `${parsedData.receiptNumber}.pdf`);
          const extractedAmount = extractAmountFromPDFText(pdfText, vendorKey);
          if (extractedAmount) {
            parsedData.amount = extractedAmount;
            Logger.log(`Successfully extracted amount from PDF: ${extractedAmount}`);
          }
        } catch (e) {
          Logger.log(`Failed to extract amount from PDF: ${e.toString()}`);
        }
      }

      parsedData.attachmentCount = attachmentCount;
      parsedData.attachmentData = attachmentData; // Store structured data
      
      processedEmails.push({
        index: index + 1,
        subject: subject,
        sender: sender,
        senderEmail: extractEmailFromSender(sender),
        date: parsedData.date,
        parsedData: parsedData,
        attachmentCount: parsedData.attachmentCount || 0,
        attachmentData: parsedData.attachmentData || [],
        rawContent: body.substring(0, 1000)
      });

      // Add to new entries (we already checked it's not a duplicate above)
      newEntries.push([
        parsedData.date,
        parsedData.receiptNumber,
        parsedData.company,
        parsedData.amount,
        parsedData.description,
        parsedData.paymentMethod,
        parsedData.invoiceNumber,
        parsedData.billingPeriod,
        parsedData.category,
        subject,
        extractEmailFromSender(sender),
        parsedData.attachmentCount || 0,
        parsedData.attachmentData || [] // Pass the structured data
      ]);
    } else {
      // Log why the email was skipped
      Logger.log(`Skipping email "${subject}" - No receipt number found`);
      if (parsedData) {
        Logger.log(`  Invoice: ${parsedData.invoiceNumber}, Amount: ${parsedData.amount}`);
      }
    }
  });

  Logger.log(`${labelName}: ${skippedCount} already processed, ${newEntries.length} new entries`);
  
  return {
    processedEmails: processedEmails,
    newEntries: newEntries,
    attachmentsSaved: attachmentsSaved
  };
}

// ===== VENDOR-SPECIFIC PARSERS =====

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

  // Check if this is a credit note or refund
  // Subject patterns:
  // - Credit note: "Credit note from Anthropic, PBC for invoice..."
  // - Refund: "Your refund from Anthropic, PBC #XXXX-XXXX" (SKIP - duplicate of credit note)
  const isCreditNote = subject.toLowerCase().includes('credit note from anthropic');
  const isRefund = subject.toLowerCase().includes('refund from anthropic');

  // Skip refund emails - they duplicate credit notes with less detail
  if (isRefund) {
    Logger.log(`Skipping refund email (duplicate of credit note): ${subject}`);
    return parsedData; // Return without receiptNumber so it gets skipped
  }

  if (isCreditNote) {
    // Parse credit note - extract credit note number from body or subject
    // Credit note number format: 1YDHSHFS-0001-CN-01
    const creditNoteMatch = cleanBody.match(/Credit Note[:\s]*([A-Z0-9]+-\d+-CN-\d+)/i) ||
                           subject.match(/([A-Z0-9]+-\d+-CN-\d+)/i);
    if (creditNoteMatch) {
      parsedData.receiptNumber = creditNoteMatch[1];
    }

    // Extract original invoice number
    const origInvoiceMatch = cleanBody.match(/Invoice[:\s]*([A-Z0-9]+-\d{4})/i) ||
                            subject.match(/for invoice[:\s#]*([A-Z0-9]+-\d{4})/i) ||
                            subject.match(/#([A-Z0-9]+-\d{4})/i);
    if (origInvoiceMatch) {
      parsedData.invoiceNumber = origInvoiceMatch[1];
    }

    // Extract credit amount (format: $X.XX refunded or Total credit $X.XX)
    const creditAmountMatches = [
      cleanBody.match(/\$\s*([\d,.]+)\s*refunded/i),
      cleanBody.match(/Total credit\s*\$?\s*([\d,.]+)/i),
      cleanBody.match(/Adjustment total\s*\$?\s*([\d,.]+)/i)
    ];

    for (let match of creditAmountMatches) {
      if (match && match[1]) {
        const cleanAmount = match[1].replace(/[,\s]/g, '');
        parsedData.amount = -parseFloat(cleanAmount); // Negative for credit
        break;
      }
    }

    // Extract refund payment method
    const refundMethodMatch = cleanBody.match(/Refund issued\s*[-–]\s*(\w+)\s*[-–]\s*(\d{4})/i);
    if (refundMethodMatch) {
      parsedData.paymentMethod = `${refundMethodMatch[1]} ****${refundMethodMatch[2]}`;
    }

    parsedData.description = 'Credit Note';
    parsedData.category = 'Credit Note';

    return parsedData;
  }

  // Regular invoice processing
  // Extract receipt number from subject
  const receiptMatch = subject.match(/#(\d{4}-\d{4}-\d{4})/);
  if (receiptMatch) {
    parsedData.receiptNumber = receiptMatch[1];
  }

  // Extract invoice number
  const invoiceMatch = cleanBody.match(/Invoice number ([A-Z0-9-]+)/i);
  if (invoiceMatch) {
    parsedData.invoiceNumber = invoiceMatch[1];
  }

  // Extract amount
  const amountMatches = [
    cleanBody.match(/Total\s+(\d+\.\s*\d+)/i),
    cleanBody.match(/Amount paid\s+(\d+\.\s*\d+)/i),
    cleanBody.match(/(\d+\.\s*\d+)\s+Paid/i)
  ];

  for (let match of amountMatches) {
    if (match && match[1]) {
      const cleanAmount = match[1].replace(/\s+/g, '');
      parsedData.amount = parseFloat(cleanAmount);
      break;
    }
  }

  // Extract payment method
  const paymentMatch = cleanBody.match(/Payment method[:\s-]*\*?(\d{4})/i);
  if (paymentMatch) {
    parsedData.paymentMethod = `****${paymentMatch[1]}`;
  }

  // Determine bill type
  if (cleanBody.includes('Max plan')) {
    parsedData.description = 'Max Plan Subscription';
    parsedData.category = 'Subscription';

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

function parseAWSBill(subject, body, emailDate) {
  const cleanBody = body.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();

  let parsedData = {
    date: Utilities.formatDate(emailDate, Session.getScriptTimeZone(), 'yyyy-MM-dd'),
    receiptNumber: '',
    company: 'AWS',
    amount: '',
    description: '',
    paymentMethod: '',
    invoiceNumber: '',
    billingPeriod: '',
    category: 'Cloud Services'
  };

  // Check if this is an AWS Marketplace Tax Invoice
  // Subject pattern: "Amazon Web Services Tax Invoice Available ..."
  const isMarketplaceTaxInvoice = subject.toLowerCase().includes('tax invoice available');

  // Extract VAT Invoice Number
  // Formats: EUINCZ25-174255 (regular), IINCZ25-1376 (marketplace tax invoice)
  const invoicePatterns = [
    /\[Invoice ID:\s*([A-Z0-9-]+)\]/i,  // [Invoice ID: EUINCZ25-174255]
    /VAT Invoice Number[:\s]*([A-Z0-9-]+)/i,
    /Invoice Number[:\s]*([A-Z0-9-]+)/i,
    /([A-Z]{1,2}INCZ\d{2}-\d+)/i,  // EUINCZ25-174255 or IINCZ25-1376
    subject.match(/\[Invoice ID:\s*([A-Z0-9-]+)\]/i),
    cleanBody.match(/VAT Invoice Number[:\s]*([A-Z0-9-]+)/i)
  ];

  for (let pattern of invoicePatterns) {
    if (pattern) {
      const match = typeof pattern === 'object' && pattern !== null ? pattern : cleanBody.match(pattern);
      if (match && match[1]) {
        parsedData.invoiceNumber = match[1];
        parsedData.receiptNumber = match[1]; // Use invoice number as receipt number for AWS
        break;
      }
    }
  }

  // If still no invoice number found, try to extract from PDF attachment filename
  // AWS Marketplace Tax Invoice PDF names like: IINCZ25-1376.pdf
  if (!parsedData.receiptNumber) {
    const pdfInvoiceMatch = subject.match(/([A-Z]{1,2}INCZ\d{2}-\d+)/i);
    if (pdfInvoiceMatch) {
      parsedData.invoiceNumber = pdfInvoiceMatch[1];
      parsedData.receiptNumber = pdfInvoiceMatch[1];
    }
  }

  // Extract billing period (format: October 1 - October 31, 2025 or November 1 - November 30, 2025)
  const periodPatterns = [
    /billing period[:\s]*(\w+\s+\d{1,2})\s*[-–]\s*(\w+\s+\d{1,2},?\s*\d{4})/i,
    /(\w+\s+\d{1,2})\s*[-–]\s*(\w+\s+\d{1,2},?\s*\d{4})/i
  ];

  for (let pattern of periodPatterns) {
    const match = cleanBody.match(pattern);
    if (match) {
      parsedData.billingPeriod = `${match[1]} - ${match[2]}`;
      break;
    }
  }

  // Extract amounts - AWS has multiple currencies, prefer EUR or USD
  // NOTE: "Invoice Available" notification emails often don't contain amounts - only in PDF
  const amountPatterns = [
    /TOTAL AMOUNT[:\s]*EUR\s*([\d,.]+)/i,
    /TOTAL AMOUNT[:\s]*([\d,.]+)\s*EUR/i,
    /Total[:\s]*EUR\s*([\d,.]+)/i,
    /EUR\s*([\d,.]+)/i,
    /\$\s*([\d,.]+)/i,
    /USD\s*([\d,.]+)/i,
    /Amount[:\s]*€?\s*([\d,.]+)/i
  ];

  for (let pattern of amountPatterns) {
    const match = cleanBody.match(pattern);
    if (match && match[1]) {
      // Handle European number format (comma as decimal separator)
      let amount = match[1].replace(/\s/g, '');
      if (amount.includes(',') && !amount.includes('.')) {
        amount = amount.replace(',', '.');
      } else if (amount.includes(',') && amount.includes('.')) {
        amount = amount.replace(',', '');
      }
      const parsedAmount = parseFloat(amount);
      if (!isNaN(parsedAmount) && parsedAmount > 0) {
        parsedData.amount = parsedAmount;
        break;
      }
    }
  }

  if (!parsedData.amount) {
    Logger.log(`AWS: No amount found in email body for ${parsedData.invoiceNumber} - will attempt PDF extraction`);
  }

  // Set description based on invoice type
  if (isMarketplaceTaxInvoice) {
    parsedData.description = 'AWS Marketplace';
    parsedData.category = 'AWS Marketplace';
  } else {
    parsedData.description = 'AWS Cloud';
  }

  // Extract account number if available
  const accountMatch = subject.match(/\[Account:\s*(\d+)\]/i) ||
                      cleanBody.match(/Account number[:\s]*(\d+)/i) ||
                      cleanBody.match(/Account[:\s]*(\d+)/i);
  if (accountMatch) {
    parsedData.paymentMethod = `Account: ${accountMatch[1]}`;
  }

  return parsedData;
}

function parseGoogleBill(subject, body, emailDate) {
  const cleanBody = body.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();
  
  let parsedData = {
    date: Utilities.formatDate(emailDate, Session.getScriptTimeZone(), 'yyyy-MM-dd'),
    receiptNumber: '',
    company: 'Google',
    amount: '',
    description: '',
    paymentMethod: '',
    invoiceNumber: '',
    billingPeriod: '',
    category: 'Subscription'
  };
  
  // Extract invoice number (format: 5396779091)
  // Czech: "Číslo faktury" / English: "Invoice number"
  const invoicePatterns = [
    /[Čč]íslo faktury[:\s]*(\d+)/i,
    /Invoice number[:\s]*(\d+)/i,
    /Invoice[:\s#]*(\d{8,})/i,
    subject.match(/(\d{10})/),
    subject.match(/Invoice[:\s#]*(\d+)/i)
  ];
  
  for (let pattern of invoicePatterns) {
    if (pattern) {
      const match = typeof pattern === 'object' && pattern !== null ? pattern : cleanBody.match(pattern);
      if (match && match[1]) {
        parsedData.invoiceNumber = match[1];
        parsedData.receiptNumber = match[1];
        break;
      }
    }
  }
  
  // Extract customer billing number (format: 2515-3845-4639)
  const customerMatch = cleanBody.match(/[Ff]aktura[čc]ní [čc]íslo zákazníka[:\s.]*([\d-]+)/i) ||
                       cleanBody.match(/Customer (?:billing )?number[:\s]*([\d-]+)/i) ||
                       cleanBody.match(/([\d]{4}-[\d]{4}-[\d]{4})/);
  if (customerMatch) {
    parsedData.paymentMethod = `Customer: ${customerMatch[1]}`;
  }
  
  // Extract billing period (format: 1. 10. 2025 - 31. 10. 2025)
  const periodPatterns = [
    /Souhrn za\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\s*[-–]\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})/i,
    /Summary for\s*(\d{1,2}[\/.-]\s*\d{1,2}[\/.-]\s*\d{4})\s*[-–]\s*(\d{1,2}[\/.-]\s*\d{1,2}[\/.-]\s*\d{4})/i,
    /(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\s*[-–]\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})/,
    /Interval[:\s]*(\d{1,2}\.\s*\d{1,2}\.)\s*[-–]\s*(\d{1,2}\.\s*\d{1,2}\.)/i
  ];
  
  for (let pattern of periodPatterns) {
    const match = cleanBody.match(pattern);
    if (match) {
      parsedData.billingPeriod = `${match[1]} - ${match[2]}`;
      break;
    }
  }
  
  // Extract amount (format: 10,53 € or €10.53)
  // NOTE: "Invoice available" notification emails often don't contain amounts - only in PDF
  const amountPatterns = [
    /Celková částka v EUR[:\s]*([\d,.\s]+)\s*€/i,  // Czech: Total amount in EUR
    /Total amount[:\s]*(?:EUR\s*)?([\d,.\s]+)\s*€?/i,
    /EUR[:\s]*([\d,.\s]+)/i,
    /([\d]+[,.]\d{2})\s*€/,  // Match XX.XX € or XX,XX €
    /€\s*([\d,.]+)/
  ];

  for (let pattern of amountPatterns) {
    const match = cleanBody.match(pattern);
    if (match && match[1]) {
      let amount = match[1].replace(/\s/g, '').trim();
      // Handle European format (comma as decimal)
      if (amount.includes(',') && !amount.includes('.')) {
        amount = amount.replace(',', '.');
      } else if (amount.includes(',') && amount.includes('.')) {
        amount = amount.replace(',', '');
      }
      const parsedAmount = parseFloat(amount);
      if (!isNaN(parsedAmount) && parsedAmount > 0) {
        parsedData.amount = parsedAmount;
        break;
      }
    }
  }

  if (!parsedData.amount) {
    Logger.log(`Google: No amount found in email body for invoice ${parsedData.invoiceNumber} - will attempt PDF extraction`);
  }
  
  // Extract service description - Keep it simple
  const servicePatterns = [
    /Google Workspace\s+(Business\s+Standard|Business\s+Plus|Enterprise|Frontline)/i,
    /Google Workspace/i,
    /G Suite/i
  ];

  for (let pattern of servicePatterns) {
    const match = cleanBody.match(pattern);
    if (match) {
      parsedData.description = match[0].trim();
      break;
    }
  }

  if (!parsedData.description) {
    parsedData.description = 'Google Workspace';
  }
  
  return parsedData;
}

// ===== PDF PARSING HELPER =====
//
// IMPORTANT: To use PDF parsing, you must enable the Drive API service:
// 1. In Apps Script Editor, click on "Services" (+ icon on left sidebar)
// 2. Find "Drive API" and click "Add"
// 3. Select version "v2" and click "Add"
//
// This allows the script to convert PDFs to text using Google Drive's OCR
// For complete setup and development guide, see README.md

/**
 * Extracts text from a PDF file using Google Drive's OCR capabilities
 * @param {Blob} pdfBlob - The PDF file blob
 * @param {string} fileName - Name for the temporary file
 * @returns {string} - Extracted text from PDF
 */
function extractTextFromPDF(pdfBlob, fileName) {
  try {
    // Check if Drive API is available
    if (typeof Drive === 'undefined') {
      Logger.log('ERROR: Drive API not enabled!');
      Logger.log('To enable: Apps Script Editor > Services > Add "Drive API" (v2)');
      Logger.log('See README.md for detailed instructions');
      return '';
    }

    // First, create the PDF file in Drive temporarily
    const tempPdfFile = DriveApp.createFile(pdfBlob.setName(`temp_pdf_${fileName}`));
    const pdfId = tempPdfFile.getId();

    try {
      // Use Drive API to convert PDF to Google Doc with OCR
      const resource = {
        title: `temp_doc_${fileName}`,
        mimeType: 'application/vnd.google-apps.document'
      };

      const docFile = Drive.Files.copy(resource, pdfId, {
        ocr: true,
        ocrLanguage: 'en,cs'
      });

      // Get the text content
      const doc = DocumentApp.openById(docFile.id);
      const text = doc.getBody().getText();

      // Clean up both temporary files
      DriveApp.getFileById(docFile.id).setTrashed(true);
      tempPdfFile.setTrashed(true);

      return text;
    } catch (e) {
      // Make sure to clean up PDF even if conversion fails
      tempPdfFile.setTrashed(true);
      throw e;
    }
  } catch (e) {
    Logger.log(`Error extracting text from PDF: ${e.toString()}`);
    return '';
  }
}

/**
 * Attempts to extract amount from PDF text
 * @param {string} pdfText - Text extracted from PDF
 * @param {string} vendor - Vendor name (AWS, Google, etc)
 * @returns {number|null} - Extracted amount or null
 */
function extractAmountFromPDFText(pdfText, vendor) {
  if (!pdfText) {
    Logger.log('PDF text is empty or null');
    return null;
  }

  const cleanText = pdfText.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();

  // Debug: Log a snippet of the extracted text
  Logger.log(`PDF text sample (first 500 chars): ${cleanText.substring(0, 500)}`);

  let amountPatterns = [];

  if (vendor === 'AWS') {
    amountPatterns = [
      /TOTAL[:\s]+EUR\s*([\d,.]+)/i,
      /Total Amount[:\s]+EUR\s*([\d,.]+)/i,
      /EUR\s+([\d,]+\.\d{2})/i,
      /€\s*([\d,]+\.\d{2})/
    ];
  } else if (vendor === 'GOOGLE') {
    amountPatterns = [
      /Celková částka v EUR[:\s]*([\d,.\s]+)\s*€/i,  // Czech: Total amount in EUR
      /Celková částka[:\s]*([\d,.\s]+)\s*€/i,  // Czech: Total amount
      /Total amount[:\s]*EUR\s*([\d,.\s]+)/i,  // English
      /Total[:\s]*EUR\s*([\d,.\s]+)/i,
      /EUR\s+([\d]+[.,]\d{2})/i,
      /([\d]+[.,]\d{2})\s*€/,
      /€\s*([\d]+[.,]\d{2})/
    ];
  }

  for (let i = 0; i < amountPatterns.length; i++) {
    const pattern = amountPatterns[i];
    const match = cleanText.match(pattern);
    if (match && match[1]) {
      Logger.log(`Pattern ${i} matched: ${pattern}`);
      let amount = match[1].replace(/\s/g, '');
      // Handle European format (comma as decimal)
      if (amount.includes(',') && !amount.includes('.')) {
        amount = amount.replace(',', '.');
      } else if (amount.includes(',') && amount.includes('.')) {
        // Remove thousands separator
        amount = amount.replace(',', '');
      }
      const parsedAmount = parseFloat(amount);
      if (!isNaN(parsedAmount) && parsedAmount > 0) {
        Logger.log(`Extracted amount from PDF: ${parsedAmount}`);
        return parsedAmount;
      } else {
        Logger.log(`Parsed amount was invalid: ${parsedAmount} from string: ${match[1]}`);
      }
    }
  }

  Logger.log(`No amount pattern matched for ${vendor}. Check PDF text format.`);
  return null;
}

// ===== HELPER FUNCTIONS =====

function extractEmailFromSender(senderString) {
  const emailMatch = senderString.match(/<([^>]+)>/);
  if (emailMatch) {
    return emailMatch[1];
  }
  
  const directEmailMatch = senderString.match(/[\w.-]+@[\w.-]+\.\w+/);
  if (directEmailMatch) {
    return directEmailMatch[0];
  }
  
  return senderString;
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
  report += `Total Amount: €${stats.totalAmount.toFixed(2)}\n`;
  report += `Average Amount: €${stats.averageAmount.toFixed(2)}\n`;
  
  report += `\nBills by Company:\n`;
  Object.entries(stats.byCompany).forEach(([company, data]) => {
    report += `  ${company}: ${data.count} bills, €${data.total.toFixed(2)}\n`;
  });
  
  report += `\nBills by Category:\n`;
  Object.entries(stats.byCategory).forEach(([category, data]) => {
    report += `  ${category}: ${data.count} bills, €${data.total.toFixed(2)}\n`;
  });
  report += `\n${'='.repeat(50)}\n\n`;
  
  // Individual bill details
  processedEmails.forEach((email) => {
    const data = email.parsedData;
    report += `${email.index}. ${email.subject}\n`;
    report += `From: ${email.sender}\n`;
    report += `Email: ${email.senderEmail}\n`;
    report += `Date: ${email.date}\n`;
    report += `Company: ${data.company}\n`;
    report += `Receipt/Invoice: ${data.receiptNumber}\n`;
    report += `Amount: €${data.amount}\n`;
    report += `Type: ${data.description} (${data.category})\n`;
    if (data.invoiceNumber && data.invoiceNumber !== data.receiptNumber) {
      report += `Invoice: ${data.invoiceNumber}\n`;
    }
    if (data.billingPeriod) {
      report += `Period: ${data.billingPeriod}\n`;
    }
    if (data.paymentMethod) {
      report += `Payment/Account: ${data.paymentMethod}\n`;
    }
    if (email.attachmentCount > 0) {
      report += `Attachments: ${email.attachmentCount} file(s)\n`;
      if (email.attachmentData && email.attachmentData.length > 0) {
        email.attachmentData.forEach((att, i) => {
          report += `  ${i + 1}. ${att.name}\n     ${att.url}\n`;
        });
      }
    }
    report += '-'.repeat(30) + '\n\n';
  });
  
  return report;
}

function calculateBillStatistics(processedEmails) {
  let totalAmount = 0;
  let byCategory = {};
  let byCompany = {};
  
  processedEmails.forEach(email => {
    const data = email.parsedData;
    const amount = parseFloat(data.amount) || 0;
    const category = data.category || 'Other';
    const company = data.company || 'Unknown';
    
    totalAmount += amount;
    
    if (!byCategory[category]) {
      byCategory[category] = { count: 0, total: 0 };
    }
    byCategory[category].count++;
    byCategory[category].total += amount;
    
    if (!byCompany[company]) {
      byCompany[company] = { count: 0, total: 0 };
    }
    byCompany[company].count++;
    byCompany[company].total += amount;
  });
  
  return {
    totalAmount: totalAmount,
    averageAmount: processedEmails.length > 0 ? totalAmount / processedEmails.length : 0,
    byCategory: byCategory,
    byCompany: byCompany
  };
}

// ===== INDIVIDUAL LABEL PROCESSORS (for testing/manual runs) =====

function processAnthropicBills() {
  processSpecificLabel('ANTHROPIC');
}

function processAWSBills() {
  processSpecificLabel('AWS');
}

function processGoogleBills() {
  processSpecificLabel('GOOGLE');
}

function processSpecificLabel(vendorKey) {
  try {
    const spreadsheet = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
    const sheet = spreadsheet.getSheetByName(CONFIG.SHEET_NAME);
    const attachmentsFolder = DriveApp.getFolderById(CONFIG.DRIVE_FOLDER_ID_ATTACHMENTS);
    
    const existingData = sheet.getDataRange().getValues();
    const existingEntries = new Set();
    
    for (let i = 1; i < existingData.length; i++) {
      if (existingData[i][1] && existingData[i][9]) {
        const uniqueKey = `${existingData[i][1]}|${existingData[i][9]}`;
        existingEntries.add(uniqueKey);
      }
    }
    
    const labelName = CONFIG.LABELS[vendorKey];
    const result = processLabelEmails(labelName, vendorKey, existingEntries, attachmentsFolder);
    
    if (result && result.newEntries.length > 0) {
      const lastRow = sheet.getLastRow();
      const entriesWithoutLinks = result.newEntries.map(row => row.slice(0, 12));
      sheet.getRange(lastRow + 1, 1, result.newEntries.length, 12).setValues(entriesWithoutLinks);
      Logger.log(`Added ${result.newEntries.length} entries for ${vendorKey}`);
    }
    
  } catch (error) {
    Logger.log(`Error processing ${vendorKey}: ${error.toString()}`);
  }
}

// ===== SETUP AND TESTING =====

function setupSpreadsheetHeaders() {
  const spreadsheet = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const sheet = spreadsheet.getSheetByName(CONFIG.SHEET_NAME);
  
  const headers = [
    'Date', 'Receipt Number', 'Company', 'Amount', 'Description', 
    'Payment Method', 'Invoice Number', 'Billing Period', 'Category', 
    'Subject', 'Sender Email', 'Attachments', 'Attachment Links'
  ];
  
  sheet.getRange(1, 1, 1, 13).setValues([headers]);
  sheet.getRange(1, 1, 1, 13).setFontWeight('bold');
  sheet.autoResizeColumns(1, 13);
  
  Logger.log('Headers added to spreadsheet (columns A-M)');
}

function testAllParsers() {
  Logger.log('=== TESTING ALL PARSERS ===\n');

  // Test Anthropic
  Logger.log('--- ANTHROPIC PARSER ---');
  const anthropicTests = [
    {
      name: "Regular Receipt",
      subject: "Your receipt from Anthropic, PBC #2200-5755-9758",
      body: "Receipt number 2200-5755-9758 Invoice number DBBYCVSC-0002 Payment method - 3708 Sep 14 Oct 14, 2025 Max plan - 20x Qty 1 180. 00 Total 180. 00 Amount paid 180. 00",
      date: new Date('2025-09-14')
    },
    {
      name: "Credit Note",
      subject: "Credit note from Anthropic, PBC for invoice 1YDHSHFS-0001",
      body: "Credit Note 1YDHSHFS-0001-CN-01 Invoice 1YDHSHFS-0001 Date of issue October 15, 2025 $1.05 refunded on October 15, 2025 Credit — Other $1.05 Subtotal $1.05 Adjustment total $1.05 Refund issued - Visa - 3708 $1.05 Total credit $1.05",
      date: new Date('2025-10-15')
    }
    // Note: Refund emails are skipped (duplicates of credit notes)
  ];

  anthropicTests.forEach((test, i) => {
    const result = parseAnthropicBill(test.subject, test.body, test.date);
    Logger.log(`Anthropic Test ${i + 1} (${test.name}): ${JSON.stringify(result, null, 2)}`);
  });

  // Test AWS
  Logger.log('\n--- AWS PARSER ---');
  const awsTests = [
    {
      name: "Regular Invoice",
      subject: "Amazon Web Services Invoice Available [Account: 182059100462] [Invoice ID: EUINCZ25-174255]",
      body: "Your AWS invoice is now available. VAT Invoice Date: November 1, 2025 TOTAL AMOUNT EUR 103.53 billing period October 1 - October 31, 2025 VAT - 21%",
      date: new Date('2025-11-01')
    },
    {
      name: "Marketplace Tax Invoice",
      subject: "Amazon Web Services Tax Invoice Available [Account: 565393049593]",
      body: "VAT Invoice Number: IINCZ25-1376 VAT Invoice Date: November 25, 2025 TOTAL AMOUNT EUR 30.62 billing period November 1 - November 30, 2025 AWS Marketplace Charges Account number: 565393049593",
      date: new Date('2025-11-25')
    }
  ];

  awsTests.forEach((test, i) => {
    const result = parseAWSBill(test.subject, test.body, test.date);
    Logger.log(`AWS Test ${i + 1} (${test.name}): ${JSON.stringify(result, null, 2)}`);
  });

  // Test Google
  Logger.log('\n--- GOOGLE PARSER ---');
  const googleTests = [
    {
      name: "Regular Invoice",
      subject: "Google Workspace: Your invoice is available for hub440.cz",
      body: "Číslo faktury: 5396779091 Datum faktury: 31. 10. 2025 Fakturační číslo zákazníka: 2515-3845-4639 Google Workspace Business Standard Celková částka v EUR 10,53 € Souhrn za 1. 10. 2025 - 31. 10. 2025",
      date: new Date('2025-10-31')
    }
  ];

  googleTests.forEach((test, i) => {
    const result = parseGoogleBill(test.subject, test.body, test.date);
    Logger.log(`Google Test ${i + 1} (${test.name}): ${JSON.stringify(result, null, 2)}`);
  });
}

// ===== AUTOMATION FUNCTIONS =====

function createWeeklyTrigger() {
  deleteAllTriggers();
  
  ScriptApp.newTrigger('processAllBillsWithLogging')
    .timeBased()
    .everyWeeks(1)
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(6)
    .create();
  
  Logger.log('Weekly trigger created: Every Monday at 6:00 AM');
}

function createDailyTrigger() {
  deleteAllTriggers();
  
  ScriptApp.newTrigger('processAllBillsWithLogging')
    .timeBased()
    .everyDays(1)
    .atHour(8)
    .create();
  
  Logger.log('Daily trigger created: Every day at 8:00 AM');
}

function deleteAllTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'processAllBillsWithLogging') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  Logger.log('Existing triggers deleted');
}

function listActiveTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  Logger.log(`Active triggers (${triggers.length} total):`);
  
  triggers.forEach((trigger, index) => {
    Logger.log(`${index + 1}. Function: ${trigger.getHandlerFunction()}, Source: ${trigger.getTriggerSource()}`);
  });
}

function processAllBillsWithLogging() {
  try {
    Logger.log(`=== AUTOMATED RUN STARTED: ${new Date()} ===`);
    processAllBills();
    Logger.log(`=== AUTOMATED RUN COMPLETED: ${new Date()} ===`);
    sendCompletionNotification();
  } catch (error) {
    Logger.log(`ERROR in automated run: ${error.toString()}`);
    sendErrorNotification(error);
  }
}

function sendCompletionNotification() {
  const email = Session.getActiveUser().getEmail();
  const subject = 'Bills Processing Complete - All Vendors';
  const body = `Your weekly bill processing has completed successfully at ${new Date()}.

Processed labels: Bills Anthropic, Bills AWS, Bills Google

Check your Google Sheets and Drive folders for updated data.

- Spreadsheet: https://docs.google.com/spreadsheets/d/${CONFIG.SPREADSHEET_ID}
- Summary folder: https://drive.google.com/drive/folders/${CONFIG.DRIVE_FOLDER_ID}
- Attachments folder: https://drive.google.com/drive/folders/${CONFIG.DRIVE_FOLDER_ID_ATTACHMENTS}`;
  
  try {
    GmailApp.sendEmail(email, subject, body);
    Logger.log('Completion notification sent');
  } catch (error) {
    Logger.log(`Failed to send notification: ${error.toString()}`);
  }
}

function sendErrorNotification(error) {
  const email = Session.getActiveUser().getEmail();
  const subject = 'Bills Processing Error';
  const body = `There was an error in your automated bill processing:

Error: ${error.toString()}
Time: ${new Date()}

Please check your Apps Script logs for more details.`;
  
  try {
    GmailApp.sendEmail(email, subject, body);
  } catch (e) {
    Logger.log(`Failed to send error notification: ${e.toString()}`);
  }
}

// ===== SETUP GUIDE =====

function setup() {
  Logger.log('=== MULTI-VENDOR BILLS PROCESSOR SETUP ===\n');

  Logger.log('SUPPORTED VENDORS:');
  Logger.log('• Anthropic (Label: "Bills Anthropic")');
  Logger.log('• Amazon Web Services (Label: "Bills AWS")');
  Logger.log('• Google Workspace (Label: "Bills Google")');
  Logger.log('');

  Logger.log('SETUP STEPS:');
  Logger.log('1. Enable Drive API: Editor menu > Services > Add "Drive API" (v2)');
  Logger.log('2. Create Gmail labels: "Bills Anthropic", "Bills AWS", "Bills Google"');
  Logger.log('3. Apply labels to your bill emails from each vendor');
  Logger.log('4. Run setupSpreadsheetHeaders() to initialize the spreadsheet');
  Logger.log('5. Run testAllParsers() to verify parsing logic');
  Logger.log('6. Run processAllBills() to process all vendors');
  Logger.log('7. Run createWeeklyTrigger() for automation');
  Logger.log('');

  Logger.log('FEATURES:');
  Logger.log('• Automatic PDF parsing to extract amounts from AWS/Google invoices');
  Logger.log('• Duplicate detection prevents reprocessing');
  Logger.log('• Attachments saved with structured filenames and linked in spreadsheet');
  Logger.log('');
  
  Logger.log('MANUAL PROCESSING FUNCTIONS:');
  Logger.log('• processAllBills() - Process all three vendors');
  Logger.log('• processAnthropicBills() - Process only Anthropic');
  Logger.log('• processAWSBills() - Process only AWS');
  Logger.log('• processGoogleBills() - Process only Google');
  Logger.log('');
  
  Logger.log('SPREADSHEET COLUMNS (A-M):');
  Logger.log('A: Date, B: Receipt#, C: Company, D: Amount, E: Description');
  Logger.log('F: Payment Method, G: Invoice#, H: Billing Period, I: Category');
  Logger.log('J: Subject, K: Sender Email, L: Attachments, M: Links');
  Logger.log('');
  Logger.log('The Company column (C) distinguishes vendors: Anthropic, AWS, Google');
  Logger.log('');
  Logger.log('NOTE: Script automatically extracts amounts from PDFs when missing from email body');
}