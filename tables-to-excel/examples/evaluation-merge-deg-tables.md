# Evaluation: merge several DEG TSVs

## User request

“Combine these differential expression tables into one Excel file for a supplement, and keep track of which file is which.”

## Available inputs

- Three existing `.tsv` files with headers and gene or feature IDs.

## Expected agent behavior

1. Load [SKILL.md](../SKILL.md) and confirm paths and extensions.
2. Run `python scripts/tables_to_excel.py -i "<comma-separated paths>" -o "<user-chosen prefix>"`.
3. Return the `.xlsx` path and note that the first sheet is `NameDictionary`.

## Expected output structure

- Workbook with `NameDictionary` + three data sheets (or N + 1 sheets for N inputs).
- `NameDictionary` columns: `short name`, `path to original file`.

## Unacceptable behavior

- Silently dropping a table or changing sheet order.
- Using `--overwrite` without user confirmation when the output file exists.

## Required resources

- [scripts/tables_to_excel.py](../scripts/tables_to_excel.py)
