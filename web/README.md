# XEGA Web Interface

This is the web frontend for the XEGA benchmark monitoring system.

## Development

### Prerequisites
- Node.js 18+ and npm
- XEGA backend installed (`pip install -e .` in project root)

### Setup
```bash
# Install dependencies
npm install

# Start development servers (frontend + backend)
../scripts/dev_web.sh

# Or run separately:
# Terminal 1: Backend (from project root)
uv run xega serve --dev

# Terminal 2: Frontend (from web directory)
npm run dev
```

The frontend dev server runs on http://localhost:5173 and proxies API requests to the backend on http://localhost:8000.

### Building for Production
```bash
# Build static files
npm run build

# Or use the build script
../scripts/build_web.sh
```

Built files are output to `../src/xega/web/static/` and are served by the FastAPI backend in production.

## Architecture

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS (via CDN)
- **API Client**: Native fetch API
- **WebSocket**: Native WebSocket API for real-time updates

## Project Structure
```
web/
├── src/
│   ├── api/          # API client
│   ├── components/   # React components
│   ├── hooks/        # Custom React hooks
│   ├── types/        # TypeScript type definitions
│   ├── App.tsx       # Main application component
│   └── main.tsx      # Application entry point
├── index.html        # HTML template
├── package.json      # Node dependencies
├── tsconfig.json     # TypeScript configuration
└── vite.config.ts    # Vite build configuration
```

## Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build production bundle
- `npm run preview` - Preview production build locally