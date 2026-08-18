#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2026-~ Hasan Al Reza && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Hasan Al Reza < hasan.al.reza.bd@gmail.com >
# File Name: run-tornado-plots.py
# Description:
# Orchestrates symlink staging and deepTools tornado-plot generation.
#########################################################################

"""Run tornado plots from BED regions and BigWig signal tracks.

This wrapper resolves user-provided filenames and input locations, stages
inputs as symlinks with scripts/link.sh, and runs scripts/plot.sh to execute
deepTools computeMatrix and plotHeatmap. It defaults to dry-run mode; pass
--run to create the run directory, symlinks, matrix, and heatmap outputs.
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


SKILL_NAME = "tornado-plots"
SKILL_VERSION = "0.2.9"
DEFAULT_CONDA_ENV = "tornado_env"
RUN_ID_TIME_FORMAT = "%Y%m%dT%H%M%SZ"
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
WRAPPER_DIR = Path(__file__).resolve().parent
ENVIRONMENT_DIR = WRAPPER_DIR / "environment"
DEFAULT_CONDA_YAML = ENVIRONMENT_DIR / "tornado_env.yml"
SCRIPTS_DIR = WRAPPER_DIR / "scripts"
LINK_SCRIPT = SCRIPTS_DIR / "link.sh"
PLOT_SCRIPT = SCRIPTS_DIR / "plot.sh"
LOGGER = logging.getLogger(SKILL_NAME)
PREFERRED_REGION_LABEL_ORDER = ("Up2FC", "Down2FC")


@dataclass(frozen=True)
class ResolvedInputs:
    """Resolved region and signal input paths.

    Attributes:
        regions (list[Path]): Existing BED region files.
        signals (list[Path]): Existing BigWig signal files.
    """

    regions: list[Path]
    signals: list[Path]


@dataclass(frozen=True)
class RunPlan:
    """Concrete run directory, commands, and expected outputs.

    Attributes:
        run_id (str): UTC run identifier in YYYYMMDDTHHMMSSZ format.
        run_dir (Path): Run-scoped output directory.
        inputs (ResolvedInputs): Ordered region and signal input paths.
        linked_inputs_dir (Path): Directory where input symlinks are staged.
        manifest_path (Path): Symlink manifest path.
        matrix_path (Path): Expected deepTools matrix path.
        plot_path (Path): Expected tornado-plot PDF path.
        link_command (list[str]): Command used to create symlinks.
        plot_command (list[str]): Command used to generate the plot.
    """

    run_id: str
    run_dir: Path
    inputs: ResolvedInputs
    linked_inputs_dir: Path
    manifest_path: Path
    matrix_path: Path
    plot_path: Path
    link_command: list[str]
    plot_command: list[str]


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv (Sequence[str] | None): Optional argument sequence. Uses
            sys.argv when None.

    Returns:
        argparse.Namespace: Parsed command-line values.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Stage BED/BigWig files and run deepTools computeMatrix plus "
            "plotHeatmap to create tornado plots."
        )
    )
    parser.add_argument("--inputDir", type=Path, help="Default directory containing input files.")
    parser.add_argument("--regionsDir", type=Path, help="Directory for relative region BED filenames.")
    parser.add_argument("--signalsDir", type=Path, help="Directory for relative BigWig filenames.")
    parser.add_argument(
        "--regions",
        nargs="+",
        required=True,
        help="BED region filenames or paths. Provide one or more values.",
    )
    parser.add_argument(
        "--signals",
        nargs="+",
        required=True,
        help="BigWig signal filenames or paths. Provide one or more values.",
    )
    parser.add_argument("--regionLabels", nargs="+", help="Labels for region BED files.")
    parser.add_argument("--sampleLabels", nargs="+", help="Labels for signal BigWig files.")
    parser.add_argument(
        "--outputRoot",
        type=Path,
        default=Path("agentResults"),
        help="Root directory for timestamped run output. Default: agentResults.",
    )
    parser.add_argument("--outputPrefix", required=True, help="Prefix for matrix and tornado plot files.")
    parser.add_argument("--runId", help="Optional UTC run ID in YYYYMMDDTHHMMSSZ format.")
    parser.add_argument("--run", action="store_true", help="Execute link.sh and plot.sh.")
    parser.add_argument(
        "--dryRun",
        action="store_true",
        help="Print planned commands without running. This is the default unless --run is set.",
    )
    parser.add_argument("--forceLinks", action="store_true", help="Replace conflicting staged links.")
    parser.add_argument("--executor", choices=["local", "bsub"], default="local", help="Execution backend.")
    parser.add_argument(
        "--condaEnv",
        default=DEFAULT_CONDA_ENV,
        help=f"Conda environment name. Default: {DEFAULT_CONDA_ENV}"
    )
    parser.add_argument(
        "--condaYaml",
        type=Path,
        default=DEFAULT_CONDA_YAML,
        help="Conda environment YAML."
    )
    parser.add_argument(
        "--condaPrefix",
        type=Path,
        help="Use an existing conda environment prefix."
    )
    parser.add_argument(
        "--createCondaEnv",
        action="store_true",
        help="Create the conda environment if it is missing."
    )
    parser.add_argument(
        "--condaExecutable",
        default="conda",
        help="Conda executable used by scripts/plot.sh. Default: conda.",
    )
    parser.add_argument("--noConda", action="store_true", help="Run deepTools from the current PATH instead of conda.")
    parser.add_argument("--referencePoint", default="center", help="deepTools reference point. Default: center.")
    parser.add_argument("--before", type=int, default=2000, help="Bases before reference point. Default: 2000.")
    parser.add_argument("--after", type=int, default=2000, help="Bases after reference point. Default: 2000.")
    parser.add_argument("--binSize", type=int, default=25, help="Bin size in bases. Default: 25.")
    parser.add_argument(
        "--noMissingDataAsZero",
        action="store_true",
        help="Do not pass --missingDataAsZero to computeMatrix.",
    )
    parser.add_argument("--sortRegions", default="descend", help="plotHeatmap sortRegions. Default: descend.")
    parser.add_argument("--sortUsing", default="mean", help="plotHeatmap sortUsing. Default: mean.")
    parser.add_argument("--sortUsingSamples", default="1", help="plotHeatmap sortUsingSamples. Default: 1.")
    parser.add_argument("--labelRotation", default="45", help="plotHeatmap labelRotation. Default: 45.")
    parser.add_argument("--heatmapHeight", default="15", help="plotHeatmap heatmapHeight. Default: 15.")
    parser.add_argument("--heatmapWidth", default="4", help="plotHeatmap heatmapWidth. Default: 4.")
    parser.add_argument("--colorMap", help="Optional plotHeatmap colorMap.")
    parser.add_argument("--zMin", help="Optional plotHeatmap zMin.")
    parser.add_argument("--zMax", help="Optional plotHeatmap zMax.")
    parser.add_argument("--proc", type=int, default=8, help="LSF core count for --executor bsub. Default: 8.")
    parser.add_argument("--mem", type=int, default=128000, help="LSF total memory in MB. Default: 128000.")
    parser.add_argument("--queue", default="cab_auto", help="LSF queue for --executor bsub. Default: cab_auto.")
    parser.add_argument("--project", help="Optional LSF project for bsub -P.")
    parser.add_argument("--jobName", help="Optional LSF job name. Default: outputPrefix.")
    return parser.parse_args(argv)


def configure_logging() -> None:
    """Configure command-line logging."""

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)


def fail(message: str) -> None:
    """Raise a command-line usage error.

    Args:
        message (str): Error message to show to the user.

    Raises:
        SystemExit: Always exits with code 2.
    """

    raise SystemExit(f"run-tornado-plots.py error: {message}")


def find_conda_env_prefix(env_name: str) -> Path | None:
    commands = []

    if shutil.which("mamba"):
        commands.append(["mamba", "env", "list"])

    if shutil.which("conda"):
        commands.append(["conda", "env", "list"])

    for cmd in commands:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        for line in completed.stdout.splitlines():
            tokens = line.split()

            if len(tokens) < 2:
                continue

            if tokens[0] == env_name:
                return Path(tokens[-1])

    return None


def create_conda_env(
    yaml_file: Path,
    env_name: str,
) -> None:

    yaml_file = yaml_file.expanduser().resolve()

    if not yaml_file.exists():
        fail(f"Missing conda YAML: {yaml_file}")

    if shutil.which("mamba"):
        cmd = [
            "mamba",
            "env",
            "create",
            "-n",
            env_name,
            "-f",
            str(yaml_file),
        ]
    else:
        cmd = [
            "conda",
            "env",
            "create",
            "-n",
            env_name,
            "-f",
            str(yaml_file),
        ]

    LOGGER.info("Creating conda environment...")

    subprocess.run(cmd, check=True)


def resolve_conda_runtime(args):

    if args.noConda:
        return

    if args.condaPrefix:

        prefix = args.condaPrefix.expanduser().resolve()

    else:

        prefix = find_conda_env_prefix(args.condaEnv)

        if prefix is None:

            if args.createCondaEnv:

                create_conda_env(
                    args.condaYaml,
                    args.condaEnv,
                )

                prefix = find_conda_env_prefix(
                    args.condaEnv
                )

            if prefix is None:
                fail(
                    f"Conda environment '{args.condaEnv}' "
                    "could not be found."
                )

    os.environ["CONDA_PREFIX"] = str(prefix)

    os.environ["PATH"] = (
        str(prefix / "bin")
        + os.pathsep
        + os.environ["PATH"]
    )

    return prefix


def resolve_optional_dir(path_value: Path | None, role: str) -> Path | None:
    """Resolve an optional directory path.

    Args:
        path_value (Path | None): Directory path or None.
        role (str): Human-readable role for error messages.

    Returns:
        Path | None: Resolved existing directory or None.
    """

    if path_value is None:
        return None
    resolved = path_value.expanduser().resolve()
    if not resolved.is_dir():
        fail(f"Expected {role} directory but found: {resolved}")
    return resolved


def resolve_output_root(path_value: Path) -> Path:
    """Resolve the output root without requiring it to already exist.

    Args:
        path_value (Path): Output root path.

    Returns:
        Path: Absolute output root path.
    """

    return path_value.expanduser().resolve()


def resolve_input_file(file_value: str, base_dir: Path | None, role: str) -> Path:
    """Resolve and validate one input file.

    Args:
        file_value (str): Filename or path supplied by the user.
        base_dir (Path | None): Base directory for relative filenames.
        role (str): Input role for error messages.

    Returns:
        Path: Resolved existing file path.
    """

    candidate = Path(file_value).expanduser()
    if not candidate.is_absolute():
        if base_dir is None:
            fail(f"Relative {role} file requires --inputDir or a role-specific directory: {file_value}")
        candidate = base_dir / candidate
    resolved = candidate.resolve()
    if not resolved.is_file():
        fail(f"Expected {role} file but found: {resolved}")
    return resolved


def validate_input_suffix(path: Path, allowed_suffixes: tuple[str, ...], role: str) -> None:
    """Validate a genomic input filename suffix.

    Args:
        path (Path): Input path to validate.
        allowed_suffixes (tuple[str, ...]): Lowercase accepted suffixes.
        role (str): Input role for error messages.
    """

    lower_name = path.name.lower()
    if not lower_name.endswith(allowed_suffixes):
        suffix_list = ", ".join(allowed_suffixes)
        fail(f"Expected {role} suffix ({suffix_list}) but found: {path.name}")


def resolve_inputs(args: argparse.Namespace) -> ResolvedInputs:
    """Resolve all input BED and BigWig files.

    Args:
        args (argparse.Namespace): Parsed command-line values.

    Returns:
        ResolvedInputs: Existing region and signal file paths.
    """

    input_dir = resolve_optional_dir(args.inputDir, "--inputDir")
    regions_dir = resolve_optional_dir(args.regionsDir, "--regionsDir") or input_dir
    signals_dir = resolve_optional_dir(args.signalsDir, "--signalsDir") or input_dir

    regions = [resolve_input_file(value, regions_dir, "region BED") for value in args.regions]
    signals = [resolve_input_file(value, signals_dir, "signal BigWig") for value in args.signals]
    for region in regions:
        validate_input_suffix(region, (".bed",), "region BED")
    for signal in signals:
        validate_input_suffix(signal, (".bw", ".bigwig"), "signal BigWig")
    validate_unique_basenames(regions + signals)
    return ResolvedInputs(regions=regions, signals=signals)


def validate_unique_basenames(paths: list[Path]) -> None:
    """Fail when different inputs share the same basename.

    Args:
        paths (list[Path]): Input paths to check.
    """

    seen: dict[str, Path] = {}
    for path in paths:
        previous = seen.get(path.name)
        if previous is not None and previous != path:
            fail(f"Input basenames must be unique for symlink staging: {previous} and {path}")
        seen[path.name] = path


def validate_positive_integer(value: int, name: str) -> None:
    """Validate an integer option is greater than zero.

    Args:
        value (int): Value to validate.
        name (str): Option name for error messages.
    """

    if value <= 0:
        fail(f"{name} must be greater than zero: {value}")


def validate_labels(labels: list[str] | None, expected_count: int, role: str) -> list[str] | None:
    """Validate label count when labels are provided.

    Args:
        labels (list[str] | None): Labels supplied by the user.
        expected_count (int): Number of input files.
        role (str): Label role for error messages.

    Returns:
        list[str] | None: Original labels when provided.
    """

    if labels is None:
        return None
    if len(labels) != expected_count:
        fail(f"{role} label count ({len(labels)}) must match input count ({expected_count})")
    return labels


def derive_region_label(path: Path) -> str:
    """Derive a default BED region label from the filename.

    Args:
        path (Path): Region BED input path.

    Returns:
        str: Region label, preferring the `Up2FC` / `Down2FC` token when
            present in a name such as `Empty.Up2FC.Region.bed`.
    """

    name = path.name
    lower_name = name.lower()
    if lower_name.endswith(".bed"):
        base = name[:-4]
    else:
        base = path.stem

    region_match = re.search(r"\.(Up2FC|Down2FC)(?:\.Region)?$", base, flags=re.IGNORECASE)
    if region_match is not None:
        return region_match.group(1)
    return base


def derive_signal_label(path: Path) -> str:
    """Derive a default BigWig sample label from the filename.

    Args:
        path (Path): Signal BigWig input path.

    Returns:
        str: Sample label with technical suffixes like `.singleRep` removed.
    """

    name = path.name
    lower_name = name.lower()
    for suffix in (".bigwig", ".bw"):
        if lower_name.endswith(suffix):
            base = name[: -len(suffix)]
            break
    else:
        base = path.stem

    if base.lower().endswith(".singlerep"):
        return base[: -len(".singleRep")]
    return base


def derive_label(path: Path, role: str) -> str:
    """Derive a readable label from a BED or BigWig filename.

    Args:
        path (Path): Input path.
        role (str): Input role, either `region` or `signal`.

    Returns:
        str: Default label derived from the input filename.
    """

    if role == "region":
        return derive_region_label(path)
    if role == "signal":
        return derive_signal_label(path)
    fail(f"Unknown label role: {role}")


def normalize_label_key(label: str) -> str:
    """Normalize a label for ordering comparisons.

    Args:
        label (str): Label text.

    Returns:
        str: Lowercase alphanumeric-only comparison key.
    """

    return re.sub(r"[^a-z0-9]+", "", label.lower())


def preferred_region_rank(label: str) -> int | None:
    """Return the preferred ordering rank for known two-region labels.

    Args:
        label (str): Derived region label.

    Returns:
        int | None: Preferred rank or None when the label is not recognized.
    """

    normalized = normalize_label_key(label)
    for index, preferred_label in enumerate(PREFERRED_REGION_LABEL_ORDER):
        if normalized.startswith(normalize_label_key(preferred_label)):
            return index
    return None


def order_default_region_inputs(paths: list[Path]) -> tuple[list[Path], list[str]]:
    """Order default region inputs so Up2FC precedes Down2FC when applicable.

    Args:
        paths (list[Path]): Region BED input paths in user-supplied order.

    Returns:
        tuple[list[Path], list[str]]: Ordered region paths and derived labels.
    """

    labels = [derive_label(path, "region") for path in paths]
    if len(paths) != 2:
        return paths, labels

    ranks = [preferred_region_rank(label) for label in labels]
    if any(rank is None for rank in ranks):
        return paths, labels

    ordered = sorted(zip(paths, labels, ranks), key=lambda item: item[2])
    ordered_paths = [path for path, _, _ in ordered]
    ordered_labels = [label for _, label, _ in ordered]
    return ordered_paths, ordered_labels


def choose_labels(user_labels: list[str] | None, paths: list[Path], role: str) -> list[str]:
    """Use user labels or derive labels from input filenames.

    Args:
        user_labels (list[str] | None): Optional labels from the CLI.
        paths (list[Path]): Input paths to label.
        role (str): Input role, either `region` or `signal`.

    Returns:
        list[str]: Labels matching the input path order.
    """

    if user_labels is not None:
        return user_labels
    return [derive_label(path, role) for path in paths]


def create_run_id(user_run_id: str | None) -> str:
    """Create or validate a UTC run ID.

    Args:
        user_run_id (str | None): Optional user-provided run ID.

    Returns:
        str: Run ID in YYYYMMDDTHHMMSSZ format.
    """

    if user_run_id is not None:
        if RUN_ID_PATTERN.match(user_run_id) is None:
            fail(f"--runId must match YYYYMMDDTHHMMSSZ: {user_run_id}")
        return user_run_id
    return datetime.now(timezone.utc).strftime(RUN_ID_TIME_FORMAT)


def build_link_command(plan_dir: Path, manifest_path: Path, inputs: ResolvedInputs, force: bool) -> list[str]:
    """Build the symlink staging command.

    Args:
        plan_dir (Path): Linked input directory.
        manifest_path (Path): Link manifest path.
        inputs (ResolvedInputs): Resolved input files.
        force (bool): Whether to replace conflicting staged paths.

    Returns:
        list[str]: Command vector for subprocess.run.
    """

    command = [
        "bash",
        str(LINK_SCRIPT),
        "--outputDir",
        str(plan_dir),
        "--manifest",
        str(manifest_path),
    ]
    if force:
        command.append("--force")
    for path in inputs.regions + inputs.signals:
        command.extend(["--file", str(path)])
    return command


def build_plot_command(
    args: argparse.Namespace,
    run_dir: Path,
    linked_inputs_dir: Path,
    inputs: ResolvedInputs,
    region_labels: list[str],
    sample_labels: list[str],
) -> tuple[list[str], Path, Path]:
    """Build the deepTools plotting command.

    Args:
        args (argparse.Namespace): Parsed command-line values.
        run_dir (Path): Run-scoped output directory.
        linked_inputs_dir (Path): Symlink staging directory.
        inputs (ResolvedInputs): Resolved input files.
        region_labels (list[str]): Labels for region BED files.
        sample_labels (list[str]): Labels for signal BigWig files.

    Returns:
        tuple[list[str], Path, Path]: Command vector, matrix path, and plot path.
    """

    matrix_path = run_dir / f"{args.outputPrefix}_matrix.gz"
    plot_path = run_dir / f"{args.outputPrefix}_tornado.pdf"
    command = [
        "bash",
        str(PLOT_SCRIPT),
        "--workDir",
        str(linked_inputs_dir),
        "--outputDir",
        str(run_dir),
        "--outputPrefix",
        args.outputPrefix,
        "--matrixFile",
        str(matrix_path),
        "--plotFile",
        str(plot_path),
        "--executor",
        args.executor,
        "--referencePoint",
        args.referencePoint,
        "--before",
        str(args.before),
        "--after",
        str(args.after),
        "--binSize",
        str(args.binSize),
        "--sortRegions",
        args.sortRegions,
        "--sortUsing",
        args.sortUsing,
        "--sortUsingSamples",
        args.sortUsingSamples,
        "--labelRotation",
        args.labelRotation,
        "--heatmapHeight",
        args.heatmapHeight,
        "--heatmapWidth",
        args.heatmapWidth,
    ]
    if args.noConda:
        command.append("--noConda")
    else:
        command.extend(["--condaEnv", args.condaEnv, "--condaExecutable", args.condaExecutable])
    if not args.run:
        command.append("--dryRun")
    if args.noMissingDataAsZero:
        command.append("--noMissingDataAsZero")
    for path in inputs.regions:
        command.extend(["--region", path.name])
    for path in inputs.signals:
        command.extend(["--signal", path.name])
    for label in region_labels:
        command.extend(["--regionLabel", label])
    for label in sample_labels:
        command.extend(["--sampleLabel", label])
    if args.colorMap:
        command.extend(["--colorMap", args.colorMap])
    if args.zMin:
        command.extend(["--zMin", args.zMin])
    if args.zMax:
        command.extend(["--zMax", args.zMax])
    if args.executor == "bsub":
        command.extend(["--proc", str(args.proc), "--mem", str(args.mem), "--queue", args.queue])
        if args.project:
            command.extend(["--project", args.project])
        if args.jobName:
            command.extend(["--jobName", args.jobName])
    return command, matrix_path, plot_path


def build_run_plan(args: argparse.Namespace, inputs: ResolvedInputs) -> RunPlan:
    """Build a complete run plan.

    Args:
        args (argparse.Namespace): Parsed command-line values.
        inputs (ResolvedInputs): Resolved input files.

    Returns:
        RunPlan: Run directories, commands, and expected output paths.
    """

    run_id = create_run_id(args.runId)
    output_root = resolve_output_root(args.outputRoot)
    run_dir = output_root / f"{SKILL_NAME}-{run_id}"
    linked_inputs_dir = run_dir / "linkedInputs"
    manifest_path = run_dir / "input-symlinks.tsv"
    region_labels_arg = validate_labels(args.regionLabels, len(inputs.regions), "Region")
    if region_labels_arg is None:
        ordered_regions, region_labels = order_default_region_inputs(inputs.regions)
    else:
        ordered_regions = inputs.regions
        region_labels = region_labels_arg
    ordered_inputs = ResolvedInputs(regions=ordered_regions, signals=inputs.signals)
    sample_labels = choose_labels(validate_labels(args.sampleLabels, len(inputs.signals), "Sample"), inputs.signals, "signal")
    link_command = build_link_command(linked_inputs_dir, manifest_path, ordered_inputs, args.forceLinks)
    plot_command, matrix_path, plot_path = build_plot_command(
        args=args,
        run_dir=run_dir,
        linked_inputs_dir=linked_inputs_dir,
        inputs=ordered_inputs,
        region_labels=region_labels,
        sample_labels=sample_labels,
    )
    return RunPlan(
        run_id=run_id,
        run_dir=run_dir,
        inputs=ordered_inputs,
        linked_inputs_dir=linked_inputs_dir,
        manifest_path=manifest_path,
        matrix_path=matrix_path,
        plot_path=plot_path,
        link_command=link_command,
        plot_command=plot_command,
    )


def format_command(command: Sequence[str]) -> str:
    """Format a command vector for shell-readable logs.

    Args:
        command (Sequence[str]): Command vector.

    Returns:
        str: Quoted command line.
    """

    return shlex.join(command)


def run_command(command: Sequence[str]) -> None:
    """Run a subprocess command and fail on non-zero exit.

    Args:
        command (Sequence[str]): Command vector to execute.

    Raises:
        subprocess.CalledProcessError: When the command exits non-zero.
    """

    LOGGER.info("Running: %s", format_command(command))
    subprocess.run(command, check=True)


def write_metadata(args: argparse.Namespace, inputs: ResolvedInputs, plan: RunPlan) -> Path:
    """Write run metadata for reproducibility.

    Args:
        args (argparse.Namespace): Parsed command-line values.
        inputs (ResolvedInputs): Resolved input files.
        plan (RunPlan): Executed run plan.

    Returns:
        Path: Metadata JSON path.
    """

    metadata = {
        "skillName": SKILL_NAME,
        "skillVersion": SKILL_VERSION,
        "runId": plan.run_id,
        "executionTimestampUtc": datetime.now(timezone.utc).isoformat(),
        "runDir": str(plan.run_dir),
        "linkedInputsDir": str(plan.linked_inputs_dir),
        "manifestPath": str(plan.manifest_path),
        "matrixPath": str(plan.matrix_path),
        "plotPath": str(plan.plot_path),
        "regions": [str(path) for path in plan.inputs.regions],
        "signals": [str(path) for path in inputs.signals],
        "parameters": {
            "outputPrefix": args.outputPrefix,
            "executor": args.executor,
            "condaEnv": None if args.noConda else args.condaEnv,
            "condaExecutable": None if args.noConda else args.condaExecutable,
            "referencePoint": args.referencePoint,
            "before": args.before,
            "after": args.after,
            "binSize": args.binSize,
            "missingDataAsZero": not args.noMissingDataAsZero,
            "sortRegions": args.sortRegions,
            "sortUsing": args.sortUsing,
            "sortUsingSamples": args.sortUsingSamples,
            "labelRotation": args.labelRotation,
            "heatmapHeight": args.heatmapHeight,
            "heatmapWidth": args.heatmapWidth,
            "colorMap": args.colorMap,
            "zMin": args.zMin,
            "zMax": args.zMax,
            "proc": args.proc,
            "mem": args.mem,
            "queue": args.queue,
            "project": args.project,
            "jobName": args.jobName,
        },
        "commands": {
            "link": plan.link_command,
            "plot": plan.plot_command,
        },
    }
    metadata_path = plan.run_dir / "tornado-plots-run-metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata_path


def validate_runtime_options(args: argparse.Namespace) -> None:
    """Validate numeric options and bundled script availability.

    Args:
        args (argparse.Namespace): Parsed command-line values.
    """

    if args.run and args.dryRun:
        fail("Use either --run or --dryRun, not both")
    if not args.noConda:
        if not args.condaEnv:
            fail("--condaEnv must not be empty unless --noConda is used")
        if not args.condaExecutable:
            fail("--condaExecutable must not be empty unless --noConda is used")
    validate_positive_integer(args.before, "--before")
    validate_positive_integer(args.after, "--after")
    validate_positive_integer(args.binSize, "--binSize")
    validate_positive_integer(args.proc, "--proc")
    validate_positive_integer(args.mem, "--mem")
    if not LINK_SCRIPT.is_file():
        fail(f"Missing helper script: {LINK_SCRIPT}")
    if not PLOT_SCRIPT.is_file():
        fail(f"Missing helper script: {PLOT_SCRIPT}")


def report_plan(plan: RunPlan, execute: bool) -> None:
    """Log the planned or executed commands.

    Args:
        plan (RunPlan): Run plan to report.
        execute (bool): Whether commands will be executed.
    """

    mode = "Execution" if execute else "Dry run"
    LOGGER.info("%s run ID: %s", mode, plan.run_id)
    LOGGER.info("Run directory: %s", plan.run_dir)
    LOGGER.info("Expected matrix: %s", plan.matrix_path)
    LOGGER.info("Expected plot: %s", plan.plot_path)
    LOGGER.info("Link command: %s", format_command(plan.link_command))
    LOGGER.info("Plot command: %s", format_command(plan.plot_command))
    if not execute:
        LOGGER.info("Dry run complete. Add --run to execute.")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tornado-plots wrapper.

    Args:
        argv (Sequence[str] | None): Optional argument sequence. Uses
            sys.argv when None.

    Returns:
        int: Process exit code.
    """

    configure_logging()
    args = parse_arguments(argv)
    validate_runtime_options(args)
    inputs = resolve_inputs(args)
    plan = build_run_plan(args, inputs)
    execute = bool(args.run)
    report_plan(plan, execute=execute)

    if not execute:
        return 0

    resolve_conda_runtime(args)
    if plan.run_dir.exists():
        fail(f"Run directory already exists: {plan.run_dir}")
    plan.run_dir.mkdir(parents=True)
    run_command(plan.link_command)
    run_command(plan.plot_command)
    metadata_path = write_metadata(args, inputs, plan)
    LOGGER.info("Metadata: %s", metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
