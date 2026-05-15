# Enrichr pathway enrichment — reference

## Contents

- [Input modes](#input-modes)
- [Library presets and engines](#library-presets-and-engines)
- [Output artifacts](#output-artifacts)
- [Manifest column aliases](#manifest-column-aliases)
- [Naming constraints](#naming-constraints)
- [Dependencies and API](#dependencies-and-api)

## Input modes

| Mode | Description |
|------|-------------|
| **single** | One plain-text gene list (`--genes`), one output prefix. Produces merged `*.sum.*` tables plus Excel and bar PDFs via `enrichment_postprocess.py`. |
| **gmt** | Standard GMT file: each row is `set_name<TAB>description<TAB>gene1<TAB>gene2<TAB>...`. Triggers per-set enrichment and combined summaries. |
| **manifest** | TSV listing paths to separate gene list files; the runner builds a temporary GMT and runs the **gmt** pipeline. |

## Library presets and engines

- **`--libraryPreset`** is passed to `enrichr_api.py` **`-t`**. Values such as `stjudehg` or `stjudemm` expand to curated comma-separated Enrichr library lists inside `enrichr_api.py`. You can instead pass an explicit comma-separated list of Enrichr library names.
- **`--engine`**: `Enrichr` (default) or **`YeastEnrichr`**. The yeast engine uses different base URLs and default library lists when presets were left at human/mouse defaults.

## Output artifacts

- **Merged tables** (`*.sum.p5`, `*.sum.q5`, `*.sum.all`): combined across libraries with a **`Database`** column; sorted by reported combined score column as in `enrichr_api.py`.
- **Single-list Excel**: `{excelStem}.GenesLists.xlsx`, `{excelStem}.fc_q0.05.xlsx`, `{excelStem}.fc_p0.05.xlsx` plus companion spreadsheet index TXT files.
- **Single-list figures**: `{outPrefix}.sum.q5.pdf`, `{outPrefix}.sum.p5.pdf` (top 10 rows when present).
- **GMT batch**: under `{outPrefix}/`, Excel gene list and FDR/nominal workbooks using the GMT stem, combined `summary_pvals.tsv` / `summary_FDRs.tsv`, heatmaps `*.summary_* .top10.pdf`, and dot plots when `pathway_dotplot.py` runs successfully.

## Manifest column aliases

The manifest reader accepts:

- File column: **`file`**, **`path`**, or **`gene_list`**
- Label column: **`label`**, **`sample`**, or **`name`**

Each file should contain one gene symbol per line (tokens before the first whitespace are used).

## Naming constraints

- **`--outPrefix`** must contain only letters, digits, `.`, `-`, and `_` (Enrichr GMT batch creates a directory with this name).
- Manifest labels are sanitized to safe tokens; ambiguous names fall back to `sample<n>`.

## Dependencies and API

- Network calls target the Enrichr endpoints on **maayanlab.cloud** (see `enrichr_api.py` for paths).
- Optional **`rich`** improves logging in `pathway_dotplot.py`; absence falls back to standard logging.
- **`xlsxwriter`** is required for Excel outputs.

For command examples, see [README.md](../README.md).
