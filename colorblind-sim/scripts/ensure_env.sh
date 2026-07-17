#!/usr/bin/env bash
# Persistent reusable venv for the colorblind-sim skill.
#
# Cache location:
#   ~/.cache/cursor-skills/colorblind-sim/
#   ├── README.txt
#   ├── requirements.txt.sha256
#   └── venv/
#
# Backend: python -m venv (pure-Python deps only; no Bioconda binaries).
#
# Force rebuild:
#   bash scripts/ensure_env.sh --force-rebuild
#   rm -rf ~/.cache/cursor-skills/colorblind-sim

set -euo pipefail

SKILL_NAME="colorblind-sim"
CACHE_ROOT="${HOME}/.cache/cursor-skills/${SKILL_NAME}"
ENV_PREFIX="${CACHE_ROOT}/venv"
SPEC_HASH_FILE="${CACHE_ROOT}/requirements.txt.sha256"
CACHE_README="${CACHE_ROOT}/README.txt"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REQ_FILE="${SKILL_ROOT}/requirements.txt"

FORCE_REBUILD=0
PRINT_PYTHON=0
PRINT_PREFIX=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Ensure a persistent Python venv for ${SKILL_NAME}.

Options:
  --print-python     Print the skill Python interpreter path (stdout).
  --print-prefix     Print the environment prefix directory (stdout).
  --force-rebuild    Delete and recreate the cached environment.
  -h, --help         Show this help.

Environment location:
  ${ENV_PREFIX}

Delete manually to reclaim disk space:
  rm -rf ${CACHE_ROOT}
EOF
}

die() {
  echo "ensure_env.sh: $*" >&2
  exit 1
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --print-python)
        PRINT_PYTHON=1
        shift
        ;;
      --print-prefix)
        PRINT_PREFIX=1
        shift
        ;;
      --force-rebuild)
        FORCE_REBUILD=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1 (try --help)"
        ;;
    esac
  done
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    die "Need sha256sum or shasum to track requirements.txt changes."
  fi
}

find_host_python() {
  local candidate
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      command -v "${candidate}"
      return 0
    fi
  done
  die "Need python3 (3.10+ recommended) on PATH to create the skill venv."
}

venv_python() {
  if [[ -x "${ENV_PREFIX}/bin/python" ]]; then
    echo "${ENV_PREFIX}/bin/python"
  elif [[ -x "${ENV_PREFIX}/Scripts/python.exe" ]]; then
    echo "${ENV_PREFIX}/Scripts/python.exe"
  else
    echo ""
  fi
}

write_cache_readme() {
  cat > "${CACHE_README}" <<EOF
colorblind-sim persistent environment
=====================================

Location: ${ENV_PREFIX}
Spec:     ${REQ_FILE}
Backend:  python -m venv

Rebuild:
  bash ${SCRIPT_DIR}/ensure_env.sh --force-rebuild
  rm -rf ${CACHE_ROOT}

This cache is outside the repository and .cursor/skills tree. Do not commit it.
EOF
}

env_ready() {
  local py
  py="$(venv_python)"
  [[ -n "${py}" && -x "${py}" ]] || return 1
  [[ -x "${ENV_PREFIX}/bin/cbviz" ]] || [[ -x "${ENV_PREFIX}/bin/cbviz-fast" ]] || return 1
  if [[ -f "${SPEC_HASH_FILE}" ]]; then
    local expected actual
    expected="$(cat "${SPEC_HASH_FILE}")"
    actual="$(sha256_file "${REQ_FILE}")"
    [[ "${expected}" == "${actual}" ]] || return 1
  else
    return 1
  fi
  return 0
}

create_env() {
  local host_py
  host_py="$(find_host_python)"
  echo "ensure_env.sh: creating venv at ${ENV_PREFIX} with ${host_py}" >&2
  mkdir -p "${CACHE_ROOT}"
  rm -rf "${ENV_PREFIX}"
  "${host_py}" -m venv "${ENV_PREFIX}"
  local py
  py="$(venv_python)"
  [[ -n "${py}" ]] || die "venv created but python is missing under ${ENV_PREFIX}"
  "${py}" -m pip install --upgrade pip setuptools wheel
  echo "ensure_env.sh: installing dependencies from requirements.txt (may need network)" >&2
  "${py}" -m pip install -r "${REQ_FILE}"
  sha256_file "${REQ_FILE}" > "${SPEC_HASH_FILE}"
  write_cache_readme
  [[ -x "${ENV_PREFIX}/bin/cbviz" ]] || die "cbviz console script missing after install"
  [[ -x "${ENV_PREFIX}/bin/cbviz-fast" ]] || die "cbviz-fast console script missing after install"
  echo "ensure_env.sh: environment ready at ${ENV_PREFIX}" >&2
}

main() {
  parse_args "$@"
  [[ -f "${REQ_FILE}" ]] || die "Missing requirements.txt: ${REQ_FILE}"

  if [[ "${FORCE_REBUILD}" -eq 1 ]]; then
    echo "ensure_env.sh: --force-rebuild: removing ${CACHE_ROOT}" >&2
    rm -rf "${CACHE_ROOT}"
  fi

  if ! env_ready; then
    create_env
  fi

  local py
  py="$(venv_python)"
  [[ -n "${py}" ]] || die "Environment python missing after ensure"

  if [[ "${PRINT_PYTHON}" -eq 1 ]]; then
    echo "${py}"
    exit 0
  fi
  if [[ "${PRINT_PREFIX}" -eq 1 ]]; then
    echo "${ENV_PREFIX}"
    exit 0
  fi

  echo "ensure_env.sh: using ${ENV_PREFIX}" >&2
  echo "ensure_env.sh: python=${py}" >&2
}

main "$@"
