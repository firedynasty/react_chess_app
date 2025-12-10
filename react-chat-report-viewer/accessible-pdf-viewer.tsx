import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// Set up the worker for PDF.js
// This is required for react-pdf to work
pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js`;

const AccessiblePDFViewer = () => {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [pdfFile, setPdfFile] = useState(null);
  const [error, setError] = useState(null);

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    setPageNumber(1);
    setError(null);
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

  const changePage = (offset) => {
    const newPage = pageNumber + offset;
    if (newPage >= 1 && newPage <= numPages) {
      setPageNumber(newPage);
    }
  };

  const changeZoom = (newScale) => {
    setScale(newScale);
  };

  // Define styles for text layer (crucial for accessibility)
  const textLayerStyles = {
    '.react-pdf__Page__textContent': {
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      overflow: 'hidden',
      lineHeight: 1.0,
      position: 'absolute',
    },
    '.react-pdf__Page__textContent > span': {
      color: 'transparent',
      position: 'absolute',
      whiteSpace: 'pre',
      cursor: 'text',
      transformOrigin: '0% 0%',
    },
    '.react-pdf__Page__textContent > span::selection': {
      backgroundColor: 'rgb(0, 128, 255, 0.3)',
    },
    '.react-pdf__Page__annotations': {
      position: 'absolute',
      top: 0,
      left: 0,
      bottom: 0,
      right: 0,
      overflow: 'hidden',
      pointerEvents: 'none',
    },
  };

  return (
    <div className="flex flex-col items-center p-4 w-full">
      <div className="w-full max-w-4xl bg-gray-100 rounded-lg p-6 shadow-md">
        <h2 className="text-2xl font-bold mb-4 text-center text-gray-800">Accessible PDF Viewer</h2>
        
        <div className="mb-6">
          <label className="block mb-2 font-medium text-gray-700">
            Choose PDF File:
            <input 
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
              className="mt-2 block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
            />
          </label>
        </div>
        
        {error && (
          <div className="mb-4 p-4 text-red-700 bg-red-100 rounded-md">
            {error}
          </div>
        )}
        
        {pdfFile && (
          <div className="flex flex-col items-center">
            <div className="mb-4 border border-gray-300 rounded-lg overflow-auto bg-white">
              <Document
                file={pdfFile}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                className="mx-auto"
              >
                <Page 
                  pageNumber={pageNumber} 
                  scale={scale}
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                  customTextRenderer={({ str, itemIndex }) => (
                    <mark key={itemIndex} className="bg-transparent text-transparent selection:bg-blue-200 selection:text-black">
                      {str}
                    </mark>
                  )}
                />
              </Document>
            </div>
            
            <div className="w-full flex justify-between items-center mb-4">
              <div className="space-x-2">
                <button 
                  onClick={() => changePage(-1)} 
                  disabled={pageNumber <= 1}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md disabled:bg-gray-400"
                >
                  Previous
                </button>
                <button 
                  onClick={() => changePage(1)} 
                  disabled={pageNumber >= numPages}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md disabled:bg-gray-400"
                >
                  Next
                </button>
              </div>
              
              <div className="text-gray-700">
                Page {pageNumber} of {numPages || '?'}
              </div>
              
              <div className="space-x-2">
                <button 
                  onClick={() => changeZoom(Math.max(0.5, scale - 0.2))} 
                  className="px-3 py-1 bg-gray-200 rounded-md"
                >
                  -
                </button>
                <span className="text-gray-700">{Math.round(scale * 100)}%</span>
                <button 
                  onClick={() => changeZoom(scale + 0.2)}
                  className="px-3 py-1 bg-gray-200 rounded-md"
                >
                  +
                </button>
              </div>
            </div>
            
            <p className="text-center text-green-600 font-medium">
              Text in this PDF is selectable! Try selecting some text on the page.
            </p>
            <p className="text-sm text-gray-500 mt-2 text-center">
              The text layer is fully accessible to screen readers and assistive technologies.
            </p>
          </div>
        )}
      </div>
      
      {/* Inject text layer styles */}
      <style jsx global>{`
        .react-pdf__Page__textContent {
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          overflow: hidden;
          line-height: 1.0;
          position: absolute;
        }
        .react-pdf__Page__textContent > span {
          color: transparent;
          position: absolute;
          white-space: pre;
          cursor: text;
          transform-origin: 0% 0%;
        }
        .react-pdf__Page__textContent > span::selection {
          background-color: rgba(0, 128, 255, 0.3);
        }
        .react-pdf__Page__annotations {
          position: absolute;
          top: 0;
          left: 0;
          bottom: 0;
          right: 0;
          overflow: hidden;
          pointer-events: none;
        }
      `}</style>
    </div>
  );
};

export default AccessiblePDFViewer;