# SICER BED to broadPeak conversion

## Contents

- When to convert
- Example SICER row
- Mapping to broadPeak
- Converter script
- Validation

## When to convert

ChIP-R accepts **narrowPeak** and **broadPeak** only. SICER outputs a 10-column BED that is **not** ENCODE-compliant. Convert before calling `chipr`.

Indicators:

- Filename contains `.sicer.` or ends with `.sicer.bed`
- Peak name field contains `dom_` (domain index)

## Example SICER row

```text
chr1    858800  875799  sample-W200-G600_dom_2_    4254    +    0.0    3.8057777584267543    0.0    1355
```

Columns (typical): chrom, start, end, name, score, strand, (unused), signal-like float, (unused), block length.

## Mapping to broadPeak

| broadPeak column | SICER source |
|------------------|--------------|
| chrom | column 1 |
| chromStart | column 2 |
| chromEnd | column 3 |
| name | column 4 |
| score | column 5 |
| strand | column 6 (or `.` if invalid) |
| signalValue | column 8 (must be finite) |
| pValue | `0` (SICER does not provide MACS-style p-values) |
| qValue | `0` |

The converter is conservative: it does **not** invent p/q values from scores. Rank-based steps in ChIP-R then rely primarily on **signalValue** for broad/SICER-style data unless the user chooses another `--rankmethod`.

## Converter script

```bash
python scripts/sicer_to_broadpeak.py \
  --input /path/to/sample.sicer.bed \
  --output /path/to/sample.broadPeak
```

Or use `reproducible_peaks.py`, which converts automatically when SICER format is detected.

## Validation

- Fail on rows with fewer than 9 columns
- Fail on non-finite **signalValue** (column 8)
- Skip `track` / `browser` / comment lines
