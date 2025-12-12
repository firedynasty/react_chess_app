// ==================== BLOCK NAVIGATION SYSTEM ====================
// Stores parsed blocks from [1], [2], etc. delimiters
window.flashcardBlocks = [];
window.currentBlockIndex = 0;

// Scan Textarea 2 for numbered blocks [1], [2], etc.
window.scanForBlocks = function() {
    const content = document.getElementById('blockSourceInput').value;
    window.flashcardBlocks = [];

    if (!content.trim()) {
        alert('Textarea 2 is empty. Paste text with [1], [2] block markers first.');
        return 0;
    }

    // Parse line by line to capture [n] and notes on same line
    const lines = content.split('\n');
    let blocks = [];
    let currentBlock = null;
    let currentContent = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        // Match [number] followed by optional notes (with or without dash)
        // e.g. "[1] - eternal life" or "[1] eternal life" or "[1]"
        const blockMatch = line.match(/^\[(\d+)\]\s*-?\s*(.*)/);

        if (blockMatch) {
            // Save previous block if exists
            if (currentBlock !== null) {
                blocks.push({
                    id: currentBlock.id,
                    notes: currentBlock.notes,
                    content: currentContent.join('\n').trim()
                });
            }

            // Start new block - capture notes after [n], strip leading dash if present
            currentBlock = {
                id: blockMatch[1],
                notes: blockMatch[2] ? blockMatch[2].trim() : ''
            };
            currentContent = [];
        } else if (currentBlock !== null) {
            // Add line to current block content
            currentContent.push(line);
        }
    }

    // Don't forget the last block
    if (currentBlock !== null) {
        blocks.push({
            id: currentBlock.id,
            notes: currentBlock.notes,
            content: currentContent.join('\n').trim()
        });
    }

    window.flashcardBlocks = blocks;
    window.currentBlockIndex = 0;

    console.log('DEBUG: scanForBlocks found', blocks.length, 'blocks');
    blocks.forEach(b => console.log('DEBUG: Block', b.id, 'notes:', b.notes));

    if (blocks.length === 0) {
        alert('No blocks found. Make sure text has [1], [2], etc. markers.');
        $('#blockCounter').text('0/0');
        $('#blockTitle').text('');
        return 0;
    }

    // Load the first block and auto-generate flashcards
    window.loadBlockByIndex(0, true);
    return blocks.length;
};

// Load specific block by index into Textarea 1
window.loadBlockByIndex = function(index, autoGenerate = false) {
    if (window.flashcardBlocks.length === 0) {
        console.log('DEBUG: No blocks to load');
        return;
    }

    if (index < 0 || index >= window.flashcardBlocks.length) {
        console.log('DEBUG: Invalid block index:', index);
        return;
    }

    window.currentBlockIndex = index;
    const block = window.flashcardBlocks[index];

    console.log('DEBUG: Loading block', block.id, 'at index', index, 'notes:', block.notes);

    // Put content into Textarea 1
    document.getElementById('pasteInput').value = block.content;

    // Update the currentSetName span - show notes if available, otherwise "Block N"
    const displayName = block.notes ? block.notes : 'Block ' + block.id;
    $('#currentSetName').text(displayName);
    $('#blockTitle').text('- ' + displayName);

    // Update block counter
    $('#blockCounter').text((index + 1) + '/' + window.flashcardBlocks.length);

    console.log('DEBUG: Loaded block', block.id, 'into Textarea 1');

    // Auto-generate flashcards after 500ms if requested
    if (autoGenerate) {
        setTimeout(function() {
            window.generateFromPaste();
        }, 500);
    }
};

// Next block with wrap-around
window.nextBlock = function() {
    if (window.flashcardBlocks.length === 0) {
        const count = window.scanForBlocks();
        if (count === 0) return;
    } else {
        window.currentBlockIndex = (window.currentBlockIndex + 1) % window.flashcardBlocks.length;
        window.loadBlockByIndex(window.currentBlockIndex, true); // auto-generate after 500ms
    }
};

