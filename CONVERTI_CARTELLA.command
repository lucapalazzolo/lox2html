#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$#" -lt 1 ]; then
  printf '%s\n' 'Usage: bash CONVERTI_CARTELLA.command /path/to/folder [--recursive] [--crs EPSG:32632] [-o /path/output]'
  exit 2
fi
if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
exec "$PYTHON" batch_convert.py "$@"
