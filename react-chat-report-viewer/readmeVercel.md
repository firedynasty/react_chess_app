# PDF Viewer with Auto-Scroll Vercel Deployment Guide

This guide provides steps to deploy the PDF Viewer with Auto-Scroll application on Vercel.

## Prerequisites

- A Vercel account (create one at [vercel.com](https://vercel.com))
- Git repository with your PDF Viewer code
- Node.js installed locally

## Deployment Steps

1. **Prepare Your Application**
   - Ensure your package.json has the correct build scripts:
     ```json
     "scripts": {
       "start": "react-scripts start",
       "build": "react-scripts build",
       "test": "react-scripts test",
       "eject": "react-scripts eject"
     }
     ```
   - Verify your application works locally with `npm start`

2. **Initialize Vercel (If Not Already Done)**
   - Install Vercel CLI: `npm i -g vercel`
   - Login to Vercel: `vercel login`

3. **Deploy to Vercel**
   - Method 1: Vercel CLI
     ```bash
     # In your project directory
     vercel
     ```
   - Method 2: GitHub Integration
     - Connect your GitHub repo to Vercel
     - Select your repository
     - Configure project settings:
       - Framework preset: Create React App
       - Build command: `npm run build`
       - Output directory: `build`
       - Install command: `npm install`

4. **Configure Environment Variables (If Needed)**
   - Add any required environment variables in the Vercel dashboard
   - Go to Project → Settings → Environment Variables

5. **Custom Domain (Optional)**
   - Add a custom domain in the Vercel dashboard
   - Project → Settings → Domains → Add

## Project Configuration

The project uses the following Vercel-specific configuration in `vercel.json`:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "build"
      }
    }
  ],
  "routes": [
    {
      "src": "^/static/(.*)",
      "headers": { "cache-control": "public, max-age=31536000, immutable" },
      "dest": "/static/$1"
    },
    {
      "src": "/(.*\\.(js|css|svg|png|jpg|jpeg|gif|ico|pdf))",
      "dest": "/$1"
    },
    {
      "src": "/(.*)",
      "dest": "/index.html"
    }
  ]
}
```

This configuration ensures proper routing for a single-page application and handles PDF files correctly.

## Handling PDF Files

- Place PDF files in the `public` directory to make them accessible at runtime
- Reference PDFs using relative paths, e.g., `/sample.pdf` rather than hardcoded absolute URLs
- For dynamic PDF loading, consider these options:
  1. Store PDFs in the public directory (smaller apps)
  2. Use a content delivery network (CDN) like Cloudinary or AWS S3 (larger apps)
  3. Implement a serverless function to serve PDFs from external storage

## Auto-Scroll Implementation

The auto-scroll functionality requires no special configuration for Vercel deployment, but ensure:

- All JavaScript files for PDFViewer and PDFAutoScroll components are properly bundled
- CSS files are correctly imported in your components
- Any keyboard shortcuts or scroll settings are documented for users

## Troubleshooting

- **Build Failures**: Check the build logs in the Vercel dashboard
- **PDF Loading Issues**: Ensure PDFs are properly stored and referenced with correct paths
- **404 Errors**: Verify the rewrites configuration in vercel.json
- **Performance Issues**: Consider setting up Vercel Analytics for monitoring

## Useful Commands

```bash
# Deploy with environment variables
vercel --env KEY=VALUE

# Preview deployment
vercel --preview

# Deploy to production
vercel --prod

# Get deployment logs
vercel logs [deployment-url]
```

## Additional Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Create React App Deployment](https://create-react-app.dev/docs/deployment/)
- [Handling Static Files in Vercel](https://vercel.com/guides/using-static-files)
- [PDF.js Documentation](https://mozilla.github.io/pdf.js/)