// Previous block with wrap-around
window.prevBlock = function() {
    if (window.flashcardBlocks.length === 0) {
        const count = window.scanForBlocks();
        if (count === 0) return;
    } else {
        window.currentBlockIndex = (window.currentBlockIndex - 1 + window.flashcardBlocks.length) % window.flashcardBlocks.length;
        window.loadBlockByIndex(window.currentBlockIndex, true); // auto-generate after 500ms
    }
};

// Paste from clipboard into Textarea 2 and scan blocks
window.pasteAndScanBlocks = function() {
    navigator.clipboard.readText()
        .then(text => {
            if (!text.trim()) {
                alert('Clipboard is empty. Please copy some block text first.');
                return;
            }

            // Paste content into Textarea 2
            document.getElementById('blockSourceInput').value = text;
            console.log('DEBUG: Pasted from clipboard into Textarea 2, length:', text.length);

            // Immediately scan for blocks
            window.scanForBlocks();
        })
        .catch(err => {
            console.error('Failed to read clipboard contents:', err);
            alert('Unable to access clipboard. Please check browser permissions or paste manually.');
        });
};

// ==================== END BLOCK NAVIGATION ====================

// Forward declarations for onclick handlers
window.generateFromPaste = function() {
    const pasteInput = document.getElementById('pasteInput');
    const content = pasteInput.value.trim();

    if (!content) {
        alert('Please paste some flashcard content first');
        return;
    }

    console.log('DEBUG: generateFromPaste called, content length:', content.length);

    // Process semicolon-delimited content
    const lines = content.split('\n').filter(line => line.trim());
    const flashcards = [];

    lines.forEach((line, index) => {
        const trimmedLine = line.trim();
        // Find the first semicolon
        const semicolonIndex = trimmedLine.indexOf(';');

        if (semicolonIndex > 0) {
            const front = trimmedLine.substring(0, semicolonIndex).trim();
            const back = trimmedLine.substring(semicolonIndex + 1).trim();

            if (front && back) {
                // Apply reversal if enabled
                if (typeof isReversed !== 'undefined' && isReversed) {
                    flashcards.push({ front: back, back: front });
                } else {
                    flashcards.push({ front, back });
                }
                console.log('DEBUG: Added flashcard - Front:', front, 'Back:', back.substring(0, 50) + '...');
            }
        } else {
            console.log('DEBUG: Skipping line (no semicolon):', trimmedLine.substring(0, 50));
        }
    });

    console.log('DEBUG: Total flashcards from paste:', flashcards.length);

    if (flashcards.length === 0) {
        alert('No valid flashcards found. Make sure each line has format: Term; Definition');
        return;
    }

    // Store flashcards globally for export
    currentFlashcards = flashcards;

    // Generate the flashcard HTML
    generateFlashcardHTML(flashcards);

    console.log('DEBUG: Generated', flashcards.length, 'flashcards from pasted content');
};

window.clearPasteInput = function() {
    document.getElementById('pasteInput').value = '';
    console.log('DEBUG: Paste input cleared');
};

window.copyTextareaToClipboard = function() {
    const textarea = document.getElementById('pasteInput');
    const content = textarea.value.trim();

    if (!content) {
        alert('Textarea is empty. Nothing to copy.');
        return;
    }

    navigator.clipboard.writeText(content)
        .then(() => {
            console.log('DEBUG: Textarea content copied to clipboard');
            alert('Copied to clipboard!');
        })
        .catch(err => {
            console.error('Failed to copy to clipboard:', err);
            alert('Failed to copy. Please select and copy manually.');
        });
};

