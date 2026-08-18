<p align="center">
  <img src="assets/CAB-aiSkills_logo.svg" alt="CAB aiSkills" width="440" />
</p>

# CAB-aiSkills

Portable **agent skills** (filesystem-discoverable folders with `SKILL.md` and tooling) for bioinformatics and omics workflows: each skill is a self-contained folder with `SKILL.md` (what the agent does), runnable scripts, and documentation. Install by copying or symlinking a skill into your client’s skill path (for example `.cursor/skills/<skill-name>/` in Cursor).

**Maintained by:** Toolbox curator in [AUTHORS.md](AUTHORS.md) (St Jude Children's Research Hospital). **Per-skill authors** and script copyrights: [AUTHORS.md](AUTHORS.md) Skills table.

**Attribution:** Three-layer policy (skill package vs bundled code vs scientific method): [docs/attribution.md](docs/attribution.md). Method citations live in each skill’s `references/citations.md`.

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

---

### [reproducible-peaks](reproducible-peaks/README.md)

Generates **reproducible ChIP-seq / ATAC-seq peak sets** across replicates with **ChIP-R** from **narrowPeak**, **broadPeak**, or **SICER BED** (auto-converted), including audit logs and run metadata.

**Example prompt:** *Generate reproducible CTCF peaks with ChIP-R using the two BED files in `reproducible-peaks/examples` and save outputs under `agentResults/`.*

---

### [custom-ES-plot-GSEApy](custom-ES-plot-GSEApy/README.md)

Generates **GSEA enrichment score (ES) plots** and **statistics text files** from saved GSEApy `pre_res` pickle files **or** Broad Institute GSEA desktop output directories, with support for exact gene sets, regex patterns (e.g. `SOS_peaks.*`), list files, and `allGeneSets` — including non-significant gene sets omitted from default top-set figure exports.

**Example prompt (GSEApy pickle):** *From `GSEApy_prerank.pre_res.RNA.SynGR303_48h_vs_DMSO_48h.pkl`, plot enrichment for all `SOS_peaks.*` gene sets and save PNG/PDF/TXT under `agentResults/`.*

**Example prompt (Broad GSEA):** *From my Broad GSEA folder `48h.GseaPreranked.<timestamp>/`, replot ES plots for `REACTOME_HEME_SIGNALING` and all `CHIP.EP300.*48H.*UP` gene sets; save PNG/PDF/TXT under `agentResults/`.*

---

### [genomic-regions-annotation](genomic-regions-annotation/README.md)

Runs **genomic region annotation and interpretation** for ATAC-seq, ChIP-seq, CUT&Tag, CUT&RUN, and differential region results, including nearby-gene annotation, genomic feature assignment, reporting, visualization, and GSEA-ready exports. Requires an explicitly stated genome build.

**Example prompt:** *Run genomic region annotation on header-free BED files in `peaks/` using genome build `hg38`, and write outputs under `agentResults/`.*

---

### [genomic-regions-correlation](genomic-regions-correlation/README.md)

Compares two genomic-region BED files with **GenometriCorr**, producing reciprocal correlation reports and visualizations for `hg19`, `hg38`, or `mm10`. Requires an explicitly stated genome build and supports local or LSF execution.

**Example prompt:** *Compare `gained.bed` and `lost.bed` with GenometriCorr using `hg38`, and write the reports under `agentResults/`.*

---

### [genomic-set-analysis](genomic-set-analysis/README.md)

**Order-independent overlap** of genomic region sets (ChIP-seq, ATAC-seq, CUT&Tag, CUT&RUN, narrowPeak/broadPeak/BED) or gene sets (GMT) with **Intervene** (Venn / UpSet / pairwise), producing a membership matrix and mutually exclusive per-sector files. Optionally chains the **`genomic-regions-annotation`** skill for nearby-gene annotation and the **`pathway-enrichment-enrichr`** skill for Enrichr pathway enrichment of **both** the intersection sectors and the original inputs, plus gated expression summaries. Requires an explicitly stated genome build for annotation/pathway steps; motif enrichment and deeptools are planned but not yet available.

**Example prompt:** *Overlap the three BED files in `genomic-set-analysis/examples`, annotate against `hg38`, and run pathway enrichment for each intersection and for the original files; write outputs under `agentResults/`.*

---

### [tornado-plots](tornado-plots/README.md)

Generates **deepTools tornado plots and heatmaps** from BED region files and BigWig signal tracks using `computeMatrix reference-point` and `plotHeatmap`. Supports local execution and optional LSF `bsub` submission.

**Example prompt:** *Create a tornado plot from `Empty.Up2FC.Region.bed` and `Empty.Down2FC.Region.bed` using the supplied ChIP-seq BigWig tracks, and save outputs under `agentResults/`.*

---

### [bioinformatics-reporting](bioinformatics-reporting/README.md)

Inspects, validates, and combines **existing** bioinformatics outputs into polished **Quarto HTML/PDF reports** with provenance-backed metrics, portable staged artifacts, and a full audit trail. Supports RNA-seq, ATAC-seq, ChIP-seq, CUT&RUN/CUT&Tag, methylation, differential results, enrichment/GSEA, overlap analysis, QC summaries, and multi-omics result collections.

**Example prompt:** *Create a scientific bioinformatics report from the results in `agentResults/my-analysis-20260709T141453Z`, including overlap plots, enrichment tables, and an evidence-grounded executive summary; write HTML and PDF under `agentResults/`.*

---

### [colorblind-sim](colorblind-sim/README.md)

Simulates how figures appear under **color vision deficiency (CVD)** using **CBviz** (protanopia, deuteranopia, tritanopia, monochrome). Accepts PNG/JPEG/TIFF directly; converts PDF (and SVG/EPS when host tools are available) to PNG before simulation. Writes multi-panel preview figures plus a full run audit trail.

**Example prompt:** *Simulate colorblindness on my volcano plot `figures/volcano.png` (or `figure.pdf`) and save the CBviz panels under `agentResults/`.*
