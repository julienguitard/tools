#!/usr/bin/env bash
# generate.sh — Thin wrapper around generate.py
# Usage: ./generate.sh [output_path]
# Default output: .julien/diagram_tables.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="${1:-${SCRIPT_DIR}/../diagram_tables.md}"

python3 "${SCRIPT_DIR}/generate.py" --output "$OUTPUT"
