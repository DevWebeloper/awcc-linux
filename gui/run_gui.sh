#!/usr/bin/env bash
# Runner for Alienware Mode & Turbo GTK4 Adwaita App
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_APP="$SCRIPT_DIR/alienware_adwaita_app.py"

if [ ! -f "$PYTHON_APP" ]; then
    echo "Error: $PYTHON_APP not found"
    exit 1
fi

chmod +x "$PYTHON_APP"
exec python3 "$PYTHON_APP" "$@"
