#!/bin/bash
# Build script for debugging

echo "Building Next.js project..."
if npm run build --dry-run 2>&1 | grep -q "ERROR"; then
  echo "Build has errors!"
  exit 1
fi
echo "Build successful!"