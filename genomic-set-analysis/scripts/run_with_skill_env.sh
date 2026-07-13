#!/usr/bin/env bash
# Run any command with the persistent genomic-set-analysis skill environment.
#
# Example:
#   scripts/run_with_skill_env.sh scripts/intervene_peaks_combine.py --help
#
# Environment cache:
#   ~/.cache/ai-skills-env/genomic-set-analysis/conda-env/

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $(basename "$0") <command> [args...]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$("${SCRIPT_DIR}/ensure_env.sh" --print-python)"
PREFIX="$("${SCRIPT_DIR}/ensure_env.sh" --print-prefix)"

export GENOMIC_SET_ANALYSIS_ENV_ACTIVE=1
export PATH="${PREFIX}/bin:${PATH}"

if [[ "$1" == *.py ]]; then
  exec "${PYTHON}" "$@"
fi

exec "$@"
