#!/usr/bin/env bash
# Persistent reusable environment for the genomic-set-analysis skill.
#
# Storage (created on first use, reused thereafter):
#   ~/.cache/ai-skills-env/genomic-set-analysis/conda-env/
#
# Force a clean rebuild:
#   scripts/ensure_env.sh --force-rebuild
# or delete the cache directory:
#   rm -rf ~/.cache/ai-skills-env/genomic-set-analysis
#
# This skill needs Bioconda binaries (intervene, bedtools), so a Conda-family
# prefix install is used—not a plain venv and not a global install.

set -euo pipefail

SKILL_NAME="genomic-set-analysis"
CACHE_ROOT="${HOME}/.cache/ai-skills-env/${SKILL_NAME}"
ENV_PREFIX="${CACHE_ROOT}/conda-env"
SPEC_HASH_FILE="${CACHE_ROOT}/environment.yml.sha256"
CACHE_README="${CACHE_ROOT}/README.txt"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_YML="${SKILL_ROOT}/environment.yml"

FORCE_REBUILD=0
PRINT_PYTHON=0
PRINT_PREFIX=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Ensure a persistent Conda/micromamba environment for ${SKILL_NAME}.

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
    die "Need sha256sum or shasum to track environment.yml changes."
  fi
}

init_conda_if_needed() {
  if command -v conda >/dev/null 2>&1; then
    return 0
  fi
  local candidate
  for candidate in \
    "${CONDA_EXE:-}" \
    "${HOME}/micromamba/bin/conda" \
    "${HOME}/miniconda3/bin/conda" \
    "${HOME}/anaconda3/bin/conda" \
    "${HOME}/programs/anaconda3/bin/conda" \
    "/opt/conda/bin/conda" \
    "/opt/miniconda3/bin/conda"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      # shellcheck disable=SC1090
      eval "$("${candidate}" shell.bash hook)"
      return 0
    fi
  done
  return 1
}

find_mamba_exe() {
  local candidate
  if command -v mamba >/dev/null 2>&1; then
    command -v mamba
    return 0
  fi
  for candidate in \
    "${MAMBA_EXE:-}" \
    "${HOME}/micromamba/bin/mamba" \
    "${HOME}/miniconda3/bin/mamba" \
    "${HOME}/anaconda3/bin/mamba" \
    "${HOME}/programs/anaconda3/bin/mamba" \
    "/opt/conda/bin/mamba" \
    "/opt/miniconda3/bin/mamba"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done
  return 1
}

find_solver() {
  if command -v micromamba >/dev/null 2>&1; then
    echo "micromamba"
    return 0
  fi
  if [[ -n "${MAMBA_EXE:-}" && -x "${MAMBA_EXE}" ]]; then
    echo "micromamba"
    return 0
  fi
  init_conda_if_needed || true
  if find_mamba_exe >/dev/null 2>&1; then
    echo "mamba"
    return 0
  fi
  if command -v conda >/dev/null 2>&1; then
    echo "conda"
    return 0
  fi
  die "No Conda-family tool found. Install micromamba, mamba, or conda and retry."
}

configure_conda_solver() {
  # libmamba uses far less RAM than the classic conda solver during repodata/metadata work.
  if [[ -n "${CONDA_SOLVER:-}" ]]; then
    echo "ensure_env.sh: using CONDA_SOLVER=${CONDA_SOLVER} (from environment)." >&2
    return 0
  fi
  if ! command -v conda >/dev/null 2>&1; then
    return 0
  fi
  if conda config --show solvers 2>/dev/null | grep -q libmamba; then
    export CONDA_SOLVER=libmamba
    echo "ensure_env.sh: using CONDA_SOLVER=libmamba for lower memory use." >&2
    return 0
  fi
  echo "ensure_env.sh: classic conda solver selected; repodata fetch can use several GB of RAM." >&2
  echo "ensure_env.sh: for HPC nodes, prefer mamba/micromamba or: conda install -n base conda-libmamba-solver" >&2
}

handle_create_exit() {
  local status="$1"
  local solver="$2"
  if [[ "${status}" -eq 0 ]]; then
    return 0
  fi
  # 137 = SIGKILL (common OOM killer), 143 = SIGTERM (node/session preemption), 134 = SIGABRT.
  if [[ "${status}" -eq 137 || "${status}" -eq 143 || "${status}" -eq 134 ]]; then
    die "$(cat <<EOF
Solver (${solver}) was killed during environment creation (exit ${status}).

This is usually NOT a bug in ensure_env.sh. On HPC/interactive nodes the conda/mamba
process is often terminated by:
  - out-of-memory (OOM) while downloading/parsing bioconda repodata
  - interactive session or node preemption (your shell may jump to another host)

Try, in order:
  1. Request more memory on the interactive node (e.g. 8–16 GB for classic conda).
  2. Install a faster solver in base, then retry:
       conda install -n base -c conda-forge mamba
       bash ensure_env.sh --force-rebuild
     or:
       conda install -n base conda-libmamba-solver
       CONDA_SOLVER=libmamba bash ensure_env.sh --force-rebuild
  3. Use micromamba if available (ensure_env prefers it automatically).
  4. As a last resort on a workstation with enough RAM, run the rebuild there once;
     the cached prefix under ~/.cache/ai-skills-env/ is reused on later runs.
EOF
)"
  fi
  die "Environment creation via ${solver} failed with exit code ${status}."
}

