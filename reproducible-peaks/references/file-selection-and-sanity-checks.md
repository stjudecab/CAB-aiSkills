# File selection and sanity checks

## Contents

- Scope one condition per run
- Filename patterns
- Replicate collision warnings
- Format checks
- When to ask the user
- Agent checklist

## Scope one condition per run

Reproducible peaks answer: *"Which intervals are consistent across biological replicates for this factor in this condition?"*

Include only replicates of **one** target (e.g. CTCF) and **one** condition (e.g. DMSO, untreated). Do **not** merge replicates from different drugs, timepoints, or genotypes unless the user explicitly designs a pooled analysis.

## Filename patterns

Useful tokens (examples):

| Token | Meaning |
|-------|---------|
| `CTCF`, `H3K27ac`, `H3K27me3` | Target / mark |
| `DMSO`, `EGF`, `UT` | Condition |
| `rep1`, `rep2`, `replicate2`, `R1` | Replicate index |
| `noC_` | MACS2 without control (→ `signalvalue` rank method) |
| `.narrowPeak`, `.broadPeak` | Format hint |
| `.sicer.` | SICER output (convert first) |

When the user says "CTCF reproducible peaks" in a folder with many files, **list candidates**, group by condition, and confirm the exact set before running ChIP-R.

## Replicate collision warnings

If two files parse to the **same replicate id** (e.g. two `rep1` from different conditions), treat this as a **strong signal** that conditions were mixed. Stop and ask the user which condition to use.

The CLI logs warnings; the agent must not ignore them.

## Format checks

1. Extension and column count (9 = broadPeak, 10 = narrowPeak or SICER)
2. Non-finite signal/p/q values → hard error
3. SICER → convert or fail

## When to ask the user

Ask before running when:

- Multiple conditions or targets match the request
- Format is ambiguous (plain `.bed` with 10 columns but unknown caller)
- Replicate ids collide across files
- Fewer than two replicates but user asked for "reproducible" peaks (explain limitation; offer single-sample union or wait for more replicates)
- ChIP-R is not installed and the user has not approved installation

## Agent checklist

1. List files in the user directory matching target/condition language.
2. State which files will be used and why.
3. State inferred strategy (`withControl`, `noControl`, `broadPeak`, `sicer`).
4. State `-m` and `--rankmethod` (defaults or user overrides).
5. Run [scripts/reproducible_peaks.py](../scripts/reproducible_peaks.py) or document why not.
6. Report output BED paths and `run_metadata.json`.
