// ============================================================
// Chess Study Tool - Script.js
// ============================================================

// Global variables for analysis report
window.analysisReportRawText = '';
window.analysisReportPositions = [];
window.analysisReportPositionIndex = 0;

// ============================================================
// 1. LOAD ANALYSIS REPORT (from clipboard)
// ============================================================

/**
 * Main function to parse and load analysis report content
 * @param {string} clipboardText - The report text content
 * @param {string} sourceName - Source identifier (e.g., 'clipboard', 'file')
 */
function loadAnalysisReportFromContent(clipboardText, sourceName = 'clipboard') {
  if (!clipboardText || clipboardText.trim() === '') {
    showStatus('No content to load', false);
    return;
  }

  // Store raw text
  window.analysisReportRawText = clipboardText;

  // Array to store parsed mistakes
  const mistakes = [];

  // Pattern 1: Standard format with eval line
  // Move 10...: d6
  //   BLUNDER: allows fork
  //   Eval: -108 -> -449 (swing: -341)
  //   FEN: r2qk1nr/...
  const pattern1 = /Move\s+(\d+)(\.{1,3}):\s*(\S+)\s*\n\s*(BLUNDER|MISTAKE|INACCURACY):\s*([^\n]+)\s*\n\s*Eval:\s*([^\n]+)\s*\n\s*FEN:\s*([^\n]+)/gi;

  // Pattern 2: Without eval line
  // Move 5.: Bb5
  //   MISTAKE: hangs piece
  //   FEN: r1bqkbnr/...
  const pattern2 = /Move\s+(\d+)(\.{1,3}):\s*(\S+)\s*\n\s*(BLUNDER|MISTAKE|INACCURACY):\s*([^\n]+)\s*\n\s*FEN:\s*([^\n]+)/gi;

  // Pattern 3: Double bracket format with description
  // [[Opening Trap - Sicilian]]
  // A common trap...
  // FEN: rnbqkb1r/...
  const pattern3 = /\[\[([^\]]+)\]\]\s*\n([^\n]+)\s*\nFEN:\s*([^\n]+)/gi;

  // Pattern 4: Simple double bracket (title + FEN only)
  // [[Critical Position]]
  // FEN: r2qk2r/...
  const pattern4 = /\[\[([^\]]+)\]\]\s*\nFEN:\s*([^\n]+)/gi;

  let match;

  // Apply Pattern 1
  while ((match = pattern1.exec(clipboardText)) !== null) {
    const [fullMatch, moveNum, dots, moveNotation, severity, explanation, evalStr, fen] = match;
    mistakes.push({
      moveNum: moveNum + dots,
      moveNotation: moveNotation.trim(),
      severity: severity.toUpperCase(),
      explanation: explanation.trim(),
      eval: evalStr.trim(),
      fen: fen.trim(),
      displayName: `Move ${moveNum}${dots}: ${moveNotation.trim()}`
    });
  }

  // Apply Pattern 2 (only if not already matched by pattern 1)
  pattern2.lastIndex = 0;
  while ((match = pattern2.exec(clipboardText)) !== null) {
    const [fullMatch, moveNum, dots, moveNotation, severity, explanation, fen] = match;
    const displayName = `Move ${moveNum}${dots}: ${moveNotation.trim()}`;

    // Check if already added
    if (!mistakes.find(m => m.displayName === displayName)) {
      mistakes.push({
        moveNum: moveNum + dots,
        moveNotation: moveNotation.trim(),
        severity: severity.toUpperCase(),
        explanation: explanation.trim(),
        eval: '',
        fen: fen.trim(),
        displayName: displayName
      });
    }
  }

  // Apply Pattern 3
  while ((match = pattern3.exec(clipboardText)) !== null) {
    const [fullMatch, title, description, fen] = match;
    mistakes.push({
      moveNum: '',
      moveNotation: title.trim(),
      severity: 'POSITION',
      explanation: description.trim(),
      eval: '',
      fen: fen.trim(),
      displayName: title.trim()
    });
  }

  // Apply Pattern 4 (only if not matched by pattern 3)
  pattern4.lastIndex = 0;
  while ((match = pattern4.exec(clipboardText)) !== null) {
    const [fullMatch, title, fen] = match;
    const displayName = title.trim();

    if (!mistakes.find(m => m.displayName === displayName)) {
      mistakes.push({
        moveNum: '',
        moveNotation: title.trim(),
        severity: 'POSITION',
        explanation: '',
        eval: '',
        fen: fen.trim(),
        displayName: displayName
      });
    }
  }

  // Show the report container and display content
  const reportContainer = document.getElementById('analysisReportContainer');
  const reportText = document.getElementById('analysisReportText');

  if (reportContainer && reportText) {
    reportContainer.style.display = 'block';
    reportText.textContent = clipboardText;
  }

  // Extract PGN from report and load to board2
  let pgnMatch = clipboardText.match(/GAME PGN[\s\S]*?-{5,}\s*(1\.[^\n]+)/);
  if (pgnMatch && pgnMatch[1]) {
    let pgnText = pgnMatch[1].trim();
    // Clean up PGN
    pgnText = pgnText.replace(/\s+/g, ' ').trim();

    if (typeof window.parsePgnToPositions === 'function') {
      window.analysisReportPositions = window.parsePgnToPositions(pgnText);
      window.analysisReportPositionIndex = 0;

      if (window.analysisReportPositions && window.analysisReportPositions.length > 0) {
        if (window.board2) {
          window.board2.position(window.analysisReportPositions[0]);
          updateBoard2MoveIndicator(0);
        }

        const navContainer = document.getElementById('board2NavContainer');
        if (navContainer) {
          navContainer.style.display = 'block';
        }
      }
    }
  }

  showStatus(`Loaded report from ${sourceName} with ${mistakes.length} positions`, true);
  console.log('Parsed mistakes:', mistakes);
}

