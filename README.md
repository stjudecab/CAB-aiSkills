<p align="center">
  <img src="assets/CAB-aiSkills_logo.svg" alt="CAB aiSkills" width="440" />
</p>

# CAB-aiSkills

Portable **agent skills** (filesystem-discoverable folders with `SKILL.md` and tooling) for bioinformatics and omics workflows: each skill is a self-contained folder with `SKILL.md` (what the agent does), runnable scripts, and documentation. Install by copying or symlinking a skill into your client’s skill path (for example `.cursor/skills/<skill-name>/` in Cursor).

**Maintained by:** [Wojciech Rosikiewicz](AUTHORS.md) (St Jude Children's Research Hospital). Per-skill and per-script credits: [AUTHORS.md](AUTHORS.md).

**License:** [CC BY-NC-SA 4.0](LICENSE.txt) (Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International).

---

## Skills

### [pathway-enrichment-enrichr](pathway-enrichment-enrichr/README.md)

Runs **Enrichr** pathway enrichment over one gene list or many lists (GMT or TSV manifest), producing merged tables, **Excel** workbooks, **PDF** bar charts for top pathways, and for batch runs **heatmaps** and **dot plots**.

**Example prompt:** *Run Enrichr pathway enrichment on my gene list `genes.txt`, use library preset `stjudehg`, and write Excel summaries and PDF bar plots under `./enrichr_out`.*

---

### [tables-to-excel](tables-to-excel/README.md)

Merges **CSV / TSV / TXT** tables into a single **multi-sheet `.xlsx`** workbook with a first-sheet **`NameDictionary`** mapping each sheet to its source path for provenance.

**Example prompt:** *Merge `table1.tsv`, `table2.csv`, and `table3.txt` into one Excel file with a NameDictionary sheet; save as `./combined_tables.xlsx`.*

---

### [kde-correlation-scatter](kde-correlation-scatter/README.md)

Builds **publication-style 2D scatter plots with KDE density** comparing two differential experiments (e.g. RNA-seq DEG tables, ChIP-seq peaks, or `.rnk` scores), with Pearson/Spearman correlation, quadrant counts, and per-quadrant export lists.

**Example prompt:** *Make a KDE correlation scatter comparing `contrast_A.regulation.tsv` and `contrast_B.regulation.tsv` using directional p-values; write figures under `./plots`.*

---

### [volcano-grid-plot](volcano-grid-plot/README.md)

Builds **publication-ready grids of Volcano and/or MA plots** from multiple differential RNA-seq or differential binding tables, with shared axis limits, optional gene highlighting, and column-name harmonization guidance.

**Example prompt:** *Plot GSE202762 EGF timepoints from "volcano-grid-plot/examples" directory in natural order as a volcano grid plot. Highlight EGR1 on volcano and MA figures.*