window.exportToTextarea = function() {
    // Get all flashcards that are NOT marked as known (green) - read directly from DOM
    const flashcardsToExport = [];
    const allFlashcardElements = $('.flashcard');
    let knownCount = 0;

    console.log('DEBUG: exportToTextarea - checking', allFlashcardElements.length, 'flashcard elements');

    allFlashcardElements.each(function(index) {
        const element = $(this);
        const isKnown = element.hasClass('known');

        // Read front and back text directly from DOM
        const front = element.find('.front h3').text().trim();
        const back = element.find('.back p').text().trim();

        if (isKnown) {
            knownCount++;
            console.log('DEBUG: Skipping known card:', front);
        } else if (front && back) {
            flashcardsToExport.push({ front, back });
            console.log('DEBUG: Including card:', front);
        }
    });

    if (flashcardsToExport.length === 0) {
        alert('No unknown flashcards to export - you know them all!');
        return;
    }

    // Convert to semicolon-delimited format
    const textContent = flashcardsToExport.map(card => `${card.front}; ${card.back}`).join('\n');

    // Clear textarea and insert exported content
    document.getElementById('pasteInput').value = textContent;

    console.log('DEBUG: Exported', flashcardsToExport.length, 'unknown cards to textarea,', knownCount, 'known cards skipped');
};

window.pasteAndGenerate = function() {
    navigator.clipboard.readText()
        .then(text => {
            if (!text.trim()) {
                alert('Clipboard is empty. Please copy some flashcard data first.');
                return;
            }

            // Paste content into textarea
            document.getElementById('pasteInput').value = text;
            console.log('DEBUG: Pasted from clipboard, length:', text.length);

            // Immediately generate flashcards
            window.generateFromPaste();
        })
        .catch(err => {
            console.error('Failed to read clipboard contents:', err);
            alert('Unable to access clipboard. Please check browser permissions or paste manually.');
        });
};

// Initialize flashcard database with file contents
window.tempFlashcardDatabase = {
  'default_computer_specs': {
    content: 'retina display, Retina display is a term used by Apple to describe displays that have a higher pixel density than traditional displays\nGHz, Short for gigahertz, GHz describes the speed the computer\'s brain works.\nProcessor, This describes the computer\'s brain. For example: i3, i4, i5, i6, i7 and i8. Think of it this way, if a computer is "i7", it has 7 brains.\nTurbo Boost, When the processor is under heavy load, Turbo Boost will automatically speed up the computer.\nMemory, This is the level to which the computer can manage several big apps at once. For example, 2GB is weak and should only be used for very basic things like email and word editing. 32GB is strong and could work for video editing and gaming.\nSSD storage, This refers to how many files can be held on the computer at once. 256GB is good. 512GB is great!',
    filename: 'default_computer_specs.txt'
  }
};

var TEMPLATE_FLASHCARDS = [
    { front: "retina display", back: "Retina display is a term used by Apple to describe displays that have a higher pixel density than traditional displays" },
    { front: "GHz", back: "Short for gigahertz, GHz describes the speed the computer\'s brain works." },
    { front: "Processor", back: "This describes the computer\'s brain. For example: i3, i4, i5, i6, i7 and i8. Think of it this way, if a computer is \"i7\", it has 7 brains." },
    { front: "Turbo Boost", back: "When the processor is under heavy load, Turbo Boost will automatically speed up the computer." },
    { front: "Memory", back: "This is the level to which the computer can manage several big apps at once. For example, 2GB is weak and should only be used for very basic things like email and word editing. 32GB is strong and could work for video editing and gaming." },
    { front: "SSD storage", back: "This refers to how many files can be held on the computer at once. 256GB is good. 512GB is great!" }
];

// Auto-populate navbar dropdown when page loads
$(document).ready(function() {
    // Wait for everything to be initialized
    setTimeout(() => {
        if (window.tempFlashcardDatabase) {
            updateNavbarDropdown();
            console.log('Navbar dropdown auto-populated with flashcard files');
        }
    }, 100);
});

// Function to load template data on page load
$(document).ready(function() {
    if (TEMPLATE_FLASHCARDS && TEMPLATE_FLASHCARDS.length > 0) {
        console.log('DEBUG: Loading', TEMPLATE_FLASHCARDS.length, 'template flashcards');
        generateFlashcardHTML(TEMPLATE_FLASHCARDS);
    }
});

// ==================== ORIGINAL SCRIPT.JS CONTENT BELOW ====================

// Initialize static flashcards
console.log('DEBUG: Initializing flashcards...');
initializeFlashcards();

