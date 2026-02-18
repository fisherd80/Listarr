#!/bin/bash
# Build Tailwind CSS for Listarr
# Run this after modifying templates or when upgrading Tailwind version

set -e

# Pin to Tailwind v3.4.x for v3 compatibility (v4 has breaking class renames)
export TAILWINDCSS_VERSION=${TAILWINDCSS_VERSION:-v3.4.19}

# Ensure pytailwindcss is installed
pip show pytailwindcss > /dev/null 2>&1 || pip install pytailwindcss==0.3.0

# Build minified CSS
echo "Building Tailwind CSS (version $TAILWINDCSS_VERSION)..."
tailwindcss -i listarr/static/css/tailwind.src.css -o listarr/static/css/tailwind.css --minify

echo "Done! CSS written to listarr/static/css/tailwind.css"
echo "File size: $(wc -c < listarr/static/css/tailwind.css) bytes"
