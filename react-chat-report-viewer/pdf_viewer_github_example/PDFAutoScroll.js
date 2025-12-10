import React, { useState, useEffect, useRef, useCallback } from 'react';

const PDFAutoScroll = ({ pdfViewerRef }) => {
  // State variables for auto-scroll feature
  const [autoScrollActive, setAutoScrollActive] = useState(false);
  const [scrollIntervalSeconds, setScrollIntervalSeconds] = useState(13);
  const [soundEnabled, setSoundEnabled] = useState(true);
  
  // References for tracking scroll timing and audio
  const lastScrollTimeRef = useRef(Date.now());
  const audioContextRef = useRef(null);
  const currentPageRef = useRef(1);
  
  // Function to play a subtle audio beep
  const playSubtleBeep = useCallback(() => {
    if (!soundEnabled) return;
    
    try {
      // Create audio context on first use
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      
      const context = audioContextRef.current;
      
      // Create oscillator for sound generation
      const oscillator = context.createOscillator();
      const gainNode = context.createGain();
      
      // Configure sound properties (gentle, quiet beep)
      oscillator.type = 'sine';
      oscillator.frequency.value = 800;
      gainNode.gain.value = 0.05;
      
      // Connect audio nodes
      oscillator.connect(gainNode);
      gainNode.connect(context.destination);
      
      // Play very short beep
      gainNode.gain.setValueAtTime(0.05, context.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.15);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.15);
    } catch (error) {
      console.error('Error playing notification sound:', error);
    }
  }, [soundEnabled]);
  
  // Function to simulate clicking the Next button
  const simulateNextButtonClick = useCallback(() => {
    // Find the Next button
    const nextButton = document.querySelector('#next-page-button');
    if (nextButton && !nextButton.disabled) {
      // Click the button
      nextButton.click();
      return true;
    }
    return false;
  }, []);
  
  // Function to reset the scroll timer
  const resetScrollTimer = useCallback(() => {
    lastScrollTimeRef.current = Date.now();
  }, []);
  
  // Function to perform the scroll action in PDF context
  const performScroll = useCallback(() => {
    if (!pdfViewerRef.current) return;
    
    try {
      // Get current page and total pages
      const viewer = pdfViewerRef.current;
      const currentPage = viewer.currentPageNumber || 1;
      const totalPages = viewer.pagesCount || 1;
      
      // Safety check for valid values
      if (currentPage <= 0 || totalPages <= 0) return;
      
      // Get the PDF container for scroll position check
      const pdfContainer = viewer.container;
      if (!pdfContainer) return;
      
      // Get the current zoom level
      const zoomElement = document.querySelector('.pdf-zoom-controls span');
      const currentZoom = zoomElement ? 
        parseInt(zoomElement.textContent.replace('%', ''), 10) / 100 : 1;
      const isZoomedIn = currentZoom > 1.05; // Consider anything over 105% as zoomed in
      
      // Check if we're at the bottom of the current page when zoomed in
      const isAtBottom = Math.abs(
        (pdfContainer.scrollTop + pdfContainer.clientHeight) - 
        pdfContainer.scrollHeight
      ) < 20; // Allow small margin of error
      
      // If zoomed in and not at bottom of page yet, scroll to bottom instead of changing page
      if (isZoomedIn && !isAtBottom && currentPage < totalPages) {
        // Scroll to the bottom of the page
        pdfContainer.scrollTo({
          top: pdfContainer.scrollHeight,
          behavior: 'smooth'
        });
        
        // Play sound if enabled
        if (soundEnabled) {
          playSubtleBeep();
        }
        
        // Reset timer after scrolling
        resetScrollTimer();
        return;
      }
      
      // If we can move to the next page (we're either not zoomed or already at bottom)
      if (currentPage < totalPages) {
        // If at normal zoom (100%), use the ',' key method (maintain scroll position)
        // If zoomed in, use the 'm' key method (reset scroll position)
        if (!isZoomedIn) {
          // Create a custom event for changing page without resetting scroll
          const pageChangeEvent = new CustomEvent('pageChangeNoScroll', { 
            detail: { newPage: currentPage + 1 } 
          });
          document.dispatchEvent(pageChangeEvent);
        } else {
          // Reset scroll position to top first
          if (pdfContainer) {
            pdfContainer.scrollTop = 0;
          }
          
          // Simulate clicking the Next button (standard method with scroll reset)
          const success = simulateNextButtonClick();
          
          // If button click simulation was successful
          if (success) {
            // Play sound if enabled
            if (soundEnabled) {
              playSubtleBeep();
            }
          } else {
            // Fallback if button click simulation fails
            currentPageRef.current = currentPage + 1;
            
            // Dispatch event to change page
            const pageChangeEvent = new CustomEvent('pageChange', { 
              detail: { newPage: currentPage + 1 } 
            });
            document.dispatchEvent(pageChangeEvent);
            
            // Play sound if enabled
            if (soundEnabled) {
              playSubtleBeep();
            }
          }
        }
        
        // Always reset the timer after advancing
        resetScrollTimer();
      } else {
        // We're at the last page, nothing to do
        console.log("Reached the last page of the document");
      }
    } catch (error) {
      console.error('Error during auto-scroll:', error);
      // Don't let errors break the auto-scroll functionality
      resetScrollTimer();
    }
  }, [pdfViewerRef, soundEnabled, playSubtleBeep, simulateNextButtonClick, resetScrollTimer]);
  
  // Set up interval for auto-scrolling with error recovery
  useEffect(() => {
    let intervalId;
    let errorCount = 0;
    
    if (autoScrollActive) {
      intervalId = setInterval(() => {
        try {
          // Get current time
          const now = Date.now();
          // Only scroll if enough time has passed
          if (now - lastScrollTimeRef.current >= scrollIntervalSeconds * 1000) {
            performScroll();
            // Reset error count on successful scroll
            if (errorCount > 0) errorCount = 0;
          }
        } catch (error) {
          // Error recovery strategy
          errorCount++;
          console.error(`Auto-scroll error (${errorCount}/3):`, error);
          
          // If we encounter too many errors, disable auto-scroll to prevent a bad user experience
          if (errorCount >= 3) {
            console.warn("Too many auto-scroll errors, disabling auto-scroll");
            setAutoScrollActive(false);
            errorCount = 0;
            
            // Show error message to user
            alert("Auto-scroll has been disabled due to errors. You can try enabling it again or use manual scrolling.");
          }
          
          // Update last scroll time to prevent rapid retries
          lastScrollTimeRef.current = Date.now();
        }
      }, 1000); // Check every second
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [autoScrollActive, performScroll, scrollIntervalSeconds]);
  
  // Monitor page changes
  useEffect(() => {
    // Instead of event listeners, we'll watch for changes to the pageNumber
    if (pdfViewerRef.current) {
      const newPage = pdfViewerRef.current.currentPageNumber;
      if (newPage !== currentPageRef.current) {
        currentPageRef.current = newPage;
        lastScrollTimeRef.current = Date.now();
      }
    }
  }, [pdfViewerRef]);
  
  // Function to increase scroll speed
  const increaseSpeed = () => {
    setScrollIntervalSeconds(prev => Math.max(1, prev - 1));
  };
  
  // Function to decrease scroll speed
  const decreaseSpeed = () => {
    setScrollIntervalSeconds(prev => Math.min(60, prev + 1));
  };
  
  // Toggle auto-scroll on/off
  const toggleAutoScroll = useCallback(() => {
    setAutoScrollActive(prev => {
      // Reset timer when turning on
      if (!prev) {
        lastScrollTimeRef.current = Date.now();
      }
      return !prev;
    });
  }, []);
  
  // Listen for various events
  useEffect(() => {
    // Toggle auto-scroll with keyboard
    const handleKeyDown = (e) => {
      // Toggle auto-scroll with "/" key
      if (e.key === '/') {
        toggleAutoScroll();
      }
      
      // Simulate page down with 'm' key (resets scroll position)
      if (e.key === 'm' || e.key === 'M') {
        resetScrollTimer();
        
        // Reset the scroll position of the PDF container
        if (pdfViewerRef.current && pdfViewerRef.current.container) {
          pdfViewerRef.current.container.scrollTop = 0;
        }
        
        simulateNextButtonClick();
      }
      
      // Go to next page with ',' key (maintains scroll position)
      if (e.key === ',') {
        resetScrollTimer();
        
        // Get the next page button but don't change scroll position
        const nextButton = document.querySelector('#next-page-button');
        
        // Store current scroll position
        let scrollPos = 0;
        if (pdfViewerRef.current && pdfViewerRef.current.container) {
          scrollPos = pdfViewerRef.current.container.scrollTop;
        }
        
        // Click the next button if it's not disabled
        if (nextButton && !nextButton.disabled) {
          nextButton.click();
          
          // Restore scroll position after a small delay to let the page change complete
          setTimeout(() => {
            if (pdfViewerRef.current && pdfViewerRef.current.container) {
              pdfViewerRef.current.container.scrollTop = scrollPos;
            }
          }, 50);
        }
      }
    };
    
    // Handle reset timer event from manual page navigation
    const handleResetTimer = () => {
      resetScrollTimer();
    };
    
    // Add event listeners
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('resetAutoScrollTimer', handleResetTimer);
    
    // Cleanup
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('resetAutoScrollTimer', handleResetTimer);
    };
  }, [toggleAutoScroll, resetScrollTimer, simulateNextButtonClick, pdfViewerRef]);
  
  return (
    <div className="pdf-auto-scroll-controls">
      <button 
        onClick={toggleAutoScroll}
        className={`scroll-toggle ${autoScrollActive ? 'active' : ''}`}
      >
        Auto-Scroll {autoScrollActive ? 'ON (/)' : 'OFF (/)'}
      </button>
      
      <div className="speed-controls">
        <button onClick={increaseSpeed} disabled={scrollIntervalSeconds <= 1}>-</button>
        <span className="interval-display">{scrollIntervalSeconds}s</span>
        <button onClick={decreaseSpeed} disabled={scrollIntervalSeconds >= 60}>+</button>
      </div>
      
      <div className="sound-controls">
        <span>Sound:</span>
        <label>
          <input
            type="radio"
            checked={soundEnabled}
            onChange={() => setSoundEnabled(true)}
          />
          On
        </label>
        <label>
          <input
            type="radio"
            checked={!soundEnabled}
            onChange={() => setSoundEnabled(false)}
          />
          Off
        </label>
      </div>
    </div>
  );
};

export default PDFAutoScroll;