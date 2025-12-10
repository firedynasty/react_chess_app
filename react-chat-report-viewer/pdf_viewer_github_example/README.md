# PDF Viewer with Auto-Scroll and Text Layering

This directory contains components that combine the text layering capabilities of React-PDF with the auto-scroll functionality of the original PDF viewer.

## Features

- **Text Selection**: Users can select and copy text from PDFs
- **Accessibility**: Text layer is fully accessible to screen readers
- **Auto-Scroll**: Automatically advances through the document
- **Keyboard Shortcuts**: Convenient navigation with keyboard controls
- **Zoom Controls**: Easily adjust the document display size

## Components

1. **PDFViewerWithAutoScroll.js**: Main PDF viewer component that supports text selection
2. **PDFAutoScroll.js**: Adds auto-scrolling functionality
3. **pdfViewerStyles.css**: CSS styles for the viewer

## Dependencies

This implementation requires:

```
"react": "^18.2.0",
"react-dom": "^18.2.0",
"react-pdf": "^7.7.0",
"pdfjs-dist": "^4.8.69"
```

## Usage

```jsx
import React from 'react';
import PDFViewerWithAutoScroll from './pdf_viewer_github_example/PDFViewerWithAutoScroll';

function App() {
  const pdfUrl = 'https://example.com/sample.pdf';
  
  return (
    <div>
      <h1>PDF Viewer Demo</h1>
      <PDFViewerWithAutoScroll pdfUrl={pdfUrl} title="Searchable Document" />
    </div>
  );
}
```

## Keyboard Shortcuts

- `/`: Toggle auto-scroll on/off
- `m` or `,`: Go to next page
- `z`: Go to previous page
- `x`: Scroll up within the current page
- `c`: Scroll down within the current page
- `o`: Scroll to top of the current page
- `p`: Scroll to bottom of the current page
- `+` or `=`: Zoom in
- `-`: Zoom out
- `r`: Reset view (first page, 100% zoom)

## How It Works

The implementation uses React-PDF for document rendering with text layer support. The auto-scroll functionality is adapted from the original canvas-based viewer but works with the React-PDF components.

Key improvements:
- Text selection works properly through React-PDF's text layer
- PDF rendering is handled by the React-PDF library rather than canvas
- Auto-scroll functionality is preserved in a library-agnostic way

This approach provides the best of both worlds: proper text selection and the convenient auto-scroll functionality.