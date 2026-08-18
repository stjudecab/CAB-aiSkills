#!/usr/bin/env bash
#########################################################################
# Copyright (c) 2026-~ Hasan Al Reza && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Hasan Al Reza < hasan.al.reza.bd@gmail.com >
# File Name: plot.sh
# Description:
# Runs generalized deepTools computeMatrix and plotHeatmap tornado plots.
#########################################################################

set -euo pipefail

show_usage() {
    cat <<'USAGE'
Usage:
  plot.sh --workDir DIR --region BED --signal BIGWIG --outputPrefix NAME [options]

Run deepTools computeMatrix reference-point and plotHeatmap for tornado plots.
Repeat --region for multiple BED files and --signal for multiple BigWig files.

Required:
  --workDir DIR             Directory containing input files or symlinks.
  --region FILE FILE        BED files for -R. Alias: --regions.
  --signal FILE FILE        BigWig files for -S. Alias: --signals.
  --outputPrefix NAME       Prefix used for default matrix and plot names.

deepTools options:
  --referencePoint VALUE    reference-point mode anchor. Default: center.
  --before INT             Bases before the reference point. Default: 2000.
  --after INT              Bases after the reference point. Default: 2000.
  --binSize INT            Bin size in bases. Default: 25.
  --noMissingDataAsZero    Do not pass --missingDataAsZero to computeMatrix.
  --regionLabel LABEL      Region label for plotHeatmap.
  --sampleLabel LABEL      Sample label for plotHeatmap.
  --sortRegions VALUE      plotHeatmap sortRegions. Default: descend.
  --sortUsing VALUE        plotHeatmap sortUsing. Default: mean.
  --sortUsingSamples VALUE plotHeatmap sortUsingSamples. Default: 1.
  --labelRotation VALUE    plotHeatmap labelRotation. Default: 45.
  --heatmapHeight VALUE    plotHeatmap heatmapHeight. Default: 15.
  --heatmapWidth VALUE     plotHeatmap heatmapWidth. Default: 4.
  --colorMap VALUE         Optional plotHeatmap colorMap.
  --zMin VALUE             Optional plotHeatmap zMin.
  --zMax VALUE             Optional plotHeatmap zMax.

Outputs:
  --outputDir DIR          Output directory. Default: --workDir.
  --matrixFile FILE        Matrix output. Default: <outputDir>/<prefix>_matrix.gz.
  --plotFile FILE          Plot output. Default: <outputDir>/<prefix>_tornado.pdf.

Execution:
  --executor local|bsub    Execution mode. Default: local.
  --condaEnv NAME          Conda environment for deepTools. Default:
                           tornado_env.
  --condaExecutable PATH   Conda executable. Default: conda.
  --noConda                Run deepTools from the current PATH instead.
  --dryRun                 Validate inputs and print commands without executing.
  --proc INT               LSF core count for bsub. Default: 8.
  --mem INT                Total memory in MB for bsub. Default: 128000.
  --queue NAME             LSF queue for bsub. Default: cab_auto.
  --project NAME           Optional LSF project for bsub -P.
  --jobName NAME           LSF job name. Default: <outputPrefix>.
  --help                   Show this help message.

Example:
  bash scripts/plot.sh \
    --workDir work \
    --region Up2FC.bed Down2FC.bed \
    --signal empty.bw treated.bw \
    --regionLabel Up2FC Down2FC \
    --sampleLabel Empty Treated \
    --labelRotation 45 \
    --outputDir results --outputPrefix xpo1 --executor bsub
USAGE
}

fail() {
    printf 'plot.sh error: %s\n' "$1" >&2
    exit 2
}

normalize_existing_dir() {
    local dir_path="$1"
    [[ -d "$dir_path" ]] || fail "Expected directory but found: ${dir_path}"
    local resolved_dir
    resolved_dir="$(cd "$dir_path" && pwd -P)"
    printf '%s\n' "$resolved_dir"
}

