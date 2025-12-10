import React, { useEffect } from 'react';
import './FAQModal.css';

const HardcodedFAQModal = ({ isOpen, onClose }) => {
  useEffect(() => {
    if (!isOpen) return;
    
    // Add event listener for escape key
    const handleEscapeKey = (event) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    
    document.addEventListener('keydown', handleEscapeKey);
    
    // Cleanup function to remove event listener
    return () => {
      document.removeEventListener('keydown', handleEscapeKey);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="faq-modal-overlay">
      <div className="faq-modal">
        <div className="faq-modal-header">
          <h2>How to Use PDF Viewer with Auto-Scroll</h2>
          <button className="faq-close-button" onClick={onClose}>×</button>
        </div>
        <div className="faq-modal-content">
          <div className="faq-formatted-content">
            {/* HOW AUTO-SCROLL WORKS section */}
            <div className="faq-section">
              <h3>HOW AUTO-SCROLL WORKS IN THE PDF VIEWER</h3>
              <ul>
                <p>The PDF Auto-Scroll feature automatically advances through PDF pages at a specified interval. Here's how it works:</p>
              </ul>
            </div>

            {/* KEY CONTROLS section */}
            <div className="faq-section">
              <h3>KEY CONTROLS</h3>
              <ul>
                <li dangerouslySetInnerHTML={{ __html: 'Press the <strong>/ key</strong> to toggle auto-scroll ON/OFF' }} />
                <li dangerouslySetInnerHTML={{ __html: 'Press <strong>m key</strong> to manually go to the next page (resets scroll position)' }} />
                <li dangerouslySetInnerHTML={{ __html: 'Press <strong>, key</strong> to manually go to the next page (maintains scroll position)' }} />
                <li dangerouslySetInnerHTML={{ __html: 'Press <strong>z key</strong> to manually go to the previous page (maintains scroll position)' }} />
                <li dangerouslySetInnerHTML={{ __html: 'Press <strong>o key</strong> to scroll to the top of the current page (like Home key)' }} />
                <li dangerouslySetInnerHTML={{ __html: 'Press <strong>p key</strong> to scroll to the bottom of the current page (like End key)' }} />
              </ul>
            </div>

            {/* PAGE NAVIGATION section */}
            <div className="faq-section">
              <h3>PAGE NAVIGATION</h3>
              <ul>
                <li>Click on the page number to edit it directly and navigate to a specific page</li>
                <li>Press Enter after editing to confirm and navigate to that page</li>
              </ul>
            </div>

            {/* AUTO-SCROLL FEATURES section */}
            <div className="faq-section">
              <h3>AUTO-SCROLL FEATURES</h3>
              <ul>
                <p className="faq-list-item">1. When activated (SCROLL ON), the viewer will automatically advance through pages:</p>
                <li>At normal zoom (100%): Uses the ',' key method that preserves scroll position</li>
                <li>When zoomed in: First scrolls to the bottom of the current page (like 'p' key), then advances to next page</li>
                
                <p className="faq-list-item">2. Speed Control:</p>
                <li>The "-" button increases scrolling speed (reduces interval time)</li>
                <li>The "+" button decreases scrolling speed (increases interval time)</li>
                <li>Default interval is 13 seconds</li>
                
                <p className="faq-list-item">3. Sound Feedback:</p>
                <li>Toggle sound ON/OFF via radio buttons</li>
                <li>When enabled, a subtle audio beep plays when changing pages</li>
              </ul>
            </div>

            {/* IMPLEMENTATION DETAILS section */}
            <div className="faq-section">
              <h3>IMPLEMENTATION DETAILS</h3>
              <ul>
                <li>Auto-scroll uses a timer (setInterval) that checks if enough time has passed since the last page change</li>
                <li>When the interval elapses, it automatically clicks the Next button</li>
                <li>The scroll timer resets whenever you manually navigate pages</li>
                <li>Error handling prevents issues if the PDF fails to load correctly</li>
                <li>The system automatically disables auto-scroll after multiple errors</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HardcodedFAQModal;