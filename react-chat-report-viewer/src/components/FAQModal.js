import React, { useEffect, useState } from 'react';
import './FAQModal.css';

const FAQModal = ({ isOpen, onClose }) => {
  const [faqContent, setFaqContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return;

    const fetchFAQContent = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Access the file directly from the public directory
        const response = await fetch('/how_auto_scroll_works_and_key_codes.txt');
        
        if (!response.ok) {
          throw new Error(`Failed to fetch FAQ content: ${response.status}`);
        }
        
        const data = await response.text();
        setFaqContent(data);
        setIsLoading(false);
      } catch (err) {
        console.error('Error fetching FAQ content:', err);
        setError('Failed to load FAQ content. Please try again later.');
        setIsLoading(false);
      }
    };

    fetchFAQContent();
    
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

  // Function to parse and format the text content into HTML
  const formatFAQContent = (content) => {
    if (!content) return null;

    // Prepare the content - remove any HTML-like content
    const cleanContent = content.replace(/<[^>]*>/g, '');
    
    // Extract the important sections and ignore the implementation details at the end
    const mainContent = cleanContent.split('BUILDING:')[0];
    
    // Split content by sections
    const sections = mainContent.split(/\n\n+/);
    
    return (
      <div className="faq-formatted-content">
        {sections.map((section, index) => {
          // Skip empty sections
          if (!section.trim()) return null;
          
          // Check if this is a section heading
          if (section.match(/^[A-Z][A-Z\s-]+:/)) {
            const [heading, ...lines] = section.split('\n');
            const headingText = heading.replace(':', '').trim();
            
            return (
              <div key={index} className="faq-section">
                <h3>{headingText}</h3>
                <ul>
                  {lines
                    .filter(line => line.trim() && !line.match(/^-+$/)) // Skip separator lines
                    .map((line, lineIndex) => {
                      // Format the line - highlight key patterns
                      let formattedLine = line.trim();
                      
                      // Handle bullet points
                      if (formattedLine.startsWith('- ')) {
                        formattedLine = formattedLine.substring(2);
                        
                        // Highlight keyboard keys
                        formattedLine = formattedLine.replace(/'([^']+)'/g, "<strong>$1 key</strong>");
                        
                        return <li key={lineIndex} dangerouslySetInnerHTML={{ __html: formattedLine }} />;
                      } else if (formattedLine.match(/^\d+\./)) {
                        // It's a numbered list item - don't process it as a paragraph
                        return <p key={lineIndex} className="faq-list-item">{formattedLine}</p>;
                      }
                      
                      return <p key={lineIndex}>{formattedLine}</p>;
                    })}
                </ul>
              </div>
            );
          }
          
          // It's a regular paragraph
          if (section.trim()) {
            return <p key={index} className="faq-paragraph">{section}</p>;
          }
          
          return null;
        })}
      </div>
    );
  };

  return (
    <div className="faq-modal-overlay">
      <div className="faq-modal">
        <div className="faq-modal-header">
          <h2>How to Use PDF Viewer with Auto-Scroll</h2>
          <button className="faq-close-button" onClick={onClose}>×</button>
        </div>
        <div className="faq-modal-content">
          {isLoading ? (
            <div className="faq-loading">Loading FAQ content...</div>
          ) : error ? (
            <div className="faq-error">{error}</div>
          ) : (
            formatFAQContent(faqContent)
          )}
        </div>
      </div>
    </div>
  );
};

export default FAQModal;