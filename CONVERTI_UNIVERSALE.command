#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$#" -lt 1 ]; then
  echo 'Uso: bash CONVERTI_UNIVERSALE.command /percorso/rilievo.lox [--site-name "Nome"] [--crs EPSG:32632] [-o output.html]'
  exit 2
fi
if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
exec "$PYTHON" convert_lox_universal.py "$@"
