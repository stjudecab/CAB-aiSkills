#!/usr/bin/env bash
# Persistent reusable Conda environment for genomic-regions-annotation.
#
# Cache location:
#   ~/.cache/cursor-skills/genomic-regions-annotation/
#   ├── README.txt
#   ├── environment.yml.sha256
#   └── conda-env/
#
# Backend: micromamba -> mamba -> conda (prefix install). Required because the
# skill needs bedtools, pybedtools, and optionally ucsc-liftover.
#
# Force rebuild:
#   bash scripts/ensure_env.sh --force-rebuild
#   rm -rf ~/.cache/cursor-skills/genomic-regions-annotation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SPEC_FILE="${SKILL_ROOT}/environment/epi_anno_env.yml"
CACHE_ROOT="${HOME}/.cache/cursor-skills/genomic-regions-annotation"
PREFIX="${CACHE_ROOT}/conda-env"
HASH_FILE="${CACHE_ROOT}/environment.yml.sha256"

FORCE_REBUILD=0
PRINT_PYTHON=0
PRINT_PREFIX=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force-rebuild) FORCE_REBUILD=1; shift ;;
    --print-python) PRINT_PYTHON=1; shift ;;
    --print-prefix) PRINT_PREFIX=1; shift ;;
    -h|--help)
      cat <<EOF
Usage: bash scripts/ensure_env.sh [--force-rebuild] [--print-python] [--print-prefix]
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "${SPEC_FILE}" ]]; then
  echo "Missing environment spec: ${SPEC_FILE}" >&2
  exit 1
fi

hash_spec() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${SPEC_FILE}" | awk '{print $1}'
  else
    shasum -a 256 "${SPEC_FILE}" | awk '{print $1}'
  fi
}

find_conda_like() {
  if command -v micromamba >/dev/null 2>&1; then
    echo micromamba
  elif command -v mamba >/dev/null 2>&1; then
    echo mamba
  elif command -v conda >/dev/null 2>&1; then
    echo conda
  else
    echo ""
  fi
}

TOOL="$(find_conda_like)"
if [[ -z "${TOOL}" ]]; then
  echo "Need micromamba, mamba, or conda on PATH to create the skill environment." >&2
  exit 1
fi

CURRENT_HASH="$(hash_spec)"
NEED_CREATE=0
if [[ "${FORCE_REBUILD}" -eq 1 ]]; then
  NEED_CREATE=1
elif [[ ! -x "${PREFIX}/bin/python" ]]; then
  NEED_CREATE=1
elif [[ ! -f "${HASH_FILE}" ]] || [[ "$(cat "${HASH_FILE}")" != "${CURRENT_HASH}" ]]; then
  NEED_CREATE=1
fi

if [[ "${NEED_CREATE}" -eq 1 ]]; then
  mkdir -p "${CACHE_ROOT}"
  if [[ -d "${PREFIX}" ]]; then
    rm -rf "${PREFIX}"
  fi
  echo "Creating genomic-regions-annotation env with ${TOOL} at ${PREFIX}" >&2
  if [[ "${TOOL}" == "micromamba" ]]; then
    micromamba create -y -p "${PREFIX}" -f "${SPEC_FILE}"
  else
    # shellcheck disable=SC1091
    export CONDA_SOLVER="${CONDA_SOLVER:-libmamba}"
    "${TOOL}" env create -y -p "${PREFIX}" -f "${SPEC_FILE}"
  fi
  echo "${CURRENT_HASH}" > "${HASH_FILE}"
  cat > "${CACHE_ROOT}/README.txt" <<EOF
genomic-regions-annotation persistent environment
prefix: ${PREFIX}
rebuild: bash scripts/ensure_env.sh --force-rebuild
delete:  rm -rf ${CACHE_ROOT}
EOF
fi

if [[ ! -x "${PREFIX}/bin/python" ]]; then
  echo "Environment python missing at ${PREFIX}/bin/python" >&2
  exit 1
fi

for bin in bedtools; do
  if [[ ! -x "${PREFIX}/bin/${bin}" ]]; then
    echo "Required binary missing in env: ${PREFIX}/bin/${bin}" >&2
    exit 1
  fi
done

if [[ "${PRINT_PYTHON}" -eq 1 ]]; then
  echo "${PREFIX}/bin/python"
fi
if [[ "${PRINT_PREFIX}" -eq 1 ]]; then
  echo "${PREFIX}"
fi

if [[ "${PRINT_PYTHON}" -eq 0 && "${PRINT_PREFIX}" -eq 0 ]]; then
  echo "Ready: ${PREFIX}"
  echo "Python: ${PREFIX}/bin/python"
fi