env_spec_matches() {
  [[ -f "${SPEC_HASH_FILE}" ]] || return 1
  [[ "$(cat "${SPEC_HASH_FILE}")" == "$(sha256_file "${ENV_YML}")" ]]
}

env_is_ready() {
  [[ -x "${ENV_PREFIX}/bin/python" ]] \
    && [[ -x "${ENV_PREFIX}/bin/intervene" ]] \
    && env_spec_matches
}

write_cache_readme() {
  mkdir -p "${CACHE_ROOT}"
  cat > "${CACHE_README}" <<EOF
genomic-set-analysis persistent skill environment
=================================================

Prefix: ${ENV_PREFIX}
Spec:   ${ENV_YML}

This directory is managed by scripts/ensure_env.sh. It is created once and
reused on later skill runs. It is NOT stored inside the project repo.

Force rebuild:
  <skill>/scripts/ensure_env.sh --force-rebuild

Delete entirely:
  rm -rf ${CACHE_ROOT}
EOF
}

create_env() {
  local solver="$1"
  local status=0
  local mamba_exe=""
  mkdir -p "${CACHE_ROOT}"
  echo "ensure_env.sh: creating persistent environment at ${ENV_PREFIX} via ${solver}..." >&2
  echo "ensure_env.sh: spec ${ENV_YML}" >&2
  case "${solver}" in
    micromamba)
      if command -v micromamba >/dev/null 2>&1; then
        micromamba create -y -p "${ENV_PREFIX}" -f "${ENV_YML}" || status=$?
      else
        "${MAMBA_EXE}" create -y -p "${ENV_PREFIX}" -f "${ENV_YML}" || status=$?
      fi
      ;;
    mamba)
      init_conda_if_needed || true
      mamba_exe="$(find_mamba_exe)"
      [[ -n "${mamba_exe}" ]] || die "mamba executable not found after solver selection."
      echo "ensure_env.sh: mamba executable: ${mamba_exe}" >&2
      "${mamba_exe}" env create -y -p "${ENV_PREFIX}" -f "${ENV_YML}" || status=$?
      ;;
    conda)
      init_conda_if_needed || die "conda initialization failed."
      configure_conda_solver
      # Older conda releases reject ``-y`` on ``env create``; micromamba/mamba use ``-y``.
      conda env create -p "${ENV_PREFIX}" -f "${ENV_YML}" || status=$?
      ;;
    *)
      die "Internal error: unknown solver ${solver}"
      ;;
  esac
  handle_create_exit "${status}" "${solver}"
  sha256_file "${ENV_YML}" > "${SPEC_HASH_FILE}"
  write_cache_readme
  if ! env_is_ready; then
    die "Environment creation did not finish successfully. Check solver output above."
  fi
  echo "ensure_env.sh: environment ready." >&2
}

ensure_env() {
  [[ -f "${ENV_YML}" ]] || die "Missing environment spec: ${ENV_YML}"

  if [[ "${FORCE_REBUILD}" -eq 1 ]]; then
    echo "ensure_env.sh: --force-rebuild requested; removing ${ENV_PREFIX}" >&2
    rm -rf "${ENV_PREFIX}"
    rm -f "${SPEC_HASH_FILE}"
  fi

  if [[ -d "${ENV_PREFIX}" ]] && ! env_is_ready; then
    echo "ensure_env.sh: cached environment is missing tools or environment.yml changed; recreating..." >&2
    rm -rf "${ENV_PREFIX}"
    rm -f "${SPEC_HASH_FILE}"
  fi

  if ! env_is_ready; then
    create_env "$(find_solver)"
  fi

  [[ -x "${ENV_PREFIX}/bin/python" ]] || die "Python not found after environment setup: ${ENV_PREFIX}/bin/python"
}

main() {
  parse_args "$@"
  ensure_env
  if [[ "${PRINT_PYTHON}" -eq 1 ]]; then
    echo "${ENV_PREFIX}/bin/python"
  fi
  if [[ "${PRINT_PREFIX}" -eq 1 ]]; then
    echo "${ENV_PREFIX}"
  fi
}

main "$@"
