#!/usr/bin/env python3
#########################################################################
# Copyright (c) 2025-~ Hasan Al Reza && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Hasan Al Reza < hasan.al.reza.bd@gmail.com >
# File Name: run_genomic_regions_annotation.py
# Description:
# Performs nearby-gene annotation, genomic feature assignment, reporting, visualization, and GSEA-ready export generation.
#########################################################################
"""
Run St. Jude/CAB-style genomic region annotation for .bed, .bed.gz, and .vout inputs.

For each .bed, .bed.gz, or .vout input file in an input directory, this wrapper runs:
  1. voom2anno.sh
  2. annotateGenomicFeatures.py

After all BED files are processed, it optionally runs:
  3. OrganizeAnnotationResults.py

The wrapper can also create/use a conda environment from a YAML file and
execute all tasks with that environment's Python and PATH.

Example:
  python run_genomic_regions_annotation.py \
    --input-dir . \
    --out-dir annotation_run \
    --conda-env epi_anno_env \
    --create-conda-env \
    --genome hg38 \
    --run

  Results are written to annotation_run-YYYYMMDDTHHMMSSZ, where the suffix
  is a UTC run ID generated at execution time.

Project layout expected by default:
project/
├── run_genomic_regions_annotation.py
│
├── scripts/
│   ├── voom2anno.sh
│   ├── annotateGenomicFeatures.py
│   ├── OrganizeAnnotationResults.py
│   │
│   ├── wcn.sh
│   ├── tabit.sh
│   ├── tabnNA.sh
│   ├── region2bed.sh
│   ├── bed2region.sh
│   ├── winandgroup.sh
│   └── gene2nomicro.awk
│
└── annotations/
    ├── gencode.v31.hg38.gtf.bed.sorted.tss
    ├── gencode.v19.hg19.bed.tss
    ├── gencode.vM22.mm10.gtf.bed.tss
    ├── gencode.vM17.mm9.gtf.bed.tss
    ├── sacCer3.shiftedBy125.flank375.bed.tss
    │
    ├── hg38/
    ├── hg19/
    ├── mm10/
    ├── mm9/
    └── sacCer3/
└── environment/
    └── epi_anno_env.yml
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_CONDA_ENV = "epi_anno_env"
WRAPPER_DIR = Path(__file__).resolve().parent
DEFAULT_BASE_DIR = WRAPPER_DIR
DEFAULT_SCRIPTS_DIR = WRAPPER_DIR / "scripts"
DEFAULT_ANNOTATIONS_DIR = WRAPPER_DIR / "annotations"
DEFAULT_ENVIRONMENT_DIR = WRAPPER_DIR / "environment"
DEFAULT_CONDA_YAML = DEFAULT_ENVIRONMENT_DIR / "epi_anno_env.yml"
RUN_ID_TIME_FORMAT = "%Y%m%dT%H%M%SZ"

TSS_ANNOTATION_BY_GENOME = {
    "hg38": "gencode.v31.hg38.gtf.bed.sorted.tss",
    "hg19": "gencode.v19.hg19.bed.tss",
    "mm10": "gencode.vM22.mm10.gtf.bed.tss",
    "mm9": "gencode.vM17.mm9.gtf.bed.tss",
    "sacCer3": "sacCer3.shiftedBy125.flank375.bed.tss",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run voom2anno.sh, annotateGenomicFeatures.py, and OrganizeAnnotationResults.py on BED, BED.GZ, and/or VOUT files.")
    parser.add_argument("--input-dir", type=Path, default=Path("."), help="Directory containing .bed, .bed.gz, and/or .vout files. Default: current directory.")
    parser.add_argument("--out-dir", type=Path, default=Path("annotation_output"), help="Output/work directory root. A UTC timestamp suffix is appended to the directory name for each run. Default root: annotation_output.")
    parser.add_argument("--bed-glob", default="*.bed,*.bed.gz", help="Comma-separated glob patterns for BED files. Default: *.bed,*.bed.gz")
    parser.add_argument("--vout-glob", default="*.vout", help="Glob pattern for VOUT/peak-test files. Default: *.vout")
    parser.add_argument("--copy-inputs", action="store_true", help="Copy input files into --out-dir instead of symlinking them.")
    parser.add_argument("--bed-has-header", action="store_true", help="Treat BED inputs as having one header line. By default, BED and BED.GZ inputs are treated as header-free.")
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR, help="Base project directory.")
    parser.add_argument("--scripts-dir", type=Path, default=DEFAULT_SCRIPTS_DIR, help="Directory containing voom2anno.sh and helper scripts.")
    parser.add_argument("--annotations-dir", type=Path, default=DEFAULT_ANNOTATIONS_DIR, help="Directory containing TSS files and genome annotation folders.")
    parser.add_argument(
        "--genome",
        required=True,
        choices=sorted(TSS_ANNOTATION_BY_GENOME),
        help="Required. Genome build used to choose the TSS annotation and passed to annotateGenomicFeatures.py. No default is applied.",
    )
    parser.add_argument("--feature-anno-dir", type=Path, help="Directory containing genomic feature BED annotations like: hg19/2kb.promoter.up.bed, hg38/2kb.promoter.up.bed, etc. Passed to annotateGenomicFeatures.py using -a.")
    parser.add_argument("--distance1", default="2000", help="Inner/proximal gene-window distance passed to voom2anno.sh. Default: 2000.")
    parser.add_argument("--distance2", default="50000", help="Outer/distal gene-window distance passed to voom2anno.sh. Default: 50000.")
    parser.add_argument("--python-bin", type=Path, help="Python interpreter used for Python annotation scripts. Overrides conda resolution when provided.")
    parser.add_argument("--conda-yaml", type=Path, default=DEFAULT_CONDA_YAML, help="Conda environment YAML file. Used with --create-conda-env, or recorded/validated when an env already exists.")
    parser.add_argument("--conda-env", default=DEFAULT_CONDA_ENV, help=f"Conda environment name to use/create. Default: {DEFAULT_CONDA_ENV}.")
    parser.add_argument("--conda-prefix", type=Path, help="Explicit conda environment prefix to use instead of looking up --conda-env.")
    parser.add_argument("--create-conda-env", action="store_true", help="Create the conda environment from --conda-yaml if it is missing.")
    parser.add_argument("--use-current-python", action="store_true", help="Use the current Python interpreter and current PATH instead of a conda environment.")
    parser.add_argument("--skip-existing-anno", action="store_true", help="Skip voom2anno.sh if INPUT.anno already exists in --out-dir.")
    parser.add_argument("--skip-organize", action="store_true", help="Do not run OrganizeAnnotationResults.py after per-BED annotation.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands and validate inputs without running them.")
    parser.add_argument("--run", action="store_true", help="Actually run the pipeline. Without --run, this behaves like a dry run.")
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    raise SystemExit(1)


def info(message: str) -> None:
    print(f"[INFO] {message}", flush=True)


def resolve_path(path: Path) -> Path:
    return path.expanduser().resolve()


def validate_file(path: Path, label: str) -> Path:
    path = resolve_path(path)
    if not path.exists():
        fail(f"{label} does not exist: {path}")
    if not path.is_file():
        fail(f"{label} is not a file: {path}")
    return path


def validate_dir(path: Path, label: str) -> Path:
    path = resolve_path(path)
    if not path.exists():
        fail(f"{label} does not exist: {path}")
    if not path.is_dir():
        fail(f"{label} is not a directory: {path}")
    return path


def utc_run_id() -> str:
    """Return a UTC timestamp run ID for output directory suffixes.

    Returns:
        str: Timestamp in YYYYMMDDTHHMMSSZ format.
    """

    return datetime.now(timezone.utc).strftime(RUN_ID_TIME_FORMAT)


def append_timestamp_suffix(path: Path, run_id: str) -> Path:
    """Append a timestamp suffix to the final component of an output path.

    Args:
        path (Path): Requested output root path.
        run_id (str): UTC timestamp run ID.

    Returns:
        Path: Output path with the run ID appended to the directory name.
    """

    expanded_path = path.expanduser()
    if expanded_path.name in {"", ".", ".."}:
        fail(
            "Output directory must include a directory name that can receive "
            f"a timestamp suffix: {path}"
        )
    return expanded_path.with_name(f"{expanded_path.name}-{run_id}")


def ensure_out_dir(path: Path, run_id: str) -> Path:
    """Create and return a timestamp-suffixed output directory.

    Args:
        path (Path): Requested output root path.
        run_id (str): UTC timestamp run ID.

    Returns:
        Path: Resolved timestamp-suffixed output directory.

    Raises:
        SystemExit: If the timestamped output directory already exists.
    """

    path = resolve_path(append_timestamp_suffix(path, run_id))
    if path.exists():
        fail(
            "Timestamped output directory already exists; rerun after one "
            f"second or choose a different --out-dir: {path}"
        )
    path.mkdir(parents=True)
    return path


def resolve_layout(scripts_dir: Path, annotations_dir: Path,) -> tuple[Path, Path]:
    scripts_dir = validate_dir(scripts_dir, "Scripts directory",)
    annotations_dir = validate_dir(annotations_dir, "Annotations directory",)
    return scripts_dir, annotations_dir


def resolve_scripts(scripts_dir: Path) -> tuple[Path, Path, Path]:
    scripts_dir = validate_dir(scripts_dir, "Script directory")
    voom2anno = validate_file(scripts_dir / "voom2anno.sh", "voom2anno.sh")
    annotate_script = validate_file(scripts_dir / "annotateGenomicFeatures.py", "annotateGenomicFeatures.py")
    organize_script = validate_file(scripts_dir / "OrganizeAnnotationResults.py", "OrganizeAnnotationResults.py")
    return voom2anno, annotate_script, organize_script


def resolve_tss_annotation(genome: str, anno_report_dir: Path) -> Path:
    anno_report_dir = validate_dir(anno_report_dir, "Annotation-report directory")
    if genome not in TSS_ANNOTATION_BY_GENOME:
        supported = ", ".join(sorted(TSS_ANNOTATION_BY_GENOME))
        fail(f"No built-in TSS annotation mapping for genome {genome!r}. Supported genomes: {supported}")
    return validate_file(anno_report_dir / TSS_ANNOTATION_BY_GENOME[genome], f"TSS annotation for {genome}")


def resolve_feature_annotation_dir(
    feature_anno_dir: Path | None,
    annotations_dir: Path,
) -> Path:

    if feature_anno_dir is not None:
        return validate_dir(
            feature_anno_dir,
            "Feature annotation directory",
        )

    return validate_dir(
        annotations_dir,
        "Annotations directory",
    )


def determine_input_kind(input_file: Path) -> str | None:
    """Return the voom2anno input kind based on file extension.

    .bed and .bed.gz files are processed with a voom2anno.sh BED mode.
    .vout files are processed with voom2anno.sh mode "pktesth1".
    """
    name = input_file.name
    if name.endswith(".bed") or name.endswith(".bed.gz"):
        return "bed"
    if name.endswith(".vout"):
        return "vout"
    return None


def voom_mode_for_kind(input_kind: str, bed_has_header: bool = False) -> str:
    """Return the voom2anno mode for the staged input kind.

    Args:
        input_kind (str): Either `bed` or `vout`.
        bed_has_header (bool): Whether BED inputs include one header line.

    Returns:
        str: voom2anno.sh mode string.
    """
    if input_kind == "bed":
        return "bed6h1" if bed_has_header else "bed6i0"
    if input_kind == "vout":
        return "pktesth1"
    fail(f"Unsupported input kind: {input_kind}")


def split_glob_patterns(patterns: str) -> list[str]:
    """Split a comma-separated glob pattern list.

    Args:
        patterns (str): Comma-separated glob patterns.

    Returns:
        list[str]: Non-empty glob patterns.
    """
    return [pattern.strip() for pattern in patterns.split(",") if pattern.strip()]


def find_input_files(input_dir: Path, bed_glob: str, vout_glob: str) -> list[tuple[Path, str]]:
    inputs: list[Path] = []
    for pattern in split_glob_patterns(bed_glob):
        inputs.extend(p.resolve() for p in sorted(input_dir.glob(pattern)) if p.is_file())
    for pattern in split_glob_patterns(vout_glob):
        inputs.extend(p.resolve() for p in sorted(input_dir.glob(pattern)) if p.is_file())

    # Avoid processing generated annotation files or duplicate matches.
    seen: set[Path] = set()
    unique_inputs: list[tuple[Path, str]] = []
    for path in inputs:
        if path.name.startswith("."):
            info(f"Skipping hidden file: {path.name}")
            continue
        if path in seen or path.name.endswith(".anno"):
            continue
        kind = determine_input_kind(path)
        if kind is None:
            info(f"Skipping unsupported file: {path.name}")
            continue
        seen.add(path)
        unique_inputs.append((path, kind))

    if not unique_inputs:
        fail(f"No .bed, .bed.gz, or .vout files matched {bed_glob!r} or {vout_glob!r} in {input_dir}")

    return unique_inputs


def staged_input_name(source: Path) -> str:
    """Return the filename used inside the output/work directory.

    Args:
        source (Path): Source input file path.

    Returns:
        str: Staged filename.
    """
    if source.name.endswith(".bed.gz"):
        return source.name[:-3]
    return source.name


def parse_env_list_output(raw_output: str, env_name: str) -> Path | None:
    for line in raw_output.splitlines():
        line = line.strip()
        if not line or line.startswith("Name") or line.startswith("-"):
            continue
        tokens = line.split()
        path_token = next((token for token in reversed(tokens) if token.startswith("/")), None)
        if path_token is None:
            continue
        prefix = Path(path_token)
        if prefix.name == env_name or (tokens and tokens[0] == env_name):
            return prefix
    return None


def find_conda_env_prefix(env_name: str) -> Path | None:
    commands: list[list[str]] = []
    if shutil.which("mamba"):
        commands.append(["mamba", "env", "list"])
    if shutil.which("conda"):
        commands.append(["conda", "env", "list"])

    for cmd in commands:
        completed = subprocess.run(cmd, capture_output=True, text=True)
        combined = f"{completed.stdout}\n{completed.stderr}"
        prefix = parse_env_list_output(combined, env_name)
        if prefix is not None and prefix.exists():
            return prefix
    return None


def create_conda_env(conda_yaml: Path, env_name: str, dry_run: bool) -> None:
    if shutil.which("mamba"):
        cmd = ["mamba", "env", "create", "-n", env_name, "-f", str(conda_yaml)]
    elif shutil.which("conda"):
        cmd = ["conda", "env", "create", "-n", env_name, "-f", str(conda_yaml)]
    else:
        fail("Neither mamba nor conda is available to create the environment")

    info("Command: " + " ".join(cmd))
    if dry_run:
        return
    completed = subprocess.run(cmd)
    if completed.returncode != 0:
        fail(f"Conda environment creation failed with exit code {completed.returncode}")


def resolve_runtime(args: argparse.Namespace, dry_run: bool) -> tuple[str, dict[str, str]]:
    env = os.environ.copy()

    if args.use_current_python:
        python_bin = str(Path(sys.executable).resolve())
        info(f"Using current Python: {python_bin}")
        return python_bin, env

    if args.python_bin is not None:
        python_bin = validate_file(args.python_bin, "Python interpreter")
        info(f"Using explicitly provided Python: {python_bin}")
        return str(python_bin), env

    conda_yaml = validate_file(args.conda_yaml, "Conda YAML") if args.conda_yaml else None

    if args.conda_prefix:
        prefix = resolve_path(args.conda_prefix)
        if not prefix.exists():
            fail(f"Conda prefix does not exist: {prefix}")
    else:
        prefix = find_conda_env_prefix(args.conda_env)
        if prefix is None and args.create_conda_env:
            create_conda_env(conda_yaml, args.conda_env, dry_run=dry_run)
            if dry_run:
                prefix = Path(f"<conda-env:{args.conda_env}>")
            else:
                prefix = find_conda_env_prefix(args.conda_env)

    if prefix is None:
        fail(
            f"Conda environment '{args.conda_env}' was not found. "
            "Use --create-conda-env --conda-yaml ENV.yml, provide --conda-prefix, or pass --use-current-python."
        )

    if str(prefix).startswith("<conda-env:"):
        python_bin = f"{prefix}/bin/python"
        return python_bin, env

    python_path = prefix / "bin" / "python"
    if not python_path.exists():
        fail(f"Expected Python interpreter not found in conda environment: {python_path}")

    env["PATH"] = f"{prefix / 'bin'}:{env.get('PATH', '')}"
    env["CONDA_PREFIX"] = str(prefix)
    info(f"Using conda environment: {prefix}")
    return str(python_path), env


def ensure_runtime_tools(env: dict[str, str]) -> None:
    search_path = env.get("PATH", os.environ.get("PATH", ""))
    missing = [tool for tool in ["bash"] if shutil.which(tool, path=search_path) is None]
    if missing:
        fail("Missing required runtime tools: " + ", ".join(missing))


def build_runtime_env(scripts_dir: Path, base_env: dict[str, str]) -> dict[str, str]:
    """
    Add CAB helper script locations to PATH so voom2anno.sh can find:
      wcn.sh
      tabit.sh
      tabnNA.sh
      region2bed.sh
      bed2region.sh
      winandgroup.sh
      gene2nomicro.awk
    """
    env = base_env.copy()

    helper_dirs = [
        scripts_dir,
    ]

    existing_dirs = [str(p) for p in helper_dirs if p.exists()]

    env["PATH"] = os.pathsep.join(
        existing_dirs + [env.get("PATH", "")]
    )

    return env


def validate_helper_scripts(env: dict[str, str]) -> None:
    helpers = [
        "wcn.sh",
        "tabit.sh",
        "tabnNA.sh",
        "region2bed.sh",
        "bed2region.sh",
        "winandgroup.sh",
        "gene2nomicro.awk",
    ]

    missing = []

    for helper in helpers:
        if shutil.which(helper, path=env["PATH"]) is None:
            missing.append(helper)

    if missing:
        fail(
            "Missing CAB helper scripts:\n  "
            + "\n  ".join(missing)
            + "\n\nCheck that these scripts are available somewhere under the repository "
              "or add their location to PATH."
        )


def stage_input_files(input_files: list[tuple[Path, str]], out_dir: Path, copy_inputs: bool, dry_run: bool) -> list[tuple[Path, str]]:
    staged: list[tuple[Path, str]] = []
    staged_targets: set[Path] = set()
    for source, kind in input_files:
        target = out_dir / staged_input_name(source)
        if target in staged_targets:
            fail(f"Multiple inputs would stage to the same output filename: {target.name}")
        staged_targets.add(target)

        if source.name.endswith(".bed.gz"):
            if target.exists():
                info(f"Decompressed BED already staged: {target.name}")
            else:
                info(f"Decompress: {source} -> {target}")
                if not dry_run:
                    with gzip.open(source, "rb") as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
            staged.append((target, kind))
            continue

        if source == target:
            staged.append((target, kind))
            continue
        if target.exists() or target.is_symlink():
            info(f"Input already staged: {target.name}")
        else:
            action = "Copy" if copy_inputs else "Symlink"
            info(f"{action}: {source} -> {target}")
            if not dry_run:
                if copy_inputs:
                    shutil.copy2(source, target)
                else:
                    target.symlink_to(source)
        staged.append((target, kind))
    return staged


def run_command(cmd: list[str], cwd: Path, dry_run: bool, env: dict[str, str]) -> None:
    info("Command: " + " ".join(cmd))
    if dry_run:
        return

    completed = subprocess.run(cmd, cwd=cwd, env=env)
    if completed.returncode != 0:
        fail(f"Command failed with exit code {completed.returncode}: {' '.join(cmd)}")


def run_annotation_for_input(
    input_file: Path,
    input_kind: str,
    args: argparse.Namespace,
    voom2anno: Path,
    annotate_script: Path,
    tss_annotation: Path,
    feature_annotation_dir: Path,
    python_bin: str,
    runtime_env: dict[str, str],
    dry_run: bool,
) -> None:
    anno_file = input_file.with_name(input_file.name + ".anno")
    voom_mode = voom_mode_for_kind(input_kind, bed_has_header=args.bed_has_header)

    if args.skip_existing_anno and anno_file.exists():
        info(f"Skipping voom2anno.sh because annotation already exists: {anno_file.name}")
    else:
        voom_cmd = [
            "bash",
            str(voom2anno),
            voom_mode,
            input_file.name,
            str(tss_annotation),
            args.distance1,
            args.distance2,
        ]
        run_command(voom_cmd, cwd=input_file.parent, dry_run=dry_run, env=runtime_env)

    annotate_cmd = [python_bin, str(annotate_script), "-i", anno_file.name, "-g", args.genome, "-a", str(feature_annotation_dir),]
    run_command(annotate_cmd, cwd=input_file.parent, dry_run=dry_run, env=runtime_env)
    info(f"{input_file.name} FIN ({input_kind} input, voom2anno mode: {voom_mode})")


def main() -> None:
    args = parse_args()
    dry_run = args.dry_run or not args.run
    run_id = utc_run_id()

    input_dir = validate_dir(args.input_dir, "Input directory")
    out_dir = ensure_out_dir(args.out_dir, run_id)
    scripts_dir, annotations_dir = resolve_layout(args.scripts_dir, args.annotations_dir,)

    voom2anno, annotate_script, organize_script = resolve_scripts(
        scripts_dir
    )

    tss_annotation = resolve_tss_annotation(
        args.genome,
        annotations_dir,
    )

    feature_annotation_dir = resolve_feature_annotation_dir(
        args.feature_anno_dir,
        annotations_dir,
    )

    python_bin, runtime_env = resolve_runtime(args, dry_run=dry_run)

    runtime_env = build_runtime_env(
    scripts_dir=scripts_dir,
    base_env=runtime_env,
    )

    ensure_runtime_tools(runtime_env)
    validate_helper_scripts(runtime_env)

    input_files = find_input_files(input_dir, args.bed_glob, args.vout_glob)
    n_bed = sum(1 for _, kind in input_files if kind == "bed")
    n_vout = sum(1 for _, kind in input_files if kind == "vout")
    info(f"Found {len(input_files)} input file(s): {n_bed} BED, {n_vout} VOUT.")
    info(f"Run ID: {run_id}")
    info(f"Requested output directory root: {resolve_path(args.out_dir)}")
    info(f"Output/work directory: {out_dir}")
    info(f"Scripts directory: {scripts_dir}")
    info(f"Annotations directory: {annotations_dir}")
    info(f"PATH used for execution:\n{runtime_env['PATH']}")

    for helper in [
        "wcn.sh",
        "tabit.sh",
        "tabnNA.sh",
        "region2bed.sh",
        "bed2region.sh",
        "winandgroup.sh",
    ]:
        info(
            f"{helper}: "
            f"{shutil.which(helper, path=runtime_env['PATH'])}"
        )

    info(f"TSS annotation: {tss_annotation}")
    info(f"Feature annotation directory: {feature_annotation_dir}")

    if dry_run:
        info("Dry-run mode: commands will be printed but not executed. Add --run to execute.")

    staged_inputs = stage_input_files(input_files, out_dir, copy_inputs=args.copy_inputs, dry_run=dry_run)

    for input_file, input_kind in staged_inputs:
        run_annotation_for_input(
            input_file=input_file,
            input_kind=input_kind,
            args=args,
            voom2anno=voom2anno,
            annotate_script=annotate_script,
            tss_annotation=tss_annotation,
            feature_annotation_dir=feature_annotation_dir,
            python_bin=python_bin,
            runtime_env=runtime_env,
            dry_run=dry_run,
        )

    if not args.skip_organize:
        organize_cmd = [python_bin, str(organize_script)]
        run_command(organize_cmd, cwd=out_dir, dry_run=dry_run, env=runtime_env)

    info("Pipeline finished successfully." if not dry_run else "Dry run complete.")
    info(f"Results are in: {out_dir}")


if __name__ == "__main__":
    main()
