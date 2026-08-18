#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Hasan Al Reza && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Hasan Al Reza < hasan.al.reza.bd@gmail.com >
# File Name: run_genomic_regions_correlation.py
# Description:
# Orchestrates reproducible GenometriCorr analyses for two BED region sets.
#########################################################################

"""Run reproducible pairwise GenometriCorr analyses on two BED files.

The wrapper validates and stages inputs, resolves an R runtime, supports local
or LSF execution, writes timestamped output directories, and records commands
and parameters in JSON metadata. It prints a dry-run plan by default.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Sequence


SKILL_NAME = "genomic-regions-correlation"
SKILL_VERSION = "0.2.0"
DEFAULT_CONDA_ENV = "genomic_regions_correlation"
RUN_ID_FORMAT = "%Y%m%dT%H%M%SZ"
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")

WRAPPER_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = WRAPPER_DIR / "scripts"
ENVIRONMENT_DIR = WRAPPER_DIR / "environment"
R_SCRIPT = SCRIPTS_DIR / "genometriCorr.r"
DEFAULT_CONDA_YAML = ENVIRONMENT_DIR / "genomic_regions_correlation.yml"
LOGGER = logging.getLogger(SKILL_NAME)


@dataclass(frozen=True)
class ResolvedInputs:
    """Resolved and staged BED input paths.

    Attributes:
        query (Path): Original query BED path.
        reference (Path): Original reference BED path.
        staged_query (Path): Query path inside the run directory.
        staged_reference (Path): Reference path inside the run directory.
        manifest_path (Path): Source-to-staged-input manifest.
    """

    query: Path
    reference: Path
    staged_query: Path
    staged_reference: Path
    manifest_path: Path


@dataclass(frozen=True)
class RunPlan:
    """Concrete run paths, commands, labels, and expected output files."""

    run_id: str
    run_dir: Path
    linked_inputs_dir: Path
    inputs: ResolvedInputs
    query_label: str
    reference_label: str
    command: list[str]
    expected_outputs: list[Path]
    metadata_path: Path
    job_script: Path


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv (Sequence[str] | None): Optional argument sequence.

    Returns:
        argparse.Namespace: Parsed command-line values.
    """

    parser = argparse.ArgumentParser(
        description="Compare two BED region sets with GenometriCorr."
    )
    parser.add_argument("--inputDir", type=Path, default=Path("."), help="Directory for relative BED paths.")
    parser.add_argument("--query", required=True, help="Query BED filename or path.")
    parser.add_argument("--reference", required=True, help="Reference BED filename or path.")
    parser.add_argument("--queryLabel", help="Display/output label for the query BED.")
    parser.add_argument("--referenceLabel", help="Display/output label for the reference BED.")
    parser.add_argument("--genome", required=True, choices=["hg19", "hg38", "mm10"], help="Genome build used by the TxDb.")
    parser.add_argument("--outputRoot", type=Path, default=Path("agentResults"), help="Root for timestamped outputs.")
    parser.add_argument("--outputPrefix", required=True, help="Descriptive prefix recorded in metadata.")
    parser.add_argument("--runId", help="UTC run ID in YYYYMMDDTHHMMSSZ format.")
    parser.add_argument("--run", action="store_true", help="Execute the analysis; dry run is the default.")
    parser.add_argument("--dryRun", action="store_true", help="Print the plan without executing.")
    parser.add_argument("--copyInputs", action="store_true", help="Copy BED files instead of staging symlinks.")
    parser.add_argument("--executor", choices=["local", "bsub"], default="local", help="Execution backend. Default: local.")
    parser.add_argument("--condaEnv", default=DEFAULT_CONDA_ENV, help=f"Conda environment name. Default: {DEFAULT_CONDA_ENV}.")
    parser.add_argument("--condaYaml", type=Path, default=DEFAULT_CONDA_YAML, help="Conda environment YAML used with --createCondaEnv.")
    parser.add_argument("--condaPrefix", type=Path, help="Existing conda environment prefix.")
    parser.add_argument("--createCondaEnv", action="store_true", help="Create the conda environment if it is missing.")
    parser.add_argument("--condaExecutable", default="conda", help="Conda executable for environment creation or dry-run commands.")
    parser.add_argument("--noConda", action="store_true", help="Use Rscript from the current PATH.")
    parser.add_argument("--proc", type=int, default=8, help="LSF core count. Default: 8.")
    parser.add_argument("--mem", type=int, default=128000, help="Total LSF memory in MB. Default: 128000.")
    parser.add_argument("--queue", default="cab_auto", help="LSF queue. Default: cab_auto.")
    parser.add_argument("--project", help="Optional LSF project passed with -P.")
    parser.add_argument("--jobName", help="LSF job name. Default: outputPrefix.")
    return parser.parse_args(argv)


