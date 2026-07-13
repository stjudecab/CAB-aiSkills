#!/usr/bin/env bash
# Run a command with the genomic-regions-annotation cached environment on PATH.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$("${SCRIPT_DIR}/ensure_env.sh" --print-python)"
PREFIX="$("${SCRIPT_DIR}/ensure_env.sh" --print-prefix)"
export PATH="${PREFIX}/bin:${PATH}"
if [[ $# -eq 0 ]]; then
  echo "Usage: bash scripts/run_with_skill_env.sh <command> [args...]" >&2
  exit 2
fi
if [[ "${1}" == *.py ]]; then
  exec "${PYTHON}" "$@"
fi
exec "$@"