// Drag and Drop functionality
$(document).ready(function() {
    console.log('DEBUG: DOM ready, setting up drag and drop...');
    const dragDropZone = $('#dragDropZone');
    const fileInput = $('#fileInput');

    console.log('DEBUG: Drag drop zone found:', dragDropZone.length);
    console.log('DEBUG: File input found:', fileInput.length);

    // Drag and drop events
    dragDropZone.on('dragover', function(e) {
        e.preventDefault();
        console.log('DEBUG: Drag over detected');
        $(this).addClass('drag-over');
    });

    dragDropZone.on('dragleave', function(e) {
        e.preventDefault();
        console.log('DEBUG: Drag leave detected');
        $(this).removeClass('drag-over');
    });

    dragDropZone.on('drop', function(e) {
        e.preventDefault();
        console.log('DEBUG: Drop detected');
        $(this).removeClass('drag-over');
        const files = e.originalEvent.dataTransfer.files;
        console.log('DEBUG: Files dropped:', files.length);
        handleFiles(files);
    });

    // File input change
    fileInput.on('change', function() {
        console.log('DEBUG: File input change detected, files:', this.files.length);
        handleFiles(this.files);
    });

    // Note: Removed automatic loading of default content
    console.log('DEBUG: Ready for file upload or drag and drop');
});

function initializeFlashcards() {
    $('.back').hide();

    // Use event delegation for dynamic flashcards
    $(document).on('mouseenter', '.front', function() {
        // Hide any currently flipped cards first
        $('.back:visible').hide();
        $('.front:hidden').addClass("animated flipInY fast").show();

        // Show this card's back
        $(this).hide();
        $(this).siblings('.back').addClass("animated flipInY fast").show();
    });

    $(document).on('mouseleave', '.back', function() {
        $(this).hide();
        $(this).siblings('.front').addClass("animated flipInY fast").show();
    });

    // Double-click on back of card to mark as known (green)
    $(document).on('dblclick', '.flashcard .back', function(e) {
        e.preventDefault();
        e.stopPropagation();

        const flashcard = $(this).closest('.flashcard');
        console.log('DEBUG: Flashcard double-clicked, toggling known status');

        if (flashcard.hasClass('known')) {
            // Remove known status
            flashcard.removeClass('known');
            console.log('DEBUG: Card marked as unknown');
        } else {
            // Mark as known
            flashcard.addClass('known');
            console.log('DEBUG: Card marked as known');
        }
    });
}

function handleFiles(files) {
    console.log('DEBUG: handleFiles called with', files.length, 'files');

    const txtFiles = Array.from(files).filter(file =>
        file.type.includes('text') || file.name.endsWith('.txt') || file.name.endsWith('.csv') || file.name.endsWith('.tsv')
    );

    console.log('DEBUG: Filtered to', txtFiles.length, 'valid files');

    if (txtFiles.length === 0) {
        alert('Please select text files only (.txt, .csv, or .tsv)');
        return;
    }

    // Process ALL files, not just the first one
    let filesProcessed = 0;
    let lastProcessedFile = null;

    txtFiles.forEach((file, index) => {
        console.log(`DEBUG: Processing file ${index + 1}/${txtFiles.length}: ${file.name}`);

        // Use a promise-based approach to handle files sequentially
        handleSingleFileWithDelimitersAsync(file).then(() => {
            filesProcessed++;
            lastProcessedFile = file;

            console.log(`DEBUG: Completed processing file ${filesProcessed}/${txtFiles.length}: ${file.name}`);

            // When all files are done, update the dropdown and load the last file
            if (filesProcessed === txtFiles.length) {
                updateNavbarDropdown();

                // Load the last processed file's content
                if (lastProcessedFile && window.tempFlashcardDatabase) {
                    const fileName = lastProcessedFile.name.replace(/\.[^/.]+$/, '');
                    if (window.tempFlashcardDatabase[fileName]) {
                        processFlashcardContent(window.tempFlashcardDatabase[fileName].content);
                        $('#currentSetName').text(fileName);
                    }
                }

                console.log(`DEBUG: All ${txtFiles.length} files processed successfully`);
            }
        });
    });
}

