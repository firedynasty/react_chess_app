import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import PDFAutoScroll from './PDFAutoScroll';
import './pdfViewerStyles.css';

// Set up the worker for PDF.js
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

const PDFViewerWithAutoScroll = ({ pdfUrl, title }) => {
  // State variables for PDF viewing
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [pdfFile, setPdfFile] = useState(pdfUrl || null);
  const [error, setError] = useState(null);
  
  // Refs
  const containerRef = useRef(null);
  const textLayerRef = useRef(null);
  
  // Reference object for auto-scroll component
  const pdfViewerRef = useRef({
    currentPageNumber: 1,
    pagesCount: 0,
    container: null
  });

  // Set PDF from props if provided
  useEffect(() => {
    if (pdfUrl) {
      setPdfFile(pdfUrl);
    }
  }, [pdfUrl]);

  // Update the pdfViewerRef whenever pageNumber or numPages changes
  useEffect(() => {
    pdfViewerRef.current.currentPageNumber = pageNumber;
    if (containerRef.current) {
      pdfViewerRef.current.container = containerRef.current;
    }
  }, [pageNumber]);

  useEffect(() => {
    pdfViewerRef.current.pagesCount = numPages || 0;
  }, [numPages]);

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    setPageNumber(1);
    setError(null);
    pdfViewerRef.current.pagesCount = numPages;
  };

  const onDocumentLoadError = (error) => {
    console.error('Error loading PDF:', error);
    setError('Failed to load PDF. Please try a different file.');
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      setPdfFile(file);
      setError(null);
    } else if (file) {
      setError('Please select a valid PDF file.');
      setPdfFile(null);
    }
  };

  // Handle page navigation
  const changePage = useCallback((offset, resetScroll = true) => {
    if (!numPages) return;
    
    // Create and dispatch an event to notify auto-scroll component to reset timer
    const resetTimerEvent = new CustomEvent('resetAutoScrollTimer');
    document.dispatchEvent(resetTimerEvent);
    
    // Reset scroll position when changing pages (if resetScroll is true)
    if (resetScroll && containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
    
    setPageNumber(prevPageNumber => {
      const newPageNumber = prevPageNumber + offset;
      return Math.min(Math.max(1, newPageNumber), numPages);
    });
  }, [numPages]);

  // Handle zoom controls
  const zoomIn = useCallback(() => {
    setScale(prevScale => Math.min(prevScale + 0.25, 4.0));
  }, []);
  
  const zoomOut = useCallback(() => {
    setScale(prevScale => Math.max(prevScale - 0.25, 0.5));
  }, []);

  // Reset the PDF view
  const resetPDFView = useCallback(() => {
    setScale(1.0);
    setPageNumber(1);
    if (containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, []);

  // Listen for page change events from auto-scroll and handle key navigation
  useEffect(() => {
    const handlePageChange = (event) => {
      const { newPage } = event.detail;
      if (newPage && newPage <= numPages) {
        setPageNumber(newPage);
      }
    };
    
    // Handle page change without scroll reset
    const handlePageChangeNoScroll = (event) => {
      const { newPage } = event.detail;
      if (newPage && newPage <= numPages) {
        changePage(newPage - pageNumber, false);
      }
    };
    
    // Handle keyboard navigation for scrolling within PDF container
    const handleKeyDown = (e) => {
      // Find the PDF container element which has the scrollbar
      const pdfContainer = containerRef.current;
      if (!pdfContainer) return;
      
      if (e.key === 'x' || e.key === 'X') {
        // Scroll up within the PDF container
        pdfContainer.scrollBy({
          top: -150,
          behavior: 'smooth'
        });
        e.preventDefault(); // Prevent default browser behavior
      } else if (e.key === 'c' || e.key === 'C') {
        // Scroll down within the PDF container
        pdfContainer.scrollBy({
          top: 150,
          behavior: 'smooth'
        });
        e.preventDefault(); // Prevent default browser behavior
      } else if (e.key === 'o' || e.key === 'O') {
        // Scroll to top of the page (like Home key)
        pdfContainer.scrollTo({
          top: 0,
          behavior: 'smooth'
        });
        e.preventDefault(); // Prevent default browser behavior
      } else if (e.key === 'p' || e.key === 'P') {
        // Scroll to bottom of the page (like End key)
        pdfContainer.scrollTo({
          top: pdfContainer.scrollHeight,
          behavior: 'smooth'
        });
        
        // Reset auto-scroll timer
        const resetTimerEvent = new CustomEvent('resetAutoScrollTimer');
        document.dispatchEvent(resetTimerEvent);
        
        e.preventDefault(); // Prevent default browser behavior
      } else if (e.key === 'r' || e.key === 'R') {
        // Reset to first page with zoom at 100%
        resetPDFView();
        
        // Reset auto-scroll timer
        const resetTimerEvent = new CustomEvent('resetAutoScrollTimer');
        document.dispatchEvent(resetTimerEvent);
        
        e.preventDefault(); // Prevent default browser behavior
      } else if (e.key === '=' || e.key === '+') {
        // Zoom in
        zoomIn();
        e.preventDefault(); // Prevent default browser behavior
      } else if (e.key === '-') {
        // Zoom out
        zoomOut();
        e.preventDefault(); // Prevent default browser behavior
      }
    };
    
    document.addEventListener('pageChange', handlePageChange);
    document.addEventListener('pageChangeNoScroll', handlePageChangeNoScroll);
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('pageChange', handlePageChange);
      document.removeEventListener('pageChangeNoScroll', handlePageChangeNoScroll);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [numPages, changePage, pageNumber, resetPDFView, zoomIn, zoomOut]);

  return (
    <div className="pdf-viewer-container">
      <div className="pdf-viewer-inner">
        <h2 className="pdf-viewer-title">
          {title || 'PDF Viewer with Auto-Scroll'}
        </h2>
        
        {!pdfUrl && (
          <div className="pdf-file-input">
            <label className="pdf-file-label">
              Choose PDF File:
              <input 
                type="file"
                accept="application/pdf"
                onChange={handleFileChange}
                className="pdf-file-input-field"
              />
            </label>
          </div>
        )}
        
        {error && (
          <div className="pdf-error">
            {error}
          </div>
        )}
        
        {pdfFile && (
          <div className="pdf-content">
            <div className="pdf-toolbar">
              <div className="pdf-nav-buttons">
                <button 
                  onClick={() => changePage(-1)} 
                  disabled={pageNumber <= 1}
                >
                  Previous (z/o)
                </button>
                <span className="pdf-page-info">
                  Page {pageNumber} of {numPages || '?'}
                </span>
                <button 
                  onClick={() => changePage(1)} 
                  disabled={pageNumber >= numPages}
                  id="next-page-button"
                >
                  Next (m/,/p)
                </button>
              </div>
              
              <div className="pdf-zoom-controls">
                <button onClick={zoomOut} disabled={scale <= 0.5}>-</button>
                <span>{Math.round(scale * 100)}%</span>
                <button onClick={zoomIn} disabled={scale >= 4.0}>+</button>
                <button onClick={resetPDFView}>Reset (r)</button>
              </div>
            </div>

            {/* Auto-scroll controls */}
            <PDFAutoScroll pdfViewerRef={pdfViewerRef} />
            
            <div className="pdf-document-container" ref={containerRef}>
              <Document
                file={pdfFile}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                className="pdf-document"
              >
                <Page 
                  pageNumber={pageNumber} 
                  scale={scale}
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                  className="pdf-page"
                  inputRef={textLayerRef}
                />
              </Document>
            </div>
            
            <p className="pdf-info-text">
              Text in this PDF is fully selectable!
            </p>
            <p className="pdf-info-small">
              The text layer is accessible to screen readers and assistive technologies.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PDFViewerWithAutoScroll;