def configure_logging() -> None:
    """Configure concise stdout logging for interactive and batch use."""

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)


def fail(message: str) -> None:
    """Exit with an actionable command-line error."""

    raise SystemExit(f"{SKILL_NAME} error: {message}")


def utc_run_id(value: str | None) -> str:
    """Return a validated user run ID or a current UTC run ID."""

    if value is None:
        return datetime.now(timezone.utc).strftime(RUN_ID_FORMAT)
    if not RUN_ID_PATTERN.fullmatch(value):
        fail(f"--runId must match YYYYMMDDTHHMMSSZ: {value}")
    return value


def resolve_path(path: Path) -> Path:
    """Expand and resolve a filesystem path without requiring it to exist."""

    return path.expanduser().resolve(strict=False)


def validate_file(path: Path, description: str) -> Path:
    """Validate and return an existing regular file path."""

    resolved = resolve_path(path)
    if not resolved.exists():
        fail(f"{description} does not exist: {resolved}")
    if not resolved.is_file():
        fail(f"{description} is not a regular file: {resolved}")
    return resolved


def validate_positive_integer(value: int, option: str) -> None:
    """Validate a positive integer CLI value."""

    if value <= 0:
        fail(f"{option} must be greater than zero: {value}")


def resolve_input(input_dir: Path, value: str, description: str) -> Path:
    """Resolve an absolute or input-directory-relative BED path."""

    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = input_dir / candidate
    return validate_file(candidate, description)


def derive_label(path: Path) -> str:
    """Derive a readable label by removing the final BED suffix."""

    name = path.name
    for suffix in (".bed.gz", ".bed"):
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name


def validate_label(value: str, option: str) -> str:
    """Validate a label used by the R script as part of an output filename."""

    if not value or value in {".", ".."}:
        fail(f"{option} must not be empty")
    if "/" in value or "\\" in value or "\x00" in value:
        fail(f"{option} cannot contain path separators or NUL characters: {value!r}")
    return value


def parse_env_list_output(raw_output: str, env_name: str) -> Path | None:
    """Extract a named conda environment prefix from `conda env list` output."""

    for raw_line in raw_output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("Name"):
            continue
        tokens = line.split()
        path_token = next((token for token in reversed(tokens) if token.startswith("/")), None)
        if path_token is None:
            continue
        prefix = Path(path_token)
        if prefix.name == env_name or (tokens and tokens[0] == env_name):
            return prefix
    return None


def find_conda_env_prefix(env_name: str, conda_executable: str) -> Path | None:
    """Find a conda environment using mamba or conda when available."""

    commands: list[list[str]] = []
    if shutil.which("mamba"):
        commands.append(["mamba", "env", "list"])
    if shutil.which(conda_executable):
        commands.append([conda_executable, "env", "list"])
    for command in commands:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        prefix = parse_env_list_output(
            f"{completed.stdout}\n{completed.stderr}", env_name
        )
        if prefix is not None and prefix.exists():
            return prefix
    return None


def create_conda_env(yaml_path: Path, env_name: str, conda_executable: str, dry_run: bool) -> None:
    """Create or print creation of a conda environment."""

    yaml_file = validate_file(yaml_path, "Conda YAML")
    executable = "mamba" if shutil.which("mamba") else conda_executable
    if shutil.which(executable) is None:
        fail(f"Conda executable is not available: {executable}")
    command = [executable, "env", "create", "-n", env_name, "-f", str(yaml_file)]
    LOGGER.info("Conda environment command: %s", shlex.join(command))
    if not dry_run:
        subprocess.run(command, check=True)


