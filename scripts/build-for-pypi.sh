#!/bin/bash
set -e

echo "Cleaning previous build artifacts..."
rm -rf \
  dist \
  build \
  *.egg-info \
  src/*.egg-info \
  src/xent/web/static

echo "Removing cached Python bytecode..."
find src -type d -name "__pycache__" -exec rm -rf {} +

echo "Building web frontend..."
cd web
npm install
npm run build

echo "Web files built directly to src/xent/web/static/"
cd ..

echo "Building Python package..."
uv build

echo "Build complete! Artifacts in dist/"