/**
 * Helper function to show status messages
 */
function showStatus(message, isSuccess) {
  console.log(isSuccess ? '' : '', message);
  // You can add a status display element here if needed
}

// ============================================================
// 2. SELECT REPORTS FOLDER
// ============================================================

// Global variable to store loaded report files
window.loadedReportFiles = [];

/**
 * Opens the report files modal to display loaded files
 */
function openReportFilesModal() {
  const modal = document.getElementById('reportFilesModal');
  const filesList = document.getElementById('reportFilesList');

  if (!modal || !filesList) return;

  filesList.innerHTML = '';

  if (!window.loadedReportFiles || window.loadedReportFiles.length === 0) {
    filesList.innerHTML = '<p style="color: #666;">No report files loaded. Use "Select Reports Folder" to load files.</p>';
    modal.style.display = 'block';
    return;
  }

  // Create clickable list items for each file
  window.loadedReportFiles.forEach((file, index) => {
    const fileItem = document.createElement('div');
    fileItem.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #eee; cursor: pointer;';
    fileItem.innerHTML = `
      <span style="flex: 1;">${file.name}</span>
      <button style="background: #007bff; color: white; border: none; padding: 5px 15px; border-radius: 3px; cursor: pointer;">Load</button>
    `;

    // Add hover effect
    fileItem.addEventListener('mouseenter', () => fileItem.style.background = '#f0f0f0');
    fileItem.addEventListener('mouseleave', () => fileItem.style.background = 'transparent');

    // Click handler to load the file
    fileItem.addEventListener('click', async () => {
      try {
        let content;
        if (typeof file.text === 'function') {
          content = await file.text();
        } else if (file.content) {
          content = file.content;
        }

        if (content) {
          loadAnalysisReportFromContent(content, file.name);
          modal.style.display = 'none';
        }
      } catch (err) {
        console.error('Error loading file:', err);
        alert('Failed to load file: ' + file.name);
      }
    });

    filesList.appendChild(fileItem);
  });

  modal.style.display = 'block';
}

// ============================================================
// 3. ANALYSIS REPORT CONTAINER FUNCTIONALITY
// ============================================================

// Reference image state
let refImageLoaded = false;
let refImageIsEnlarged = false;

// ============================================================
// 4. BOARD2 AND NAVIGATION CONTROLS
// ============================================================

// Piece theme path for chess board
const pieceThemePath = 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png';

/**
 * Parse PGN notation to array of FEN positions
 * Uses chess.js library
 */
