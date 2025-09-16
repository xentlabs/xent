#!/bin/bash
set -e

echo "Building web frontend..."
cd web
npm install
npm run build

echo "Web files built directly to src/xent/web/static/"
cd ..

echo "Building Python package..."
uv build

echo "Build complete! Artifacts in dist/"
