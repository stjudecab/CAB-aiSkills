#!/usr/bin/env bash
# Run a command inside the bioinformatics-reporting persistent venv.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$("${SCRIPT_DIR}/ensure_env.sh" --print-python)"
PREFIX="$("${SCRIPT_DIR}/ensure_env.sh" --print-prefix)"
export PATH="${PREFIX}/bin:${PATH}"
if [[ $# -eq 0 ]]; then
  echo "Usage: $(basename "$0") <command> [args...]" >&2
  exit 1
fi
if [[ "$1" == *.py ]]; then
  exec "${PYTHON}" "$@"
fi
exec "$@"