// Removed loadDefaultContent function - no automatic fetching

function processFlashcardContent(content) {
    console.log('DEBUG: processFlashcardContent called');
    console.log('DEBUG: Content preview:', content.substring(0, 200) + '...');

    const lines = content.split('\n').filter(line => line.trim());
    console.log('DEBUG: Found', lines.length, 'non-empty lines');

    const flashcards = [];

    lines.forEach((line, index) => {
        console.log('DEBUG: Processing line', index + 1, ':', line);
        const parts = line.split(',');
        if (parts.length >= 2) {
            const front = parts[0].trim();
            const back = parts.slice(1).join(',').trim();

            // Apply reversal if enabled
            if (isReversed) {
                flashcards.push({ front: back, back: front });
            } else {
                flashcards.push({ front, back });
            }

            console.log('DEBUG: Added flashcard - Front:', front, 'Back:', back.substring(0, 50) + '...');
        } else {
            console.log('DEBUG: Skipping invalid line (not enough parts):', line);
        }
    });

    console.log('DEBUG: Total flashcards processed:', flashcards.length);

    if (flashcards.length > 0) {
        // Store flashcards globally for export
        currentFlashcards = flashcards;
        generateFlashcardHTML(flashcards);
    } else {
        console.log('DEBUG: No valid flashcards found');
    }
}

function generateFlashcardHTML(flashcards) {
    console.log('DEBUG: generateFlashcardHTML called with', flashcards.length, 'flashcards');

    // Clear existing dynamic content first
    const dynamicContainer = $('#dynamicFlashcards');
    console.log('DEBUG: Dynamic container found:', dynamicContainer.length);
    console.log('DEBUG: Clearing existing content...');
    dynamicContainer.empty();

    let html = '<div class="container">';

    for (let i = 0; i < flashcards.length; i += 3) {
        html += '<div class="row">';
        console.log('DEBUG: Creating row', Math.floor(i/3) + 1, 'starting with card', i + 1);

        for (let j = 0; j < 3 && (i + j) < flashcards.length; j++) {
            const card = flashcards[i + j];
            console.log('DEBUG: Adding card', i + j + 1, '- Front:', card.front);
            html += `
                <div class="col-sm">
                    <div class="flashcard">
                        <div class="p-3 front border">
                            <h3>${card.front}</h3>
                        </div>
                        <div class="p-3 back border">
                            <p>${card.back}</p>
                        </div>
                    </div>
                </div>
            `;
        }

        html += '</div><br><br>';
    }

    html += '</div>';

    console.log('DEBUG: Generated HTML length:', html.length);
    console.log('DEBUG: HTML preview:', html.substring(0, 300) + '...');

    dynamicContainer.html(html);
    console.log('DEBUG: HTML inserted into dynamic container');

    // Initialize the new flashcards
    const backElements = $('#dynamicFlashcards .back');
    console.log('DEBUG: Found', backElements.length, 'back elements to hide');
    backElements.hide();
    console.log('DEBUG: Back elements hidden');

    // Verify the content was added
    const allFlashcards = $('#dynamicFlashcards .flashcard');
    console.log('DEBUG: Total flashcards in DOM after generation:', allFlashcards.length);
}

// Global variable to store current flashcards for export
let currentFlashcards = [];
let isReversed = false;

