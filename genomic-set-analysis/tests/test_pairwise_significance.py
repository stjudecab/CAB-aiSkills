"""Unit tests for pairwise Fisher overlap significance."""

from __future__ import annotations

import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pairwise_significance as pw  # noqa: E402


def test_bh_fdr_monotonic():
    """BH FDR is monotone non-decreasing in the ranked p-values."""
    p = np.array([0.01, 0.04, 0.03, 0.20])
    fdr = pw.bhFdr(p)
    assert np.all(np.isfinite(fdr))
    assert np.all(fdr >= p - 1e-12)
    assert np.all(fdr <= 1.0)


def test_parse_universe_spec():
    """Universe flag accepts auto/-1 or a positive integer."""
    assert pw.parseUniverseSpec("auto") == "auto"
    assert pw.parseUniverseSpec("-1") == "auto"
    assert pw.parseUniverseSpec("20000") == 20000
    with pytest.raises(ValueError):
        pw.parseUniverseSpec("0")
    with pytest.raises(ValueError):
        pw.parseUniverseSpec("nope")


def test_fold_enrichment_direction():
    """FE > 1 is overrepresented; FE < 1 is underrepresented."""
    expected, fe, direction = pw.pairFoldEnrichment(a=8, sizeA=10, sizeB=10, N=20)
    assert expected == 5.0
    assert fe == pytest.approx(1.6)
    assert direction == "overrepresented"
    _, fe2, direction2 = pw.pairFoldEnrichment(a=1, sizeA=10, sizeB=10, N=20)
    assert fe2 == pytest.approx(0.2)
    assert direction2 == "underrepresented"


def test_run_pairwise_significance_gmt(tmp_path):
    """GMT mode writes TSV matrices including fold enrichment and clustermaps."""
    geneSets = OrderedDict(
        [
            ("SetA", ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]),
            ("SetB", ["G1", "G2", "G3", "G4", "G9", "G10"]),
            ("SetC", ["G11", "G12", "G13", "G14"]),
        ]
    )
    outDir = tmp_path / "pairwiseSignificance"
    result = pw.runPairwiseSignificance(
        names=list(geneSets.keys()),
        outDir=outDir,
        mode="gmt",
        figsize=(6, 5),
        universeSize=14,
        universeSpec="auto",
        geneSets=geneSets,
    )
    assert result == outDir
    longDf = pd.read_csv(outDir / "pairwise.summary.long.tsv", sep="\t")
    assert len(longDf) == 3
    assert {
        "jaccard",
        "odds_ratio",
        "fisher_pvalue",
        "fisher_fdr",
        "fold_enrichment",
        "enrichment_direction",
        "expected_overlap",
        "universe_source",
    } <= set(longDf.columns)
    assert (longDf["universe_source"] == "auto_union").all()
    assert (outDir / "pairwise.fold_enrichment.tsv").is_file()
    assert (outDir / "pairwise.enrichment_direction.tsv").is_file()
    assert (outDir / "pairwise.fold_enrichment.clustermap.pdf").is_file()
    assert not (outDir / "pairwise.log2_fold_enrichment.clustermap.pdf").is_file()
    for stem in (
        "pairwise.overlap_count",
        "pairwise.jaccard",
        "pairwise.log2_odds_ratio",
        "pairwise.fold_enrichment",
        "pairwise.fisher_pvalue",
        "pairwise.fisher_fdr",
    ):
        assert (outDir / f"{stem}.clustermap.pdf").is_file()


def test_run_pairwise_significance_manual_universe(tmp_path):
    """Manual universe N is recorded and changes fold enrichment."""
    geneSets = OrderedDict(
        [
            ("SetA", ["G1", "G2", "G3", "G4"]),
            ("SetB", ["G1", "G2", "G5", "G6"]),
        ]
    )
    outDir = tmp_path / "pwManual"
    pw.runPairwiseSignificance(
        names=["SetA", "SetB"],
        outDir=outDir,
        mode="gmt",
        figsize=(5, 4),
        universeSize=6,
        universeSpec=100,
        geneSets=geneSets,
    )
    longDf = pd.read_csv(outDir / "pairwise.summary.long.tsv", sep="\t")
    assert longDf.loc[0, "universe_N"] == 100
    assert longDf.loc[0, "universe_source"] == "manual"
    assert longDf.loc[0, "union_size"] == 6
    assert longDf.loc[0, "fold_enrichment"] == pytest.approx(2 * 100 / (4 * 4))
    assert longDf.loc[0, "enrichment_direction"] == "overrepresented"


def test_run_pairwise_significance_skips_single_set(tmp_path):
    """Fewer than two sets returns None and writes nothing."""
    outDir = tmp_path / "pairwiseSignificance"
    result = pw.runPairwiseSignificance(
        names=["Only"],
        outDir=outDir,
        mode="gmt",
        geneSets={"Only": ["G1", "G2"]},
    )
    assert result is None