window.parsePgnToPositions = function(pgnString) {
  const positions = [];

  try {
    const chess = new Chess();
    positions.push(chess.fen()); // Starting position

    // Clean PGN
    let cleanPgn = pgnString
      .replace(/\{[^}]*\}/g, '') // Remove comments
      .replace(/\([^)]*\)/g, '') // Remove variations
      .replace(/\d+\.\.\./g, '') // Remove black move indicators
      .replace(/\s+/g, ' ')
      .trim();

    // Extract moves
    const moveRegex = /([KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?|O-O-O|O-O)(?:\+|#)?/g;
    let match;

    while ((match = moveRegex.exec(cleanPgn)) !== null) {
      const move = match[1];
      try {
        const result = chess.move(move, { sloppy: true });
        if (result) {
          positions.push(chess.fen());
        }
      } catch (e) {
        console.warn('Invalid move:', move);
      }
    }
  } catch (e) {
    console.error('Error parsing PGN:', e);
  }

  return positions;
};

/**
 * Update the board2 move indicator display
 */
function updateBoard2MoveIndicator(index) {
  const indicator = document.getElementById('board2MoveIndicator');
  const positionCount = document.getElementById('board2PositionCount');
  const lichessLink = document.getElementById('lichessBoard2Link');

  if (!indicator || !window.analysisReportPositions) return;

  const total = window.analysisReportPositions.length;
  if (positionCount) {
    positionCount.textContent = `${index + 1}/${total}`;
  }

  if (index === 0) {
    indicator.textContent = 'Start';
  } else {
    // Move numbering: odd index = white, even index = black
    const moveNumber = Math.ceil(index / 2);
    const isWhiteMove = index % 2 === 1;
    indicator.textContent = isWhiteMove ? `${moveNumber}.` : `${moveNumber}...`;
  }

  // Update Lichess link with current position
  if (lichessLink && window.analysisReportPositions[index]) {
    const position = window.analysisReportPositions[index];
    const colorToMove = (index % 2 === 0) ? 'w' : 'b';
    let fen = position.includes(' ') ? position : `${position} ${colorToMove} KQkq - 0 1`;
    lichessLink.href = `https://lichess.org/analysis/${fen.replace(/ /g, '_')}`;
  }
}

/**
 * Navigate to next position on board2
 */
function board2NextMove() {
  if (!window.analysisReportPositions || window.analysisReportPositions.length === 0) return;

  window.analysisReportPositionIndex++;
  if (window.analysisReportPositionIndex >= window.analysisReportPositions.length) {
    window.analysisReportPositionIndex = window.analysisReportPositions.length - 1;
  }

  if (window.board2) {
    window.board2.position(window.analysisReportPositions[window.analysisReportPositionIndex]);
  }
  updateBoard2MoveIndicator(window.analysisReportPositionIndex);
}

/**
 * Navigate to previous position on board2
 */
function board2PrevMove() {
  if (!window.analysisReportPositions || window.analysisReportPositions.length === 0) return;

  window.analysisReportPositionIndex--;
  if (window.analysisReportPositionIndex < 0) {
    window.analysisReportPositionIndex = 0;
  }

  if (window.board2) {
    window.board2.position(window.analysisReportPositions[window.analysisReportPositionIndex]);
  }
  updateBoard2MoveIndicator(window.analysisReportPositionIndex);
}

// ============================================================
// DOM READY EVENT LISTENERS
// ============================================================

