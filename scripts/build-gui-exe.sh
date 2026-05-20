#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python -m pip install -r backend/requirements.txt
python -m pip install -r desktop_native/requirements-build.txt

pyinstaller \
  --name SafePromptGuard \
  --onefile \
  --windowed \
  --paths backend \
  --add-data "shared:shared" \
  desktop_native/safeprompt_gui.py

echo "GUI executable created under dist/"
