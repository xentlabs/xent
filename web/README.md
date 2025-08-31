# XEGA Web Interface

Simple web frontend for monitoring XEGA benchmarks.

## Setup

```bash
# Install dependencies (one-time)
npm install

# Build production assets
npm run build
```

Built files are output to `../src/xega/web/static/` and served by the FastAPI backend.

## Usage

After building, start the web server from the project root:

```bash
uv run xega serve
```

Then open http://localhost:8000 in your browser.

## Structure

- `src/api/` - API client
- `src/components/` - React components  
- `src/hooks/` - Custom React hooks
- `src/types/` - TypeScript type definitions

The interface is read-only and displays benchmark progress and results in real-time via WebSocket connections.