# XENT Web Interface

Simple web frontend for monitoring XENT benchmarks.

## Setup

```bash
# Install dependencies (one-time)
npm install

# Build production assets
npm run build
```

Built files are output to `../src/xent/web/static/` and served by the FastAPI backend.

## Usage

After building, start the web server from the project root:

```bash
uv run xent serve
```

Then open http://localhost:8000 in your browser.
