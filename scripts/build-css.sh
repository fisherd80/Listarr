#!/bin/bash
# Build Tailwind CSS for Listarr
# Run this after modifying templates or when upgrading Tailwind version
#
# Handles UNC network paths (\\server\share) where Tailwind v3's glob
# scanner fails. Detects UNC paths and builds from a local temp copy.

set -e

# Pin to Tailwind v3.4.x for v3 compatibility (v4 has breaking class renames)
export TAILWINDCSS_VERSION=${TAILWINDCSS_VERSION:-v3.4.19}

# Ensure pytailwindcss is installed
pip show pytailwindcss > /dev/null 2>&1 || pip install pytailwindcss==0.3.0

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT="listarr/static/css/tailwind.src.css"
OUTPUT="listarr/static/css/tailwind.css"

echo "Building Tailwind CSS (version $TAILWINDCSS_VERSION)..."

# Detect UNC path (//server or \\server) — Tailwind v3 fast-glob cannot scan these
if [[ "$PROJECT_DIR" == //* ]] || [[ "$PROJECT_DIR" == \\\\* ]]; then
    echo "UNC path detected — building from local temp copy..."
    TMPDIR=$(mktemp -d)
    trap 'rm -rf "$TMPDIR"' EXIT

    # Copy only what Tailwind needs to scan + build
    cp -r "$PROJECT_DIR/listarr/templates" "$TMPDIR/templates"
    cp -r "$PROJECT_DIR/listarr/static/js" "$TMPDIR/js"
    cp "$PROJECT_DIR/$INPUT" "$TMPDIR/tailwind.src.css"
    cp "$PROJECT_DIR/tailwind.config.js" "$TMPDIR/tailwind.config.js"

    # Rewrite content paths for flat temp structure
    sed -i 's|./listarr/templates|./templates|;s|./listarr/static/js|./js|' "$TMPDIR/tailwind.config.js"

    # Build from temp dir
    cd "$TMPDIR"
    tailwindcss -i tailwind.src.css -o tailwind.css --minify

    # Copy result back
    cp tailwind.css "$PROJECT_DIR/$OUTPUT"
else
    cd "$PROJECT_DIR"
    tailwindcss -i "$INPUT" -o "$OUTPUT" --minify
fi

echo "Done! CSS written to $OUTPUT"
echo "File size: $(wc -c < "$PROJECT_DIR/$OUTPUT") bytes"