function exportFlashcards() {
    console.log('DEBUG: exportFlashcards called');

    // Get flashcards from both template and dynamic content
    let allFlashcards = [];

    // Add template flashcards if they exist
    if (TEMPLATE_FLASHCARDS && TEMPLATE_FLASHCARDS.length > 0) {
        allFlashcards = [...TEMPLATE_FLASHCARDS];
        console.log('DEBUG: Found', TEMPLATE_FLASHCARDS.length, 'template flashcards');
    }

    // Add current flashcards from imports if they exist
    if (currentFlashcards && currentFlashcards.length > 0) {
        allFlashcards = [...currentFlashcards];
        console.log('DEBUG: Found', currentFlashcards.length, 'imported flashcards');
    }

    if (allFlashcards.length === 0) {
        alert('No flashcards to export');
        return;
    }

    // Filter out known (green) flashcards based on DOM state
    const flashcardsToExport = [];
    const allFlashcardElements = $('.flashcard');

    console.log('DEBUG: Checking', allFlashcardElements.length, 'flashcard elements for known status');

    allFlashcardElements.each(function(index) {
        const element = $(this);
        const isKnown = element.hasClass('known');

        if (!isKnown && index < allFlashcards.length) {
            flashcardsToExport.push(allFlashcards[index]);
            console.log('DEBUG: Including card', index + 1, ':', allFlashcards[index].front);
        } else if (isKnown) {
            console.log('DEBUG: Skipping known card', index + 1, ':', allFlashcards[index].front);
        }
    });

    if (flashcardsToExport.length === 0) {
        alert('No unknown flashcards to export - you know them all! 🎉');
        return;
    }

    // Convert to text format (front, back)
    const textContent = flashcardsToExport.map(card => `${card.front}, ${card.back}`).join('\n');
    console.log('DEBUG: Generated text content for', flashcardsToExport.length, 'unknown cards, length:', textContent.length);

    // Create and download file
    const blob = new Blob([textContent], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'flashcards_unknown.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    const knownCount = allFlashcards.length - flashcardsToExport.length;
    console.log('DEBUG: Export completed -', flashcardsToExport.length, 'unknown cards exported,', knownCount, 'known cards skipped');
}

// Async version for handling multiple files
function handleSingleFileWithDelimitersAsync(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result.trim();
            if (!content) {
                console.warn(`DEBUG: File ${file.name} is empty`);
                resolve();
                return;
            }

            console.log(`DEBUG: Processing ${file.name}, content length:`, content.length);

            // Check if file contains ### delimiters
            if (content.includes('\n###\n###\n')) {
                // Process with delimiter splitting for dropdown - ADD to existing data
                processFlashcardContentWithDelimiters(content);
                console.log(`DEBUG: Processed ${file.name} with ### delimiters`);
            } else {
                // No delimiters found, add as single flashcard set to dropdown
                const fileName = file.name.replace(/\.[^/.]+$/, ''); // Remove extension

                // Add to tempFlashcardDatabase instead of processing immediately
                window.tempFlashcardDatabase[fileName] = {
                    content: content,
                    filename: file.name
                };

                console.log(`DEBUG: Added ${fileName} to dropdown`);
            }
            resolve();
        };
        reader.onerror = () => {
            console.error(`DEBUG: Error reading file: ${file.name}`);
            reject(new Error(`Error reading file: ${file.name}`));
        };
        reader.readAsText(file);
    });
}

// Original function to handle single file with ### delimiters
function handleSingleFileWithDelimiters(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const content = e.target.result.trim();
        if (!content) {
            alert('File is empty');
            return;
        }

        console.log('DEBUG: File content length:', content.length);
        console.log('DEBUG: Processing content with \\n###\\n###\\n delimiters and @ renaming');

        // Check if file contains ### delimiters
        if (content.includes('\n###\n###\n')) {
            // Process with delimiter splitting for dropdown - ADD to existing data
            processFlashcardContentWithDelimiters(content);
        } else {
            // No delimiters found, add as single flashcard set to dropdown
            const fileName = file.name.replace(/\.[^/.]+$/, ''); // Remove extension

            // Add to tempFlashcardDatabase instead of processing immediately
            window.tempFlashcardDatabase[fileName] = {
                content: content,
                filename: file.name
            };

            // Update dropdown with new data
            updateNavbarDropdown();

            // Load this file's content immediately
            processFlashcardContent(content);

            // Update dropdown button to show current set
            $('#currentSetName').text(fileName);

            console.log('DEBUG: Added single file to dropdown:', fileName);
        }
    };
    reader.onerror = () => {
        console.error(`DEBUG: Error reading file: ${file.name}`);
        alert(`Error reading file: ${file.name}`);
    };
    reader.readAsText(file);
}