def ensure_genometricorr_package(r_command: list[str], allow_install: bool, dry_run: bool) -> None:
    """Check GenometriCorr and optionally install the upstream GitHub package."""

    check_code = "if (!requireNamespace('GenometriCorr', quietly=TRUE)) quit(status=1)"
    check_command = r_command + ["-e", check_code]
    if dry_run:
        if allow_install:
            LOGGER.info(
                "GenometriCorr install command: %s",
                shlex.join(r_command + ["-e", "remotes::install_github('favorov/GenometriCorr', upgrade='never')"]),
            )
        return
    check = subprocess.run(check_command, capture_output=True, text=True, check=False)
    if check.returncode == 0:
        return
    if not allow_install:
        fail(
            "GenometriCorr is not installed in the selected R runtime. "
            "Use --createCondaEnv with the bundled YAML to install the upstream package."
        )
    install_code = "remotes::install_github('favorov/GenometriCorr', upgrade='never')"
    install_command = r_command + ["-e", install_code]
    LOGGER.info("Installing upstream GenometriCorr package...")
    subprocess.run(install_command, check=True)


def resolve_r_command(args: argparse.Namespace, dry_run: bool) -> tuple[list[str], dict[str, str]]:
    """Resolve the Rscript command and environment for local or LSF execution."""

    environment = os.environ.copy()
    if args.noConda:
        rscript = shutil.which("Rscript") or "Rscript"
        if not dry_run and shutil.which("Rscript") is None:
            fail("Rscript is not on PATH; install R or omit --noConda to use conda.")
        return [rscript], environment

    prefix = resolve_path(args.condaPrefix) if args.condaPrefix else find_conda_env_prefix(args.condaEnv, args.condaExecutable)
    if prefix is not None:
        if not prefix.is_dir():
            fail(f"Conda prefix is not a directory: {prefix}")
        rscript = prefix / "bin" / "Rscript"
        if not dry_run and not rscript.is_file():
            fail(f"Rscript was not found in conda prefix: {rscript}")
        environment["PATH"] = str(prefix / "bin") + os.pathsep + environment.get("PATH", "")
        environment["CONDA_PREFIX"] = str(prefix)
        return [str(rscript)], environment

    if args.createCondaEnv:
        create_conda_env(args.condaYaml, args.condaEnv, args.condaExecutable, dry_run=dry_run)
        if not dry_run:
            prefix = find_conda_env_prefix(args.condaEnv, args.condaExecutable)
            if prefix is None:
                fail(f"Conda environment was created but could not be found: {args.condaEnv}")
            rscript = prefix / "bin" / "Rscript"
            if not rscript.is_file():
                fail(f"Rscript was not found in created conda prefix: {rscript}")
            environment["PATH"] = str(prefix / "bin") + os.pathsep + environment.get("PATH", "")
            environment["CONDA_PREFIX"] = str(prefix)
            return [str(rscript)], environment

    if dry_run:
        return [args.condaExecutable, "run", "-n", args.condaEnv, "Rscript"], environment
    fail(
        f"Conda environment {args.condaEnv!r} was not found. Use --createCondaEnv, "
        "--condaPrefix, or --noConda."
    )


def stage_inputs(query: Path, reference: Path, linked_dir: Path, manifest: Path, copy_inputs: bool, dry_run: bool) -> ResolvedInputs:
    """Stage the two BED inputs and write a source-to-stage manifest."""

    if query.name == reference.name:
        fail(f"Query and reference basenames collide during staging: {query.name}")
    staged_query = linked_dir / query.name
    staged_reference = linked_dir / reference.name
    if not dry_run:
        linked_dir.mkdir(parents=True, exist_ok=False)
        for source, target in ((query, staged_query), (reference, staged_reference)):
            if copy_inputs:
                shutil.copy2(source, target)
            else:
                target.symlink_to(source)
        manifest.write_text(
            f"{query}\t{staged_query}\n{reference}\t{staged_reference}\n",
            encoding="utf-8",
        )
    return ResolvedInputs(query, reference, staged_query, staged_reference, manifest)


