#!/usr/bin/env python
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "extractRegionsPerFeature.py"
SPEC = importlib.util.spec_from_file_location("extractRegionsPerFeature", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExtractRegionsPerFeatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.outDir = Path(self.tmp.name) / "output"

    def tearDown(self):
        self.tmp.cleanup()

    def writeTsv(self, name, df):
        path = Path(self.tmp.name) / name
        df.to_csv(path, sep="\t", index=False)
        return str(path)

    def baseBedDf(self):
        return pd.DataFrame(
            [
                {
                    "Region": "chr1:100-200",
                    "chr": "chr1",
                    "start": 100,
                    "end": 200,
                    "FeatureAssignment": "Exon",
                    "inGeneBody": "GENE1",
                },
                {
                    "Region": "chr1:300-400",
                    "chr": "chr1",
                    "start": 300,
                    "end": 400,
                    "FeatureAssignment": "Intron",
                    "inGeneBody": "GENE2, GENE3",
                },
                {
                    "Region": "chr1:500-600",
                    "chr": "chr1",
                    "start": 500,
                    "end": 600,
                    "FeatureAssignment": "Intergenic",
                    "inGeneBody": ".",
                },
            ]
        )

    def baseVoomDf(self):
        return pd.DataFrame(
            [
                {
                    "Region": "chr1:100-200",
                    "chr": "chr1",
                    "start": 100,
                    "end": 200,
                    "log2FC": 1.5,
                    "q.value": 0.01,
                    "FeatureAssignment": "Promoter.Up",
                    "inGeneBody": "UP1, UP2",
                },
                {
                    "Region": "chr1:300-400",
                    "chr": "chr1",
                    "start": 300,
                    "end": 400,
                    "log2FC": -2.0,
                    "q.value": 0.02,
                    "FeatureAssignment": "Promoter.Up",
                    "inGeneBody": "DOWN1",
                },
                {
                    "Region": "chr1:500-600",
                    "chr": "chr1",
                    "start": 500,
                    "end": 600,
                    "log2FC": 0.5,
                    "q.value": 0.2,
                    "FeatureAssignment": "Exon",
                    "inGeneBody": "NS1",
                },
                {
                    "Region": "chr1:700-800",
                    "chr": "chr1",
                    "start": 700,
                    "end": 800,
                    "log2FC": 1.0,
                    "q.value": 0.01,
                    "FeatureAssignment": "TES (transcription end sites)",
                    "inGeneBody": "UP1, UP1",
                },
            ]
        )

    def makeArgs(self, infileName, **kwargs):
        defaults = {
            "infileName": infileName,
            "outDir": str(self.outDir),
            "mode": "auto",
            "featureColumn": "FeatureAssignment",
            "geneBodyColumn": "inGeneBody",
            "log2FCColumn": "log2FC",
            "fdrColumn": "q.value",
            "fdrThreshold": 0.05,
            "log2FCThreshold": 0.0,
            "sheetName": None,
        }
        defaults.update(kwargs)
        return argparseNamespace(defaults)

    def test_bed_mode_writes_one_bed_per_feature(self):
        infile = self.writeTsv("bed.anno", self.baseBedDf())
        manifest = MODULE.extractRegions(self.makeArgs(infile, mode="bed"))
        self.assertEqual(manifest["mode"], "bed")
        self.assertEqual(manifest["input_summary"]["output_bed_files"], 3)
        self.assertTrue((self.outDir / "Exon.bed").exists())
        self.assertTrue((self.outDir / "Intron.bed").exists())
        self.assertTrue((self.outDir / "Intergenic.bed").exists())

    def test_voom_mode_splits_up_and_down(self):
        infile = self.writeTsv("voom.anno", self.baseVoomDf())
        manifest = MODULE.extractRegions(self.makeArgs(infile, mode="voom"))
        self.assertEqual(manifest["mode"], "voom")
        names = {entry["set_name"] for entry in manifest["output_files"]}
        self.assertIn("Promoter.Up.up", names)
        self.assertIn("Promoter.Up.down", names)
        self.assertIn("TES.transcription_end_sites.up", names)
        self.assertNotIn("Exon.up", names)

    def test_gmt_deduplicates_genes(self):
        infile = self.writeTsv("voom.anno", self.baseVoomDf())
        MODULE.extractRegions(self.makeArgs(infile, mode="voom"))
        gmtPath = self.outDir / "voom.byFeature.genesets.gmt"
        lines = gmtPath.read_text(encoding="utf-8").strip().splitlines()
        tesLine = [line for line in lines if line.startswith("TES.transcription_end_sites.up")][0]
        fields = tesLine.split("\t")
        self.assertEqual(fields[2:], ["UP1"])

    def test_region_fallback_when_coords_missing(self):
        df = self.baseBedDf().drop(columns=["chr", "start", "end"])
        infile = self.writeTsv("region_only.anno", df)
        manifest = MODULE.extractRegions(self.makeArgs(infile, mode="bed"))
        self.assertEqual(manifest["input_summary"]["total_rows"], 3)

    def test_missing_required_columns_fails(self):
        df = self.baseBedDf().drop(columns=["inGeneBody"])
        infile = self.writeTsv("missing.anno", df)
        with self.assertRaises(SystemExit):
            MODULE.extractRegions(self.makeArgs(infile, mode="bed"))

    def test_column_overrides(self):
        df = self.baseVoomDf().rename(
            columns={
                "FeatureAssignment": "Feat",
                "inGeneBody": "Genes",
                "log2FC": "FC",
                "q.value": "FDR",
            }
        )
        infile = self.writeTsv("override.anno", df)
        manifest = MODULE.extractRegions(
            self.makeArgs(
                infile,
                mode="voom",
                featureColumn="Feat",
                geneBodyColumn="Genes",
                log2FCColumn="FC",
                fdrColumn="FDR",
            )
        )
        self.assertGreaterEqual(manifest["input_summary"]["output_bed_files"], 1)

    def test_xlsx_input(self):
        df = self.baseVoomDf()
        infile = str(Path(self.tmp.name) / "sample.xlsx")
        df.to_excel(infile, index=False, sheet_name="differentialPeaksTab")
        manifest = MODULE.extractRegions(self.makeArgs(infile, mode="voom", sheetName="differentialPeaksTab"))
        self.assertEqual(manifest["source_sheet"], "differentialPeaksTab")

    def test_manifest_and_summary_written(self):
        infile = self.writeTsv("bed.anno", self.baseBedDf())
        MODULE.extractRegions(self.makeArgs(infile, mode="bed"))
        manifest = json.loads((self.outDir / "extraction_manifest.json").read_text(encoding="utf-8"))
        summary = (self.outDir / "extraction_manifest.tsv").read_text(encoding="utf-8")
        self.assertIn("feature_name_mapping", manifest)
        self.assertIn("set_name", summary)


class argparseNamespace:
    def __init__(self, kwargs):
        self.__dict__.update(kwargs)


if __name__ == "__main__":
    unittest.main()
