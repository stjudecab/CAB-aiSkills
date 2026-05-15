
<p align="center">
  <img src="../assets/CAB-aiSkills_tables-to-excel.svg" alt="tables-to-excel skill badge" width="520" />
</p>

# Tables to Excel — Agent Skill

Portable **Agent Skill** for merging **CSV / TSV / TXT** tables into one **multi-sheet `.xlsx`** workbook with a provenance **`NameDictionary`** sheet. Agent-facing instructions are in [SKILL.md](SKILL.md).

## Environment

- **Python** 3.10 or newer
- **Dependencies:**

```bash
cd exampleSkills/tables-to-excel
pip install -r requirements.txt
```

## Install for Cursor or other agent clients

- **Project skill:** Copy or symlink this folder so the client discovers a directory named `tables-to-excel` containing `SKILL.md` (for example `.cursor/skills/tables-to-excel/` in a project, or a path your runtime lists as a skill root).
- **Invoke** by skill name `tables-to-excel` or by asking the agent to merge tables into a multi-sheet Excel file with a NameDictionary map, as described in [SKILL.md](SKILL.md).

Microsoft’s Agent Skills pattern (filesystem discovery, `SKILL.md` frontmatter, progressive disclosure) is summarized in the repository copy of the Learn article: [Agent Skills - Microsoft Learn - guidelines.html](../../Agent%20Skills%20-%20Microsoft%20Learn%20-%20guidelines.html).

## Example usage

Run from **this directory** (`exampleSkills/tables-to-excel`) unless you pass absolute paths.

### Comma-separated inputs (e.g. DEG tables)

```bash
python scripts/tables_to_excel.py \
  -i "/path/to/table1.tsv,/path/to/table2.tsv,/path/to/table3.tsv" \
  -o "/path/to/out/DEG_suplTable"
```

Produces `/path/to/out/DEG_suplTable.xlsx` with `NameDictionary` first, then one sheet per file.

### Output path already ending in `.xlsx`

```bash
python scripts/tables_to_excel.py \
  -i "results/a.csv,results/b.tsv" \
  -o "agentResults/20260508T120000Z/combined.xlsx"
```

### Manifest (`.lst`) — one path per line

```bash
python scripts/tables_to_excel.py \
  -i tests/fixtures/three_tables.lst \
  -o tmp/combined_from_lst
```

Paths inside the `.lst` are relative to the **folder that contains the `.lst` file**.

### Replace existing workbook

```bash
python scripts/tables_to_excel.py -i data.csv -o out/workbook --overwrite
```

### Verbosity

```bash
python scripts/tables_to_excel.py -i data.csv -o out/run --logLevel DEBUG
```

## Layout

| Path | Role |
|------|------|
| [SKILL.md](SKILL.md) | When to use, workflow, safety, outputs |
| [scripts/tables_to_excel.py](scripts/tables_to_excel.py) | CLI entrypoint |
| [scripts/logging_support.py](scripts/logging_support.py) | Logging helpers |
| [references/formats-and-output.md](references/formats-and-output.md) | Input/output reference |
| [tests/](tests/) | Pytest suite and fixtures |

## Relationship to `ExcelBuilder/`

The canonical development tree with Sphinx docs lives under repository **`ExcelBuilder/`**. This **`tables-to-excel`** folder is the **portable skill package** (skill metadata + `scripts/` layout) aligned with [AGENTS.md](../../AGENTS.md). When changing behavior, update **both** trees or document a single source of truth.

## Testing

```bash
python scripts/tables_to_excel.py --help
python -m pytest tests/ -v
```

## License

Packaging and skill text: **Apache-2.0** (see [SKILL.md](SKILL.md) frontmatter).
