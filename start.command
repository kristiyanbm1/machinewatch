#!/bin/sh
# macOS/Linux launcher. Run from Terminal, or double-click on macOS.
set -eu
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
if [ ! -f .venv/setup-complete ]; then
    .venv/bin/python -m pip install -r requirements.txt
    touch .venv/setup-complete
fi
if [ ! -f data/machinewatch.db ]; then
    .venv/bin/python -m machinewatch prepare
fi
printf '\nOpen http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.\n\n'
.venv/bin/python -m machinewatch serve