document.addEventListener('DOMContentLoaded', function() {

  // ============================================================
  // BOARD2 INITIALIZATION
  // ============================================================

  // Initialize Board2
  window.board2 = Chessboard('myBoard2', {
    draggable: true,
    dropOffBoard: 'snapback',
    position: 'start',
    snapbackSpeed: 500,
    snapSpeed: 100,
    pieceTheme: pieceThemePath
  });

  // --- Board2 Navigation Buttons ---
  const board2NextBtn = document.getElementById('board2NextMove');
  if (board2NextBtn) {
    board2NextBtn.addEventListener('click', board2NextMove);
  }

  const board2PrevBtn = document.getElementById('board2PrevMove');
  if (board2PrevBtn) {
    board2PrevBtn.addEventListener('click', board2PrevMove);
  }

  // --- Flip Board 2 ---
  const flipBoard2 = document.getElementById('flip_board2');
  if (flipBoard2) {
    flipBoard2.addEventListener('click', function() {
      console.log('Flipping board 2 (myBoard2)');
      window.board2.flip();
    });
  }

  // --- Load PGN from Clipboard Button ---
  const loadPgnFromClipboardBtn = document.getElementById('loadPgnFromClipboard');
  if (loadPgnFromClipboardBtn) {
    loadPgnFromClipboardBtn.addEventListener('click', async function() {
      try {
        const clipboardText = await navigator.clipboard.readText();
        if (!clipboardText || clipboardText.trim() === '') {
          alert('Clipboard is empty. Please copy a PGN first.');
          return;
        }

        // Clean up PGN - remove headers, normalize whitespace
        let pgnText = clipboardText.trim();
        pgnText = pgnText.split('\n')
          .filter(line => !line.trim().startsWith('['))
          .join(' ')
          .replace(/\s+/g, ' ')
          .trim();

        // Validate PGN format
        if (!/\d+\./.test(pgnText)) {
          alert('Clipboard does not contain valid PGN.');
          return;
        }

        // Parse and load to board2
        if (typeof window.parsePgnToPositions === 'function') {
          window.analysisReportPositions = window.parsePgnToPositions(pgnText);
          window.analysisReportPositionIndex = 0;

          if (window.analysisReportPositions && window.analysisReportPositions.length > 0) {
            window.board2.position(window.analysisReportPositions[0]);
            updateBoard2MoveIndicator(0);
            document.getElementById('board2NavContainer').style.display = 'block';
            showStatus(`Loaded ${window.analysisReportPositions.length} positions from clipboard`, true);
          }
        }
      } catch (err) {
        console.error('Failed to read clipboard:', err);
        alert('Could not read clipboard. Please check permissions.');
      }
    });
  }

  // --- Keyboard Navigation for Board2 ---
  document.addEventListener('keydown', function(e) {
    // Only if not in input field
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    if (e.key === 'ArrowLeft') {
      board2PrevMove();
      e.preventDefault();
    } else if (e.key === 'ArrowRight') {
      board2NextMove();
      e.preventDefault();
    }
  });

  // --- Load Analysis Report from Clipboard ---
  const loadBtn = document.getElementById('loadAnalysisReport');
  if (loadBtn) {
    loadBtn.addEventListener('click', async function() {
      try {
        const clipboardText = await navigator.clipboard.readText();
        loadAnalysisReportFromContent(clipboardText, 'clipboard');
      } catch (err) {
        console.error('Failed to read clipboard:', err);
        alert('Could not read clipboard. Please check permissions.');
      }
    });
  }

  // --- Report Folder Input Handler ---
  const reportFolderInput = document.getElementById('reportFolderInput');
  if (reportFolderInput) {
    reportFolderInput.addEventListener('change', async function(e) {
      const files = Array.from(e.target.files);

      // Filter for .txt files only
      const txtFiles = files.filter(file => file.name.toLowerCase().endsWith('.txt'));

      if (txtFiles.length === 0) {
        showStatus('No .txt files found in selected folder', false);
        return;
      }

      // Sort files naturally (handles numbers correctly)
      txtFiles.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));

      // Store files for later use
      window.loadedReportFiles = txtFiles;

      // Show the View Reports button
      const viewBtn = document.getElementById('viewPreloadedReports');
      if (viewBtn) {
        viewBtn.style.display = 'inline-block';
      }

      // Update count display
      const countDisplay = document.getElementById('reportsCountDisplay');
      if (countDisplay) {
        countDisplay.textContent = `${txtFiles.length} Reports Loaded`;
      }

      showStatus(`Loaded ${txtFiles.length} report files. Click "View Reports" to select.`, true);

      // Auto-open the modal
      openReportFilesModal();
    });
  }

  // --- View Reports Button ---
  const viewReportsBtn = document.getElementById('viewPreloadedReports');
  if (viewReportsBtn) {
    viewReportsBtn.addEventListener('click', openReportFilesModal);
  }

  // --- Close Modal Button ---
  const closeModalBtn = document.getElementById('closeReportFilesModal');
  if (closeModalBtn) {
    closeModalBtn.addEventListener('click', function() {
      document.getElementById('reportFilesModal').style.display = 'none';
    });
  }

  // --- Close modal when clicking outside ---
  const modal = document.getElementById('reportFilesModal');
  if (modal) {
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        modal.style.display = 'none';
      }
    });
  }

  // ============================================================
  // ANALYSIS REPORT CONTAINER EVENT LISTENERS
  // ============================================================

  // --- Toggle Report Button ---
  const toggleReportBtn = document.getElementById('toggleReportBtn');
  if (toggleReportBtn) {
    toggleReportBtn.addEventListener('click', function() {
      const reportText = document.getElementById('analysisReportText');
      const toggleBtn = document.getElementById('toggleReportBtn');

      if (reportText.style.display === 'none') {
        reportText.style.display = 'block';
        toggleBtn.textContent = 'Hide Report';
        toggleBtn.style.background = '#6c757d';  // Gray
      } else {
        reportText.style.display = 'none';
        toggleBtn.textContent = 'Show Report';
        toggleBtn.style.background = '#28a745';  // Green
      }
    });
  }

  // --- Save Report Button ---
  const saveReportBtn = document.getElementById('saveReportBtn');
  if (saveReportBtn) {
    saveReportBtn.addEventListener('click', function() {
      const reportText = document.getElementById('analysisReportText');
      if (reportText && reportText.textContent.trim()) {
        const content = reportText.textContent;
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-');
        a.download = `chess_analysis_report_${timestamp}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        alert('No report content to save.');
      }
    });
  }

  // --- Load PGN from Highlight Button ---
  const loadPgnFromHighlightBtn = document.getElementById('loadPgnFromHighlight');
  if (loadPgnFromHighlightBtn) {
    loadPgnFromHighlightBtn.addEventListener('click', function() {
      const selection = window.getSelection();
      const selectedText = selection.toString().trim();

      if (!selectedText || selectedText === '') {
        alert('No text is highlighted. Please highlight/select a PGN first.');
        return;
      }

      // Clean up PGN - remove headers, normalize whitespace
      let pgnText = selectedText;
      pgnText = pgnText.split('\n')
        .filter(line => !line.trim().startsWith('['))
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim();

      // Validate PGN format
      if (!/\d+\./.test(pgnText)) {
        alert('Selected text does not contain valid PGN.');
        return;
      }

      // Parse and load to board2
      if (typeof window.parsePgnToPositions === 'function') {
        window.analysisReportPositions = window.parsePgnToPositions(pgnText);
        window.analysisReportPositionIndex = 0;

        if (window.analysisReportPositions && window.analysisReportPositions.length > 0) {
          if (window.board2) {
            window.board2.position(window.analysisReportPositions[0]);
            updateBoard2MoveIndicator(0);
          }

          // Show navigation container
          const navContainer = document.getElementById('board2NavContainer');
          if (navContainer) {
            navContainer.style.display = 'block';
          }

          showStatus(`Loaded ${window.analysisReportPositions.length} positions from highlighted PGN`, true);
        }
      } else {
        alert('PGN parser not available.');
      }
    });
  }

  // --- Load Reference Image Button ---
  const loadRefImageBtn = document.getElementById('loadRefImageBtn');
  if (loadRefImageBtn) {
    loadRefImageBtn.addEventListener('click', function() {
      if (refImageLoaded) {
        // Show modal with existing image
        document.getElementById('refImageModal').style.display = 'block';
      } else {
        // Open file picker
        document.getElementById('refImageFileInput').click();
      }
    });
  }

  // --- Reference Image File Input ---
  const refImageFileInput = document.getElementById('refImageFileInput');
  if (refImageFileInput) {
    refImageFileInput.addEventListener('change', function(e) {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function(event) {
          const img = document.getElementById('refImagePreview');
          img.src = event.target.result;
          img.style.display = 'block';
          document.getElementById('refImagePlaceholder').style.display = 'none';
          document.getElementById('loadRefImageBtn').textContent = '🖼️ ' + file.name;
          refImageLoaded = true;
          document.getElementById('refImageModal').style.display = 'block';
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // --- Close Reference Image Modal ---
  const closeRefImageModalBtn = document.getElementById('closeRefImageModal');
  if (closeRefImageModalBtn) {
    closeRefImageModalBtn.addEventListener('click', function() {
      document.getElementById('refImageModal').style.display = 'none';
    });
  }

  // --- Reference Image Modal Click Outside ---
  const refImageModal = document.getElementById('refImageModal');
  if (refImageModal) {
    refImageModal.addEventListener('click', function(e) {
      if (e.target === refImageModal) {
        refImageModal.style.display = 'none';
      }
    });
  }

  // --- Reference Image Zoom Toggle ---
  const refImagePreview = document.getElementById('refImagePreview');
  if (refImagePreview) {
    refImagePreview.addEventListener('click', function() {
      if (refImageIsEnlarged) {
        this.style.maxWidth = '100%';
        this.style.maxHeight = '70vh';
        this.style.cursor = 'zoom-in';
        refImageIsEnlarged = false;
      } else {
        this.style.maxWidth = 'none';
        this.style.maxHeight = 'none';
        this.style.cursor = 'zoom-out';
        refImageIsEnlarged = true;
      }
    });
  }

});
