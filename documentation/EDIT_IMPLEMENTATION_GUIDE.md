# Edit Implementation Guide

This guide explains how to implement edit and save functionality for a markdown/text viewer, based on the textviewer.html implementation.

## Your Setup

- **Display element**: `<div id="analysisReportText">` - shows the rendered markdown
- **Save button**: `<button id="saveReportBtn">` - saves the file (always, not just when edited)

## Required HTML Elements

Add these elements to your HTML:

```html
<!-- Edit Button (add near your save button) -->
<button id="editReportBtn" style="background: #9c27b0; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold;">✏️ Edit</button>

<!-- Cancel Button (hidden by default) -->
<button id="cancelEditBtn" style="display: none; background: #f44336; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold;">✖ Cancel</button>

<!-- Edit Textarea (hidden by default, same location as your display div) -->
<textarea id="reportEditTextarea" style="display: none; width: 100%; height: 400px; padding: 20px; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.6; border: 2px solid #9c27b0; border-radius: 8px; resize: vertical;"></textarea>

<!-- Your existing elements -->
<div id="analysisReportText"><!-- Rendered markdown appears here --></div>
<button id="saveReportBtn" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold;">💾 Save Report</button>
```

## Required JavaScript

Add this JavaScript code:

```javascript
// ============================================
// EDIT FUNCTIONALITY
// ============================================

// State variables
let isEditMode = false;
let currentReportContent = ''; // Store the current markdown content (raw)

// DOM Elements
const analysisReportText = document.getElementById('analysisReportText');
const reportEditTextarea = document.getElementById('reportEditTextarea');
const editReportBtn = document.getElementById('editReportBtn');
const cancelEditBtn = document.getElementById('cancelEditBtn');
const saveReportBtn = document.getElementById('saveReportBtn');

// Enter edit mode
function enterEditMode() {
    isEditMode = true;

    // Show textarea, hide rendered view
    analysisReportText.style.display = 'none';
    reportEditTextarea.style.display = 'block';

    // Load current content into textarea
    reportEditTextarea.value = currentReportContent;

    // Update buttons
    editReportBtn.textContent = '✏️ Editing...';
    editReportBtn.style.background = '#7b1fa2';
    cancelEditBtn.style.display = 'inline-block';

    // Focus textarea
    reportEditTextarea.focus();
}

// Cancel edit mode (discard changes)
function cancelEditMode() {
    isEditMode = false;

    // Hide textarea, show rendered view
    reportEditTextarea.style.display = 'none';
    analysisReportText.style.display = 'block';

    // Reset buttons
    editReportBtn.textContent = '✏️ Edit';
    editReportBtn.style.background = '#9c27b0';
    cancelEditBtn.style.display = 'none';
}

// Save and exit edit mode (apply changes)
function saveAndExitEditMode() {
    if (isEditMode) {
        // Get edited content
        currentReportContent = reportEditTextarea.value;

        // Re-render the markdown
        analysisReportText.innerHTML = marked.parse(currentReportContent);

        // Apply syntax highlighting if using highlight.js
        analysisReportText.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }

    // Exit edit mode
    cancelEditMode();
}

// Save report to file (works whether edited or not)
function saveReport() {
    // If in edit mode, apply changes first
    if (isEditMode) {
        currentReportContent = reportEditTextarea.value;
    }

    // Create filename (customize as needed)
    const filename = 'report.md';

    // Create blob and download
    const blob = new Blob([currentReportContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // Visual feedback
    saveReportBtn.textContent = '✓ Saved!';
    saveReportBtn.style.background = '#1b5e20';
    setTimeout(() => {
        saveReportBtn.textContent = '💾 Save Report';
        saveReportBtn.style.background = '#28a745';
    }, 1500);

    // Exit edit mode if active
    if (isEditMode) {
        cancelEditMode();
    }
}

// Event Listeners
editReportBtn.addEventListener('click', function() {
    if (isEditMode) {
        // If already editing, save and exit
        saveAndExitEditMode();
    } else {
        // Enter edit mode
        enterEditMode();
    }
});

cancelEditBtn.addEventListener('click', cancelEditMode);
saveReportBtn.addEventListener('click', saveReport);

// ============================================
// IMPORTANT: Set currentReportContent when loading
// ============================================

// When you load/generate a report, store the raw markdown:
function loadReport(markdownContent) {
    // Store raw content for editing
    currentReportContent = markdownContent;

    // Render to display
    analysisReportText.innerHTML = marked.parse(markdownContent);

    // Apply syntax highlighting
    analysisReportText.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
}

// Example usage:
// loadReport('# My Report\n\nThis is the content...');
```

## Key Differences from textviewer.html

| Feature | textviewer.html | Your Implementation |
|---------|-----------------|---------------------|
| Save behavior | Only saves edited files | Always saves current content |
| Edit tracking | Tracks multiple edited files | Single report |
| Save output | Zip for multiple, single file download | Always single file |
| Content source | Loaded from blob URLs | Your `currentReportContent` variable |

## How It Works

1. **Loading**: When you load a report, call `loadReport(markdownContent)` with the raw markdown string. This stores it in `currentReportContent` and renders it.

2. **Editing**: Click Edit button → textarea appears with raw markdown → user edits → click Edit again (or Save) to apply changes.

3. **Saving**: Click Save → downloads the current content (whether edited or not) as a .md file.

4. **Canceling**: Click Cancel → discards changes and returns to rendered view.

## Required Libraries

Make sure you have these in your `<head>`:

```html
<!-- Markdown parsing -->
<script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>

<!-- Syntax highlighting (optional) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/default.min.css">
<script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js"></script>
```

## Quick Integration Checklist

- [ ] Add Edit button HTML
- [ ] Add Cancel button HTML
- [ ] Add textarea HTML
- [ ] Add JavaScript variables and functions
- [ ] Add event listeners
- [ ] Update your report loading code to call `loadReport()`
- [ ] Include marked.js library
- [ ] (Optional) Include highlight.js for code highlighting
