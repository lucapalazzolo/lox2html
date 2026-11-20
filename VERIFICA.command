#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
"$PYTHON" verifica_integrita.py
"$PYTHON" -m unittest discover -s tests -v
if command -v node >/dev/null 2>&1; then
  node tests/check_universal_viewer.cjs
  node tests/check_viewer_js.cjs
  node tests/check_mobile_js.cjs
  node tests/check_joystick_js.cjs
else
  echo 'Node.js non installato: test JavaScript ignorati; test Python completati.'
fi