normalize_output_path() {
    local base_dir="$1"
    local path_value="$2"
    case "$path_value" in
        /*) printf '%s\n' "$path_value" ;;
        *) printf '%s/%s\n' "$base_dir" "$path_value" ;;
    esac
}

validate_positive_integer() {
    local value="$1"
    local name="$2"
    [[ "$value" =~ ^[0-9]+$ ]] || fail "${name} must be a positive integer: ${value}"
    [[ "$value" -gt 0 ]] || fail "${name} must be greater than zero: ${value}"
}

validate_input_file() {
    local work_dir="$1"
    local file_value="$2"
    local candidate="$file_value"

    case "$file_value" in
        /*) candidate="$file_value" ;;
        *) candidate="${work_dir}/${file_value}" ;;
    esac

    [[ -f "$candidate" ]] || fail "Expected input file but found: ${candidate}"
}

append_optional_label_args() {
    local label_flag="$1"
    shift
    local labels=("$@")
    local label_value
    local wrapped_label
    local newline=$'\n'

    if [[ ${#labels[@]} -gt 0 ]]; then
        plot_cmd+=("$label_flag")
        for label_value in "${labels[@]}"; do
            # Wrap compound labels at underscores for readable heatmap ticks.
            wrapped_label="${label_value//_/_${newline}}"
            plot_cmd+=("$wrapped_label")
        done
    fi
}

print_command() {
    printf '%q ' "$@"
    printf '\n'
}

write_job_script() {
    local job_script="$1"
    local work_dir="$2"

    {
        printf '#!/usr/bin/env bash\n'
        printf 'set -euo pipefail\n\n'
        printf 'cd %q\n\n' "$work_dir"
        print_command "${compute_run_cmd[@]}"
        print_command "${plot_run_cmd[@]}"
    } > "$job_script"

    chmod 755 "$job_script"
}

main() {
    local work_dir=""
    local output_dir=""
    local output_prefix=""
    local matrix_file=""
    local plot_file=""
    local reference_point="center"
    local before="2000"
    local after="2000"
    local bin_size="25"
    local missing_data_as_zero=true
    local sort_regions="descend"
    local sort_using="mean"
    local sort_using_samples="1"
    local label_rotation="45"
    local heatmap_height="15"
    local heatmap_width="4"
    local color_map=""
    local z_min=""
    local z_max=""
    local executor="local"
    local conda_env="tornado_env"
    local conda_executable="conda"
    local dry_run=false
    local proc="8"
    local mem="128000"
    local queue="cab_auto"
    local project=""
    local job_name=""
    local regions=()
    local signals=()
    local region_labels=()
    local sample_labels=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --workDir)
                [[ $# -ge 2 ]] || fail "--workDir requires a value"
                work_dir="$2"
                shift 2
                ;;
            --region|--regions)
                [[ $# -ge 2 ]] || fail "$1 requires a value"
                regions+=("$2")
                shift 2
                ;;
            --signal|--signals)
                [[ $# -ge 2 ]] || fail "$1 requires a value"
                signals+=("$2")
                shift 2
                ;;
            --outputPrefix)
                [[ $# -ge 2 ]] || fail "--outputPrefix requires a value"
                output_prefix="$2"
                shift 2
                ;;
            --referencePoint)
                [[ $# -ge 2 ]] || fail "--referencePoint requires a value"
                reference_point="$2"
                shift 2
                ;;
            --before)
                [[ $# -ge 2 ]] || fail "--before requires a value"
                before="$2"
                shift 2
                ;;
            --after)
                [[ $# -ge 2 ]] || fail "--after requires a value"
                after="$2"
                shift 2
                ;;
            --binSize)
                [[ $# -ge 2 ]] || fail "--binSize requires a value"
                bin_size="$2"
                shift 2
                ;;
            --noMissingDataAsZero)
                missing_data_as_zero=false
                shift
                ;;
            --regionLabel|--regionsLabel)
                [[ $# -ge 2 ]] || fail "$1 requires a value"
                region_labels+=("$2")
                shift 2
                ;;
            --sampleLabel|--samplesLabel)
                [[ $# -ge 2 ]] || fail "$1 requires a value"
                sample_labels+=("$2")
                shift 2
                ;;
            --sortRegions)
                [[ $# -ge 2 ]] || fail "--sortRegions requires a value"
                sort_regions="$2"
                shift 2
                ;;
            --sortUsing)
                [[ $# -ge 2 ]] || fail "--sortUsing requires a value"
                sort_using="$2"
                shift 2
                ;;
            --sortUsingSamples)
                [[ $# -ge 2 ]] || fail "--sortUsingSamples requires a value"
                sort_using_samples="$2"
                shift 2
                ;;
            --labelRotation)
                [[ $# -ge 2 ]] || fail "--labelRotation requires a value"
                label_rotation="$2"
                shift 2
                ;;
            --heatmapHeight)
                [[ $# -ge 2 ]] || fail "--heatmapHeight requires a value"
                heatmap_height="$2"
                shift 2
                ;;
            --heatmapWidth)
                [[ $# -ge 2 ]] || fail "--heatmapWidth requires a value"
                heatmap_width="$2"
                shift 2
                ;;
            --colorMap)
                [[ $# -ge 2 ]] || fail "--colorMap requires a value"
                color_map="$2"
                shift 2
                ;;
            --zMin)
                [[ $# -ge 2 ]] || fail "--zMin requires a value"
                z_min="$2"
                shift 2
                ;;
            --zMax)
                [[ $# -ge 2 ]] || fail "--zMax requires a value"
                z_max="$2"
                shift 2
                ;;
            --outputDir)
                [[ $# -ge 2 ]] || fail "--outputDir requires a value"
                output_dir="$2"
                shift 2
                ;;
            --matrixFile)
                [[ $# -ge 2 ]] || fail "--matrixFile requires a value"
                matrix_file="$2"
                shift 2
                ;;
            --plotFile)
                [[ $# -ge 2 ]] || fail "--plotFile requires a value"
                plot_file="$2"
                shift 2
                ;;
            --executor)
                [[ $# -ge 2 ]] || fail "--executor requires a value"
                executor="$2"
                shift 2
                ;;
            --condaEnv)
                [[ $# -ge 2 ]] || fail "--condaEnv requires a value"
                conda_env="$2"
                shift 2
                ;;
            --condaExecutable)
                [[ $# -ge 2 ]] || fail "--condaExecutable requires a value"
                conda_executable="$2"
                shift 2
                ;;
            --noConda)
                conda_env=""
                shift
                ;;
            --dryRun)
                dry_run=true
                shift
                ;;
            --proc)
                [[ $# -ge 2 ]] || fail "--proc requires a value"
                proc="$2"
                shift 2
                ;;
            --mem)
                [[ $# -ge 2 ]] || fail "--mem requires a value"
                mem="$2"
                shift 2
                ;;
            --queue)
                [[ $# -ge 2 ]] || fail "--queue requires a value"
                queue="$2"
                shift 2
                ;;
            --project)
                [[ $# -ge 2 ]] || fail "--project requires a value"
                project="$2"
                shift 2
                ;;
            --jobName)
                [[ $# -ge 2 ]] || fail "--jobName requires a value"
                job_name="$2"
                shift 2
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                fail "Unknown argument: $1"
                ;;
        esac
    done

    [[ -n "$work_dir" ]] || fail "Missing required --workDir"
    [[ -n "$output_prefix" ]] || fail "Missing required --outputPrefix"
    [[ ${#regions[@]} -gt 0 ]] || fail "Provide at least one --region"
    [[ ${#signals[@]} -gt 0 ]] || fail "Provide at least one --signal"

    [[ "$executor" == "local" || "$executor" == "bsub" ]] || fail "--executor must be local or bsub"
    [[ -n "$conda_executable" ]] || fail "--condaExecutable must not be empty"
    validate_positive_integer "$before" "--before"
    validate_positive_integer "$after" "--after"
    validate_positive_integer "$bin_size" "--binSize"
    validate_positive_integer "$proc" "--proc"
    validate_positive_integer "$mem" "--mem"

    if [[ ${#region_labels[@]} -gt 0 && ${#region_labels[@]} -ne ${#regions[@]} ]]; then
        fail "Region label count (${#region_labels[@]}) must match region count (${#regions[@]})"
    fi

    if [[ ${#sample_labels[@]} -gt 0 && ${#sample_labels[@]} -ne ${#signals[@]} ]]; then
        fail "Sample label count (${#sample_labels[@]}) must match signal count (${#signals[@]})"
    fi

    work_dir="$(normalize_existing_dir "$work_dir")"
    if [[ -z "$output_dir" ]]; then
        output_dir="$work_dir"
    fi
    output_dir="$(normalize_output_path "$work_dir" "$output_dir")"

    if [[ -z "$matrix_file" ]]; then
        matrix_file="${output_dir}/${output_prefix}_matrix.gz"
    else
        matrix_file="$(normalize_output_path "$output_dir" "$matrix_file")"
    fi

    if [[ -z "$plot_file" ]]; then
        plot_file="${output_dir}/${output_prefix}_tornado.pdf"
    else
        plot_file="$(normalize_output_path "$output_dir" "$plot_file")"
    fi

    local region_value
    for region_value in "${regions[@]}"; do
        validate_input_file "$work_dir" "$region_value"
    done

    local signal_value
    for signal_value in "${signals[@]}"; do
        validate_input_file "$work_dir" "$signal_value"
    done

    if [[ "$dry_run" == false ]]; then
        mkdir -p "$output_dir"
    fi

    compute_cmd=(computeMatrix reference-point --referencePoint "$reference_point" -R "${regions[@]}" -S "${signals[@]}" -b "$before" -a "$after" --binSize "$bin_size")
    if [[ "$missing_data_as_zero" == true ]]; then
        compute_cmd+=(--missingDataAsZero)
    fi
    compute_cmd+=(-o "$matrix_file")

    plot_cmd=(plotHeatmap -m "$matrix_file" -o "$plot_file")
    append_optional_label_args --regionsLabel "${region_labels[@]}"
    append_optional_label_args --samplesLabel "${sample_labels[@]}"
    plot_cmd+=(--sortRegions "$sort_regions" --sortUsing "$sort_using" --sortUsingSamples "$sort_using_samples")
    plot_cmd+=(--labelRotation "$label_rotation")
    plot_cmd+=(--heatmapHeight "$heatmap_height" --heatmapWidth "$heatmap_width")
    if [[ -n "$color_map" ]]; then
        plot_cmd+=(--colorMap "$color_map")
    fi
    if [[ -n "$z_min" ]]; then
        plot_cmd+=(--zMin "$z_min")
    fi
    if [[ -n "$z_max" ]]; then
        plot_cmd+=(--zMax "$z_max")
    fi

    if [[ -n "$conda_env" ]]; then
        compute_run_cmd=("$conda_executable" run -n "$conda_env" "${compute_cmd[@]}")
        plot_run_cmd=("$conda_executable" run -n "$conda_env" "${plot_cmd[@]}")
    else
        compute_run_cmd=("${compute_cmd[@]}")
        plot_run_cmd=("${plot_cmd[@]}")
    fi

    local job_script=""
    local bsub_cmd=()
    if [[ "$executor" == "bsub" ]]; then
        if [[ -z "$job_name" ]]; then
            job_name="$output_prefix"
        fi
        local mem_per_proc=$((mem / proc))
        job_script="${output_dir}/${job_name}.commands.sh"
        bsub_cmd=(bsub -L /bin/bash -n "$proc" -R "span[hosts=1]" -R "rusage[mem=${mem_per_proc}]" -J "$job_name" -q "$queue" -cwd "$work_dir")
        if [[ -n "$project" ]]; then
            bsub_cmd+=(-P "$project")
        fi
    fi

    if [[ "$dry_run" == true ]]; then
        printf '# workDir\ncd %q\n\n' "$work_dir"
        printf '# computeMatrix\n'
        print_command "${compute_run_cmd[@]}"
        printf '\n# plotHeatmap\n'
        print_command "${plot_run_cmd[@]}"
        if [[ "$executor" == "bsub" ]]; then
            printf '\n# bsub options: proc=%s mem=%s queue=%s project=%s jobName=%s\n' "$proc" "$mem" "$queue" "$project" "${job_name:-$output_prefix}"
            printf '# bsub command\n'
            print_command "${bsub_cmd[@]}" "<" "$job_script"
        fi
        exit 0
    fi

    if [[ "$executor" == "local" ]]; then
        if [[ -n "$conda_env" ]]; then
            command -v "$conda_executable" >/dev/null 2>&1 || fail "Conda executable is not available on PATH: ${conda_executable}"
        else
            command -v computeMatrix >/dev/null 2>&1 || fail "computeMatrix is not available on PATH"
            command -v plotHeatmap >/dev/null 2>&1 || fail "plotHeatmap is not available on PATH"
        fi
        (
            cd "$work_dir"
            "${compute_run_cmd[@]}"
            "${plot_run_cmd[@]}"
        )
    else
        command -v bsub >/dev/null 2>&1 || fail "bsub is not available on PATH"
        write_job_script "$job_script" "$work_dir"
        "${bsub_cmd[@]}" < "$job_script"
        printf 'LSF command script: %s\n' "$job_script"
    fi

    printf 'Matrix: %s\n' "$matrix_file"
    printf 'Plot: %s\n' "$plot_file"
}

main "$@"
