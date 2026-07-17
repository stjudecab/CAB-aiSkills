#!/usr/bin/env bash
# Run a command with the colorblind-sim persistent venv on PATH.
#
# Usage:
#   bash scripts/run_with_skill_env.sh scripts/run_colorblind_sim.py --help
#   bash scripts/run_with_skill_env.sh cbviz simulate -a infile.png outfile.png

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENSURE="${SCRIPT_DIR}/ensure_env.sh"

PYTHON="$("${ENSURE}" --print-python)"
PREFIX="$("${ENSURE}" --print-prefix)"
export PATH="${PREFIX}/bin:${PATH}"

if [[ $# -eq 0 ]]; then
  echo "Usage: bash scripts/run_with_skill_env.sh <command> [args...]" >&2
  exit 2
fi

if [[ "$1" == *.py ]]; then
  exec "${PYTHON}" "$@"
fi
exec "$@"
