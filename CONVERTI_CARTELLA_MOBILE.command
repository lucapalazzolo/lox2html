#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$#" -lt 1 ]; then
  echo 'Uso: bash CONVERTI_CARTELLA_MOBILE.command /percorso/cartella [--recursive] [-o /percorso/output]'
  exit 2
fi
if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
exec "$PYTHON" batch_convert_mobile.py "$@"