// Process flashcard content with ### delimiters and @ renaming support
function processFlashcardContentWithDelimiters(content) {
    // Split content by double ### delimiter (\n###\n###\n)
    const sections = content.split('\n###\n###\n').map(section => section.trim()).filter(section => section.length > 0);

    if (sections.length === 0) {
        alert('No sections found in file');
        return;
    }

    console.log('DEBUG: Found', sections.length, 'sections');

    // DO NOT clear existing database - ADD to it instead
    // Initialize tempFlashcardDatabase if it doesn't exist
    if (!window.tempFlashcardDatabase) {
        window.tempFlashcardDatabase = {};
    }

    // Process each section with @ symbol renaming support
    sections.forEach((section, index) => {
        const lines = section.split('\n');
        let sectionKey = `section_${index + 1}`;
        let customName = null;
        let processedContent = [];

        // Look for @ symbol in any line to use as section name
        for (let line of lines) {
            line = line.trim();
            if (line.startsWith('@')) {
                // Found @ symbol - use this as the section name
                customName = line.substring(1).trim(); // Remove @ and trim
                sectionKey = customName.replace(/[^a-zA-Z0-9_]/g, '_') || `section_${index + 1}`;
                continue; // Skip adding the @name line to processed content
            }

            if (line) { // Skip empty lines
                processedContent.push(line);
            }
        }

        // If no custom name found, try to use first line as key if it's short
        if (!customName && processedContent.length > 0 && processedContent[0].length > 0 && processedContent[0].length < 50) {
            customName = processedContent[0];
            sectionKey = customName.replace(/[^a-zA-Z0-9_]/g, '_') || `section_${index + 1}`;
        }

        // Store in temporary database
        window.tempFlashcardDatabase[sectionKey] = {
            content: processedContent.join('\n'),
            filename: customName || sectionKey
        };

        console.log(`DEBUG: Created section: "${customName || sectionKey}" with ${processedContent.length} lines`);
    });

    // Update navbar dropdown with the processed content
    updateNavbarDropdown();

    console.log(`DEBUG: Created ${sections.length} sections from file with ### delimiters and @ renaming support`);
}

function updateNavbarDropdown() {
    console.log('DEBUG: updateNavbarDropdown called');
    const dropdown = $('#flashcardDropdown');

    // Clear existing dropdown content
    dropdown.empty();

    // Add items for each flashcard set
    if (window.tempFlashcardDatabase) {
        for (let key in window.tempFlashcardDatabase) {
            const item = $('<div></div>')
                .addClass('dropdown-item')
                .text(key)
                .attr('data-key', key)
                .click(() => {
                    selectFlashcardSet(key);
                });

            dropdown.append(item);
        }
    }

    const fileCount = Object.keys(window.tempFlashcardDatabase || {}).length;
    console.log(`DEBUG: Dropdown updated with ${fileCount} flashcard sets`);
}

function selectFlashcardSet(key) {
    console.log('DEBUG: selectFlashcardSet called with key:', key);

    // Update the dropdown button text
    $('#currentSetName').text(key);

    // Remove active class from all dropdown items
    $('.dropdown-item').removeClass('active');

    // Add active class to selected item
    const activeItem = $(`.dropdown-item[data-key="${key}"]`);
    if (activeItem.length) {
        activeItem.addClass('active');
    }

    // Close the dropdown
    $('#flashcardDropdown').removeClass('show');
    $('#flashcardDropdownBtn').removeClass('active');

    // Load the content
    if (window.tempFlashcardDatabase && window.tempFlashcardDatabase[key]) {
        const fileData = window.tempFlashcardDatabase[key];
        processFlashcardContent(fileData.content);

        console.log(`DEBUG: Loaded ${key} flashcards`);
    }
}

