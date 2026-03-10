#!/usr/bin/env bash
# generate.sh — Thin wrapper around generate_data_diagram
# Usage: ./generate.sh [output_path]
# Default output: ../diagram_tables.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT="${1:-${SCRIPT_DIR}/../diagram_tables.md}"

cd "$PACKAGE_DIR"
python3 -m generate_data_diagram --output "$OUTPUT"
