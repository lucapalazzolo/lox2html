#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$#" -lt 1 ]; then
  echo 'Uso: bash CONVERTI_MOBILE.command input.lox [--site-name "Nome"] [--type all|cave|mine] [--mine "*pattern*"] [-o output.html]'
  exit 2
fi
if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
exec "$PYTHON" convert_lox_mobile.py "$@"
