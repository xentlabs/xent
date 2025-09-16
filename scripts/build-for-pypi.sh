#!/bin/bash
set -e

echo "Cleaning previous build artifacts..."
rm -rf \
  dist \
  build \
  *.egg-info \
  src/*.egg-info \
  src/xent/web/static

echo "Building web frontend..."
cd web
npm install
npm run build

echo "Web files built directly to src/xent/web/static/"
cd ..

echo "Building Python package..."
uv build

echo "Build complete! Artifacts in dist/"