def expected_outputs(run_dir: Path, query_label: str, reference_label: str) -> list[Path]:
    """Return the four PDF paths emitted by the bundled R script."""

    return [
        run_dir / f"{query_label}_versus_{reference_label}.projection.pdf.pdf",
        run_dir / f"{query_label}_versus_{reference_label}.vis.pdf",
        run_dir / f"{reference_label}_versus_{query_label}.projection.pdf",
        run_dir / f"{reference_label}_versus_{query_label}.vis.pdf",
    ]


def build_r_command(r_command: list[str], inputs: ResolvedInputs, query_label: str, reference_label: str, genome: str) -> list[str]:
    """Build the Rscript command using staged input paths."""

    return r_command + [
        str(R_SCRIPT),
        str(inputs.staged_query),
        str(inputs.staged_reference),
        query_label,
        reference_label,
        genome,
    ]


def build_bsub_command(args: argparse.Namespace, run_dir: Path, job_script: Path) -> list[str]:
    """Build the LSF submission command for a generated job script."""

    job_name = args.jobName or args.outputPrefix
    validate_positive_integer(args.proc, "--proc")
    validate_positive_integer(args.mem, "--mem")
    command = [
        "bsub", "-L", "/bin/bash", "-n", str(args.proc),
        "-R", "span[hosts=1]", "-R", f"rusage[mem={args.mem // args.proc}]",
        "-J", job_name, "-q", args.queue, "-cwd", str(run_dir),
    ]
    if args.project:
        command.extend(["-P", args.project])
    return command + ["<", str(job_script)]


def write_job_script(path: Path, run_dir: Path, command: list[str]) -> None:
    """Write an executable shell script for an LSF submission."""

    content = "#!/usr/bin/env bash\nset -euo pipefail\ncd " + shlex.quote(str(run_dir)) + "\n" + shlex.join(command) + "\n"
    path.write_text(content, encoding="utf-8")
    path.chmod(0o750)