// Add dropdown functionality
$(document).ready(function() {
    // Toggle dropdown when button is clicked
    $('#flashcardDropdownBtn').click(function(e) {
        e.preventDefault();
        e.stopPropagation();

        const dropdown = $('#flashcardDropdown');
        const button = $(this);

        dropdown.toggleClass('show');
        button.toggleClass('active');

        console.log('DEBUG: Dropdown toggled, show class:', dropdown.hasClass('show'));
    });

    // Close dropdown when clicking outside
    $(document).click(function(e) {
        if (!$(e.target).closest('.dropdown').length) {
            $('#flashcardDropdown').removeClass('show');
            $('#flashcardDropdownBtn').removeClass('active');
        }
    });

    // Prevent dropdown from closing when clicking inside dropdown content
    $('#flashcardDropdown').click(function(e) {
        e.stopPropagation();
    });

    // Load from clipboard functionality
    $('#loadFromClipboard').click(function() {
        navigator.clipboard.readText()
            .then(text => {
                if (!text.trim()) {
                    alert('Clipboard is empty. Please copy some flashcard data first.');
                    return;
                }

                console.log('DEBUG: Loading clipboard content, length:', text.length);

                // Process like a file with ### delimiter support
                processClipboardContent(text);
            })
            .catch(err => {
                console.error('Failed to read clipboard contents:', err);
                alert('Unable to access clipboard. Please check browser permissions.');
            });
    });
});

// Process clipboard content similar to file processing
function processClipboardContent(content) {
    // Check if content contains ### delimiters
    if (content.includes('\n###\n###\n')) {
        // Process with delimiter splitting for dropdown - ADD to existing data
        processFlashcardContentWithDelimiters(content);
        console.log('DEBUG: Processed clipboard content with ### delimiters');
    } else {
        // No delimiters found, add as single flashcard set to dropdown
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[:\-T]/g, '_');
        const clipboardKey = `clipboard_${timestamp}`;

        // Add to tempFlashcardDatabase
        window.tempFlashcardDatabase[clipboardKey] = {
            content: content,
            filename: 'clipboard.txt'
        };

        // Update dropdown with new data
        updateNavbarDropdown();

        // Load this content immediately
        processFlashcardContent(content);

        // Update dropdown button to show current set
        $('#currentSetName').text(clipboardKey);

        console.log('DEBUG: Added clipboard content to dropdown:', clipboardKey);
    }
}

function reverseFlashcards() {
    console.log('DEBUG: reverseFlashcards called');

    // Toggle the reversed state
    isReversed = !isReversed;

    console.log('DEBUG: isReversed now:', isReversed);

    // Reload the current flashcard set
    const currentSetName = $('#currentSetName').text();

    if (window.tempFlashcardDatabase && window.tempFlashcardDatabase[currentSetName]) {
        const fileData = window.tempFlashcardDatabase[currentSetName];
        processFlashcardContent(fileData.content);
        console.log('DEBUG: Reloaded flashcards with reversed state');
    } else {
        console.log('DEBUG: No current flashcard set to reload');
        alert('Please load a flashcard set first');
    }
}

// ==================== DARK MODE ====================
let darkModeEnabled = false;

window.toggleDarkMode = function() {
    darkModeEnabled = !darkModeEnabled;
    const body = document.body;
    const darkModeButton = document.getElementById('darkModeButton');

    if (darkModeEnabled) {
        body.classList.add('dark-mode');
        darkModeButton.textContent = '☀️ Light';
        darkModeButton.title = 'Switch to light mode';
    } else {
        body.classList.remove('dark-mode');
        darkModeButton.textContent = '🌙 Dark';
        darkModeButton.title = 'Switch to dark mode';
    }

    saveDarkMode();
};

function saveDarkMode() {
    localStorage.setItem('flashcardsDarkMode', darkModeEnabled.toString());
}

function loadDarkMode() {
    const savedDarkMode = localStorage.getItem('flashcardsDarkMode');
    if (savedDarkMode === 'true') {
        darkModeEnabled = true;
        document.body.classList.add('dark-mode');
        const darkModeButton = document.getElementById('darkModeButton');
        if (darkModeButton) {
            darkModeButton.textContent = '☀️ Light';
            darkModeButton.title = 'Switch to light mode';
        }
    }
}

// Load dark mode preference on page load
$(document).ready(function() {
    loadDarkMode();
});

// ==================== END DARK MODE ====================

// Expose functions to window for CodePen compatibility
window.reverseFlashcards = reverseFlashcards;
window.exportFlashcards = exportFlashcards;