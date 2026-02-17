#!/bin/sh
# rename-papers — drop this in ~/.local/bin/ and chmod +x
#
# Usage:
#   rename-papers ~/Downloads/papers --dry-run
#   rename-papers ~/Downloads/papers

set -e

TOOL_DIR="${RENAME_PAPERS_HOME:-$HOME/Documents/99_Perso/Code/local_python/sandbox/tools/rename-papers}"

if [ ! -d "$TOOL_DIR/.venv" ]; then
    echo "First run — setting up venv in $TOOL_DIR ..."
    make -C "$TOOL_DIR" setup
fi

# Load .env (set -a exports every variable)
set -a
. "$TOOL_DIR/.env"
set +a

cd "$TOOL_DIR"
exec "$TOOL_DIR/.venv/bin/python" -m rename_papers "$@"