def write_metadata(plan: RunPlan, args: argparse.Namespace, status: str, submission_output: str | None = None) -> None:
    """Write reproducibility metadata for a planned, local, or submitted run."""

    metadata = {
        "skillName": SKILL_NAME,
        "skillVersion": SKILL_VERSION,
        "runId": plan.run_id,
        "executionTimestampUtc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "runDir": str(plan.run_dir),
        "linkedInputsDir": str(plan.linked_inputs_dir),
        "manifestPath": str(plan.inputs.manifest_path),
        "query": str(plan.inputs.query),
        "reference": str(plan.inputs.reference),
        "stagedQuery": str(plan.inputs.staged_query),
        "stagedReference": str(plan.inputs.staged_reference),
        "queryLabel": plan.query_label,
        "referenceLabel": plan.reference_label,
        "genome": args.genome,
        "outputPrefix": args.outputPrefix,
        "expectedOutputs": [str(path) for path in plan.expected_outputs],
        "parameters": {
            "executor": args.executor,
            "condaEnv": None if args.noConda else args.condaEnv,
            "condaPrefix": str(args.condaPrefix) if args.condaPrefix else None,
            "copyInputs": args.copyInputs,
            "proc": args.proc,
            "mem": args.mem,
            "queue": args.queue,
            "project": args.project,
            "jobName": args.jobName or args.outputPrefix,
        },
        "command": plan.command,
        "jobScript": str(plan.job_script) if plan.job_script.exists() else None,
        "submissionOutput": submission_output,
    }
    plan.metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> None:
    """Validate inputs, execute or print a GenometriCorr run plan."""

    configure_logging()
    args = parse_arguments(argv)
    dry_run = args.dryRun or not args.run
    run_id = utc_run_id(args.runId)
    if args.dryRun and args.run:
        fail("--run and --dryRun cannot be used together")
    if args.executor == "bsub":
        validate_positive_integer(args.proc, "--proc")
        validate_positive_integer(args.mem, "--mem")

    input_dir = resolve_path(args.inputDir)
    if not input_dir.is_dir():
        fail(f"Input directory does not exist or is not a directory: {input_dir}")
    query = resolve_input(input_dir, args.query, "Query BED")
    reference = resolve_input(input_dir, args.reference, "Reference BED")
    validate_file(R_SCRIPT, "Bundled GenometriCorr R script")
    validate_label(args.outputPrefix, "--outputPrefix")
    validate_label(args.jobName or args.outputPrefix, "--jobName")
    query_label = validate_label(args.queryLabel or derive_label(query), "--queryLabel")
    reference_label = validate_label(args.referenceLabel or derive_label(reference), "--referenceLabel")

    run_dir = resolve_path(args.outputRoot) / f"{SKILL_NAME}-{run_id}"
    if run_dir.exists():
        fail(f"Run directory already exists; choose another --runId or --outputRoot: {run_dir}")
    linked_dir = run_dir / "linkedInputs"
    manifest = run_dir / "input-symlinks.tsv"
    metadata_path = run_dir / f"{SKILL_NAME}-run-metadata.json"
    job_script = run_dir / f"{args.jobName or args.outputPrefix}.commands.sh"
    inputs = stage_inputs(query, reference, linked_dir, manifest, args.copyInputs, dry_run=True)
    r_command, runtime_env = resolve_r_command(args, dry_run)
    ensure_genometricorr_package(
        r_command,
        allow_install=args.createCondaEnv and not args.noConda,
        dry_run=dry_run,
    )
    local_command = build_r_command(r_command, inputs, query_label, reference_label, args.genome)
    submission_command = build_bsub_command(args, run_dir, job_script) if args.executor == "bsub" else []
    display_command = submission_command if submission_command else local_command
    plan = RunPlan(run_id, run_dir, linked_dir, inputs, query_label, reference_label, display_command, expected_outputs(run_dir, query_label, reference_label), metadata_path, job_script)

    LOGGER.info("Run ID: %s", run_id)
    LOGGER.info("Run directory: %s", run_dir)
    LOGGER.info("Query: %s", query)
    LOGGER.info("Reference: %s", reference)
    LOGGER.info("Labels: %s | %s", query_label, reference_label)
    LOGGER.info("Executor: %s", args.executor)
    LOGGER.info("Command: %s", shlex.join(display_command))
    LOGGER.info("Expected outputs:")
    for path in plan.expected_outputs:
        LOGGER.info("  %s", path)
    if dry_run:
        LOGGER.info("Dry run complete. Use --run to execute.")
        return

    run_dir.mkdir(parents=True, exist_ok=False)
    inputs = stage_inputs(query, reference, linked_dir, manifest, args.copyInputs, dry_run=False)
    local_command = build_r_command(r_command, inputs, query_label, reference_label, args.genome)
    if args.executor == "local":
        plan = RunPlan(run_id, run_dir, linked_dir, inputs, query_label, reference_label, local_command, plan.expected_outputs, metadata_path, job_script)
        LOGGER.info("Running: %s", shlex.join(local_command))
        subprocess.run(local_command, cwd=run_dir, env=runtime_env, check=True)
        missing = [path for path in plan.expected_outputs if not path.is_file()]
        if missing:
            fail("GenometriCorr completed but expected outputs are missing:\n  " + "\n  ".join(map(str, missing)))
        write_metadata(plan, args, "completed")
        LOGGER.info("Metadata: %s", metadata_path)
        return

    plan = RunPlan(run_id, run_dir, linked_dir, inputs, query_label, reference_label, submission_command, plan.expected_outputs, metadata_path, job_script)
    write_job_script(job_script, run_dir, local_command)
    bsub_command = [part for part in submission_command if part != "<" and part != str(job_script)] + ["<", str(job_script)]
    if shutil.which("bsub") is None:
        fail("bsub is not available on PATH for --executor bsub")
    LOGGER.info("Submitting: %s", shlex.join(bsub_command))
    with job_script.open("rb") as job_handle:
        completed = subprocess.run(bsub_command[:-2], stdin=job_handle, text=False, capture_output=True, check=True)
    submission_output = (completed.stdout + completed.stderr).decode(errors="replace") if isinstance(completed.stdout, bytes) else (completed.stdout or "") + (completed.stderr or "")
    write_metadata(plan, args, "submitted", submission_output.strip())
    LOGGER.info("Metadata: %s", metadata_path)


if __name__ == "__main__":
    main()
