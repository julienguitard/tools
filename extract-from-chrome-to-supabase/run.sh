#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
MAIN="$SCRIPT_DIR/chrome_to_supabase.py"

# ── Bootstrap venv if missing ────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
  echo "⏳ Creating virtual environment…"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# ── Install / update deps if requirements changed ───────────────────
MARKER="$VENV_DIR/.requirements.sha"
CURRENT_SHA=$(shasum "$REQUIREMENTS" | awk '{print $1}')

if [[ ! -f "$MARKER" ]] || [[ "$(cat "$MARKER")" != "$CURRENT_SHA" ]]; then
  echo "📦 Installing dependencies…"
  pip install -q -r "$REQUIREMENTS"
  echo "$CURRENT_SHA" > "$MARKER"
fi

# ── Run ──────────────────────────────────────────────────────────────
python "$MAIN" "$@"
