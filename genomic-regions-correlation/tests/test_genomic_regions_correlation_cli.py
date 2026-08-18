"""Smoke tests for the GenometriCorr skill wrapper."""

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "run_genomic_regions_correlation.py"


class GenomicRegionsCorrelationCliTests(unittest.TestCase):
    """Test validation and dry-run behavior without R or conda."""

    def test_help(self) -> None:
        """Expose the required correlation arguments in help output."""
        result = subprocess.run([sys.executable, str(WRAPPER), "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--query", result.stdout)
        self.assertIn("--reference", result.stdout)
        self.assertIn("--genome", result.stdout)

    def test_dry_run_with_current_r(self) -> None:
        """Print a valid command without creating output or requiring conda."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "query.bed").write_text("chr1\t10\t20\n", encoding="utf-8")
            (root / "reference.bed").write_text("chr1\t30\t40\n", encoding="utf-8")
            output_root = root / "agentResults"
            result = subprocess.run(
                [
                    sys.executable,
                    str(WRAPPER),
                    "--inputDir", str(root),
                    "--query", "query.bed",
                    "--reference", "reference.bed",
                    "--genome", "hg38",
                    "--outputRoot", str(output_root),
                    "--outputPrefix", "demo",
                    "--noConda",
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = result.stdout + result.stderr
            self.assertIn("genometriCorr.r", output)
            self.assertIn("linkedInputs/query.bed", output)
            self.assertIn("Dry run complete", output)
            self.assertFalse(output_root.exists())

    def test_local_run_stages_inputs_and_writes_metadata(self) -> None:
        """Run the wrapper with a fake Rscript and verify its artifacts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "inputs"
            bin_dir = root / "bin"
            input_dir.mkdir()
            bin_dir.mkdir()
            (input_dir / "query.bed").write_text("chr1\t10\t20\n", encoding="utf-8")
            (input_dir / "reference.bed").write_text("chr1\t30\t40\n", encoding="utf-8")
            fake_rscript = bin_dir / "Rscript"
            fake_rscript.write_text(
                "#!/bin/sh\n"
                "touch \"${4}_versus_${5}.projection.pdf.pdf\"\n"
                "touch \"${4}_versus_${5}.vis.pdf\"\n"
                "touch \"${5}_versus_${4}.projection.pdf\"\n"
                "touch \"${5}_versus_${4}.vis.pdf\"\n",
                encoding="utf-8",
            )
            fake_rscript.chmod(0o750)
            output_root = root / "agentResults"
            environment = os.environ.copy()
            environment["PATH"] = str(bin_dir) + os.pathsep + environment.get("PATH", "")
            result = subprocess.run(
                [
                    sys.executable, str(WRAPPER),
                    "--inputDir", str(input_dir),
                    "--query", "query.bed",
                    "--reference", "reference.bed",
                    "--genome", "hg38",
                    "--outputRoot", str(output_root),
                    "--outputPrefix", "demo",
                    "--runId", "20260101T010203Z",
                    "--noConda", "--run",
                ],
                text=True,
                capture_output=True,
                env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            run_dir = output_root / "genomic-regions-correlation-20260101T010203Z"
            self.assertTrue((run_dir / "linkedInputs" / "query.bed").is_symlink())
            self.assertTrue((run_dir / "input-symlinks.tsv").is_file())
            metadata = json.loads((run_dir / "genomic-regions-correlation-run-metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["status"], "completed")
            self.assertEqual(len(metadata["expectedOutputs"]), 4)
            self.assertTrue(all(Path(path).is_file() for path in metadata["expectedOutputs"]))

    def test_bsub_dry_run_prints_cluster_options(self) -> None:
        """Print a complete LSF plan without requiring bsub or R."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "query.bed").write_text("chr1\t10\t20\n", encoding="utf-8")
            (root / "reference.bed").write_text("chr1\t30\t40\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(WRAPPER),
                    "--inputDir", str(root),
                    "--query", "query.bed",
                    "--reference", "reference.bed",
                    "--genome", "mm10",
                    "--outputRoot", str(root / "results"),
                    "--outputPrefix", "demo",
                    "--executor", "bsub",
                    "--queue", "cab_auto",
                    "--project", "project_a",
                    "--proc", "4",
                    "--mem", "8000",
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("bsub", result.stdout)
            self.assertIn("-q cab_auto", result.stdout)
            self.assertIn("-P project_a", result.stdout)
            self.assertIn("rusage[mem=2000]", result.stdout)
            self.assertIn("Dry run complete", result.stdout)
            self.assertFalse((root / "results").exists())

    def test_missing_input_fails(self) -> None:
        """Reject a missing BED file with an actionable error."""
        result = subprocess.run(
            [
                sys.executable, str(WRAPPER),
                "--query", "missing.bed",
                "--reference", "missing-reference.bed",
                "--genome", "hg38",
                "--outputPrefix", "demo",
                "--noConda",
            ],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
