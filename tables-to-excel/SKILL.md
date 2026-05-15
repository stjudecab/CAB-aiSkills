---
name: tables-to-excel
description: >-
  Merge CSV, TSV, or tab-delimited TXT tables into one multi-sheet .xlsx workbook with a first-sheet NameDictionary mapping each worksheet name to the absolute path of its source file. Use when consolidating DEG tables, gene lists, QC summaries, or any flat tables for a shareable Excel bundle with auditability; when avoiding manual copy-paste into Excel; or when the user asks for multi-sheet Excel from several TSV/CSV files with traceable provenance.
license: Apache-2.0
compatibility: >-
  Requires Python 3.10+, pandas, openpyxl, rich, packaging. Local filesystem read/write only; no network. Writes one .xlsx and a tables_to_excel.log in the process working directory unless logging is reconfigured.
metadata:
  author: SKILL_merge_tables maintainers
  version: "1.0.0"
  status: stable
  last_reviewed: "2026-05-08"
allowed-tools: shell python
---

# Tables to Excel (multi-sheet workbook)

## Purpose

Produce a single `.xlsx` where each input table is its own worksheet and the first sheet **`NameDictionary`** records **final sheet name → absolute source path**. This preserves provenance for reproducibility and gives a controlled merge path compared to pasting into Excel (where identifiers can be misinterpreted as dates).

## When to use

- Combine multiple **CSV / TSV / TXT** (tab-delimited) tables into **one workbook**.
- Need an **audit trail** of which files were merged.
- User mentions **supplemental table**, **multi-sheet Excel**, **bundle DEG / RNA-seq tables**, **NameDictionary**, or **merge TSV to xlsx**.

## When not to use

- Inputs are not flat delimited tables (e.g. Excel-in-Excel styling, images, multi-region reports).
- User needs a single long table (join / append rows) rather than one sheet per file.
- Overwriting an existing workbook without explicit user approval (default is to **fail** if output exists).

## Required inputs

- **Input spec (`-i`)**: either
  - a **comma-separated** list of paths to `.csv`, `.tsv`, or `.txt` files, or
  - a **single `.lst` file** (one path per line; `#` comments and blank lines ignored; relative paths resolve against the **directory containing the `.lst`**).
- **Output prefix (`-o`)**: path or prefix; the workbook is **`{output}.xlsx`** unless `-o` already ends with `.xlsx`.

## Optional inputs

- **`--maxSheetNameLen`**: max worksheet title length (default **31**, Excel’s limit; values **> 31** are clamped with a warning).
- **`--overwrite`**: allow replacing an existing output file.
- **`--logLevel`**: `DEBUG` … `CRITICAL` (default `INFO`).

## Workflow

1. Confirm all input paths exist and extensions are `.csv`, `.tsv`, or `.txt`.
2. Choose an output path; prefer a dedicated directory such as repository-local **`agentResults/<runId>/`** for agent-produced deliverables (see repository `AGENTS.md`).
3. From the skill root, run:

   `python scripts/tables_to_excel.py -i "<spec>" -o "<outputPrefix>" [--overwrite]`

4. Verify exit code **0**, then open the workbook and confirm sheet order: **`NameDictionary`**, then data sheets in input order.
5. Report the **absolute path** of the `.xlsx` and summarize sheet names.

## Scripts

| Script | Role |
|--------|------|
| [scripts/tables_to_excel.py](scripts/tables_to_excel.py) | CLI: load tables, build `NameDictionary`, write `.xlsx`. |
| [scripts/logging_support.py](scripts/logging_support.py) | Rich console + `tables_to_excel.log` file logging. |

## Output format

- **File**: `<OUTPUT>.xlsx` (or exact path if `-o` ends with `.xlsx`).
- **Sheet order**: `NameDictionary` first; then one sheet per input file in order.
- **NameDictionary columns**: `short name`, `path to original file` (absolute paths at run time).
- **Data sheet names**: file **stem**, truncated to the active max length, deduplicated with `(1)`, `(2)`, … if needed.

## Quality checks

- Non-zero exit: read stderr and `tables_to_excel.log` in the working directory.
- First sheet must be **`NameDictionary`** with the two expected columns.
- Sheet count = **1 + number of inputs**.

## Safety and limitations

- **Do not** pass **`--overwrite`** unless the user explicitly wants to replace the file.
- **UTF-8** encoding is assumed for all inputs.
- **Delimiters**: `.csv` → comma; `.tsv` and `.txt` → tab; first row is the header.
- Very large files may be slow or memory-heavy; scope runs appropriately.

## Failure and escalation

- Missing files or wrong extensions: fix paths or convert inputs; do not guess alternate files.
- Output exists without `--overwrite`: ask once whether to use `--overwrite` or a new path.

## Resources

- [references/formats-and-output.md](references/formats-and-output.md) — inputs, outputs, naming rules.
- [README.md](README.md) — install, Cursor/Biomni-style invocation, command examples.

## Examples

- Comma-separated inputs: see [README.md](README.md).
- `.lst` manifest: [tests/fixtures/three_tables.lst](tests/fixtures/three_tables.lst) (used by tests).
