# Formats and workbook layout

## Contents

- Input modes (`-i`)
- Encoding and delimiters
- Output path (`-o`)
- `NameDictionary` sheet
- Data sheets and naming
- Logging

## Input modes (`-i`)

1. **Comma-separated paths** — Multiple `.csv`, `.tsv`, or `.txt` paths in one argument. Order is preserved.
2. **Single `.lst` file** — When `-i` resolves to exactly one path ending in `.lst`, that file is read as a manifest:
   - One path per non-empty line.
   - Lines starting with `#` are comments.
   - Relative paths are resolved relative to the **directory containing the `.lst` file**.

## Encoding and delimiters

- **Encoding:** UTF-8 for list files and tables.
- **`.csv`:** comma-separated.
- **`.tsv` and `.txt`:** tab-separated (same rules).

## Output path (`-o`)

- If `-o` ends with `.xlsx`, that path is used.
- Otherwise, `.xlsx` is appended to the prefix. Parent directories are created as needed.

## `NameDictionary` sheet

Always the **first** worksheet.

| Column | Meaning |
|--------|---------|
| `short name` | Final Excel sheet name for that input. |
| `path to original file` | Absolute path to the source file at merge time. |

## Data sheets and naming

- One worksheet per input, **after** `NameDictionary`, in the same order as inputs.
- Name = file **stem** (no directory, no extension), max length **31** by default (Excel limit). **`--maxSheetNameLen`** cannot exceed 31 (larger values are clamped).
- Duplicate stems after truncation get suffixes `(1)`, `(2)`, … while staying within the length limit.

## Logging

- **Console:** Rich-formatted messages.
- **File:** `tables_to_excel.log` in the **current working directory** of the process (basename tied to the script stem).

For full deduplication and truncation logic, see the upstream **ExcelBuilder** `docs/methods.md` in this repository if present.
