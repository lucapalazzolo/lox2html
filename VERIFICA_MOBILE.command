#!/usr/bin/env bash
# Kept for compatibility: the complete suite now lives in VERIFICA.command.
set -euo pipefail
cd "$(dirname "$0")"
exec bash VERIFICA.command "$@"
