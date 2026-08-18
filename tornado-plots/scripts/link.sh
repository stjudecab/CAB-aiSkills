#!/usr/bin/env bash
#########################################################################
# Copyright (c) 2026-~ Hasan Al Reza && St Jude
#
# This source code is released for free distribution under the terms of the
# CreativeCommons BY-NC-SA 4.0 International License
#
#*Author:       Hasan Al Reza < hasan.al.reza.bd@gmail.com >
# File Name: link.sh
# Description:
# Creates validated symlinks for tornado-plot BED and BigWig inputs.
#########################################################################

set -euo pipefail

show_usage() {
    cat <<'USAGE'
Usage:
  link.sh --outputDir DIR --file FILE [--file FILE ...]
  link.sh --sourceDir DIR --outputDir DIR --pattern '*.bw' [--pattern '*.bed']

Create symlinks for tornado-plot inputs in a working directory.

Required:
  --outputDir DIR       Directory where symlinks are created.

Inputs:
  --file FILE           Source file to link. Repeat for multiple files.
                        Relative paths are resolved against --sourceDir.
  --sourceDir DIR       Base directory for relative --file values and patterns.
  --pattern GLOB        Filename pattern to match under --sourceDir. Repeatable.
  --recursive           Search patterns recursively under --sourceDir.

Options:
  --manifest FILE       Write source-to-link TSV manifest. Default:
                        <outputDir>/input-symlinks.tsv.
  --force               Replace an existing conflicting link or file.
  --dryRun              Validate and print planned links without creating them.
  --help                Show this help message.

Examples:
  bash scripts/link.sh --sourceDir inputs --outputDir work --file up.bed --file sample.bw
  bash scripts/link.sh --sourceDir bw --outputDir work --pattern '*.bw'
USAGE
}

fail() {
    printf 'link.sh error: %s\n' "$1" >&2
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
    local path_value="$1"
    case "$path_value" in
        /*) printf '%s\n' "$path_value" ;;
        *) printf '%s/%s\n' "$(pwd -P)" "$path_value" ;;
    esac
}

normalize_existing_file() {
    local file_path="$1"
    [[ -f "$file_path" ]] || fail "Expected input file but found: ${file_path}"
    local file_dir
    file_dir="$(cd "$(dirname "$file_path")" && pwd -P)"
    printf '%s/%s\n' "$file_dir" "$(basename "$file_path")"
}

resolve_source_file() {
    local candidate="$1"
    local source_dir="$2"

    case "$candidate" in
        /*) normalize_existing_file "$candidate" ;;
        *)
            [[ -n "$source_dir" ]] || fail "Relative --file value requires --sourceDir: ${candidate}"
            normalize_existing_file "${source_dir}/${candidate}"
            ;;
    esac
}

append_pattern_matches() {
    local source_dir="$1"
    local pattern="$2"
    local recursive="$3"
    local match
    local found=false

    if [[ "$recursive" == true ]]; then
        while IFS= read -r -d '' match; do
            source_files+=("$(normalize_existing_file "$match")")
            found=true
        done < <(find "$source_dir" -type f -name "$pattern" -print0)
    else
        while IFS= read -r -d '' match; do
            source_files+=("$(normalize_existing_file "$match")")
            found=true
        done < <(find "$source_dir" -maxdepth 1 -type f -name "$pattern" -print0)
    fi

    [[ "$found" == true ]] || fail "Pattern matched no files under ${source_dir}: ${pattern}"
}

record_manifest_line() {
    local source_path="$1"
    local target_path="$2"
    local manifest_path="$3"

    if [[ -n "$manifest_path" ]]; then
        printf '%s\t%s\n' "$source_path" "$target_path" >> "$manifest_path"
    fi
}

create_or_report_link() {
    local source_path="$1"
    local output_dir="$2"
    local manifest_path="$3"
    local force="$4"
    local dry_run="$5"
    local target_path="${output_dir}/$(basename "$source_path")"

    if [[ "$dry_run" == true ]]; then
        printf 'Would link: %s -> %s\n' "$target_path" "$source_path"
        return
    fi

    if [[ -e "$target_path" || -L "$target_path" ]]; then
        if [[ -L "$target_path" && "$(readlink "$target_path")" == "$source_path" ]]; then
            printf 'Already linked: %s -> %s\n' "$target_path" "$source_path"
            record_manifest_line "$source_path" "$target_path" "$manifest_path"
            return
        fi

        if [[ "$force" == true ]]; then
            rm -f "$target_path"
        else
            fail "Refusing to overwrite existing path without --force: ${target_path}"
        fi
    fi

    ln -s "$source_path" "$target_path"
    printf 'Linked: %s -> %s\n' "$target_path" "$source_path"
    record_manifest_line "$source_path" "$target_path" "$manifest_path"
}

main() {
    local source_dir=""
    local output_dir=""
    local manifest=""
    local force=false
    local dry_run=false
    local recursive=false
    local explicit_files=()
    local patterns=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --sourceDir)
                [[ $# -ge 2 ]] || fail "--sourceDir requires a value"
                source_dir="$2"
                shift 2
                ;;
            --outputDir)
                [[ $# -ge 2 ]] || fail "--outputDir requires a value"
                output_dir="$2"
                shift 2
                ;;
            --file)
                [[ $# -ge 2 ]] || fail "--file requires a value"
                explicit_files+=("$2")
                shift 2
                ;;
            --pattern)
                [[ $# -ge 2 ]] || fail "--pattern requires a value"
                patterns+=("$2")
                shift 2
                ;;
            --manifest)
                [[ $# -ge 2 ]] || fail "--manifest requires a value"
                manifest="$2"
                shift 2
                ;;
            --force)
                force=true
                shift
                ;;
            --dryRun)
                dry_run=true
                shift
                ;;
            --recursive)
                recursive=true
                shift
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

    [[ -n "$output_dir" ]] || fail "Missing required --outputDir"
    [[ ${#explicit_files[@]} -gt 0 || ${#patterns[@]} -gt 0 ]] || fail "Provide at least one --file or --pattern"

    if [[ -n "$source_dir" ]]; then
        source_dir="$(normalize_existing_dir "$source_dir")"
    fi

    if [[ ${#patterns[@]} -gt 0 && -z "$source_dir" ]]; then
        fail "--pattern requires --sourceDir"
    fi

    output_dir="$(normalize_output_path "$output_dir")"
    if [[ -z "$manifest" ]]; then
        manifest="${output_dir}/input-symlinks.tsv"
    else
        manifest="$(normalize_output_path "$manifest")"
    fi

    source_files=()
    local file_value
    for file_value in "${explicit_files[@]}"; do
        source_files+=("$(resolve_source_file "$file_value" "$source_dir")")
    done

    local pattern_value
    for pattern_value in "${patterns[@]}"; do
        append_pattern_matches "$source_dir" "$pattern_value" "$recursive"
    done

    if [[ "$dry_run" == false ]]; then
        mkdir -p "$output_dir"
        mkdir -p "$(dirname "$manifest")"
        : > "$manifest"
    fi

    local source_file
    for source_file in "${source_files[@]}"; do
        create_or_report_link "$source_file" "$output_dir" "$manifest" "$force" "$dry_run"
    done

    if [[ "$dry_run" == false ]]; then
        printf 'Manifest: %s\n' "$manifest"
    fi
}

main "$@"
