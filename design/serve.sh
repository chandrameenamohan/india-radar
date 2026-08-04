#!/usr/bin/env bash
# Serve the repo root so every variant and the gallery resolve their data.
#
# Port 8732 deliberately: scripts/e2e.sh owns 8731 and scripts/worker-e2e.sh
# owns 8788. Concurrent agents running the gate WILL collide otherwise.
#
#   bash design/serve.sh            # foreground
#   http://127.0.0.1:8732/design/gallery.html
#   http://127.0.0.1:8732/design/iterations/<id>/index.html
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
exec "$PY" -m http.server "${1:-8732}" --bind 127.0.0.1
