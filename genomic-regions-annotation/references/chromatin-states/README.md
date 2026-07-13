# Chromatin-state reference resources

| File | Purpose |
|------|---------|
| `RoadmapCollectionsMetadata.tsv` | ChromHMM collections with `StatesFileLoc.hg38` / `StatesFileLoc.hg19` download URLs |
| `Segway_annotations_ENCODE_metadata.tsv` | ENCODE Segway accessions and download URLs (native hg19) |
| `availableModelsLookup.tsv` | Biosample descriptions → ChromHMM / Segway collection IDs for model matching |
| `state2name.tsv` | Roadmap 15-state friendly names (E1–E15) |
| `ENCODE_state2name.tsv` | Segway 9-state friendly names (E1–E9) |
| `hg19ToHg38.over.chain` | UCSC chain for Segway liftOver |

Prepared models are **not** stored here; they go under the skill-local `cache/` directory (gitignored).
