"""Smoke tests for tornado-plots command-line helpers."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command and capture text output.

    Args:
        command (list[str]): Command vector to execute.
        cwd (Path | None): Optional working directory.

    Returns:
        subprocess.CompletedProcess[str]: Completed process with captured output.
    """

    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


class TornadoPlotsCliTests(unittest.TestCase):
    """Smoke tests for wrapper and helper CLIs."""

    def test_wrapper_help(self) -> None:
        """Verify the Python wrapper exposes help text."""

        result = run_command([sys.executable, str(ROOT / "run-tornado-plots.py"), "--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--regions", result.stdout)
        self.assertIn("--signals", result.stdout)
        self.assertIn("--condaEnv", result.stdout)

    def test_link_script_creates_symlinks(self) -> None:
        """Verify link.sh stages explicit input files and writes a manifest."""

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_path = Path(tmp_dir_name)
            source_dir = tmp_path / "source"
            output_dir = tmp_path / "linked"
            source_dir.mkdir()
            bed_file = source_dir / "up.bed"
            bw_file = source_dir / "sample.bw"
            bed_file.write_text("chr1\t10\t20\n", encoding="utf-8")
            bw_file.write_text("placeholder\n", encoding="utf-8")

            result = run_command(
                [
                    "bash",
                    str(ROOT / "scripts" / "link.sh"),
                    "--outputDir",
                    str(output_dir),
                    "--file",
                    str(bed_file),
                    "--file",
                    str(bw_file),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output_dir / "up.bed").is_symlink())
            self.assertTrue((output_dir / "sample.bw").is_symlink())
            manifest = output_dir / "input-symlinks.tsv"
            self.assertTrue(manifest.is_file())
            self.assertIn("up.bed", manifest.read_text(encoding="utf-8"))

    def test_plot_script_dry_run(self) -> None:
        """Verify plot.sh builds deepTools commands without requiring deepTools."""

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_path = Path(tmp_dir_name)
            work_dir = tmp_path / "work"
            out_dir = tmp_path / "out"
            work_dir.mkdir()
            (work_dir / "up.bed").write_text("chr1\t10\t20\n", encoding="utf-8")
            (work_dir / "sample.bw").write_text("placeholder\n", encoding="utf-8")

            result = run_command(
                [
                    "bash",
                    str(ROOT / "scripts" / "plot.sh"),
                    "--workDir",
                    str(work_dir),
                    "--outputDir",
                    str(out_dir),
                    "--outputPrefix",
                    "demo",
                    "--region",
                    "up.bed",
                    "--signal",
                    "sample.bw",
                    "--regionLabel",
                    "Up Region",
                    "--sampleLabel",
                    "Sample_A",
                    "--dryRun",
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("computeMatrix", result.stdout)
            self.assertIn("plotHeatmap", result.stdout)
            self.assertIn("demo_tornado.pdf", result.stdout)
            self.assertEqual(result.stdout.count("--regionsLabel"), 1)
            self.assertEqual(result.stdout.count("--samplesLabel"), 1)
            self.assertIn("--labelRotation 45", result.stdout)
            self.assertIn("Up\\ Region", result.stdout)
            self.assertIn("$'Sample_\\nA'", result.stdout)
            self.assertNotIn("bsub options:", result.stdout)
            self.assertNotIn("# bsub command", result.stdout)
            self.assertNotIn("-L /bin/bash", result.stdout)

    def test_wrapper_dry_run_plans_commands(self) -> None:
        """Verify wrapper dry-run resolves filenames and prints helper commands."""

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_path = Path(tmp_dir_name)
            input_dir = tmp_path / "inputs"
            output_root = tmp_path / "agentResults"
            input_dir.mkdir()
            (input_dir / "Empty.Down2FC.Region.bed").write_text("chr1\t30\t40\n", encoding="utf-8")
            (input_dir / "Empty.Up2FC.Region.bed").write_text("chr1\t10\t20\n", encoding="utf-8")
            (input_dir / "XPO1-AB_Mut.singleRep.bw").write_text("placeholder\n", encoding="utf-8")
            (input_dir / "XPO1-AB_WT.singleRep.bw").write_text("placeholder\n", encoding="utf-8")

            result = run_command(
                [
                    sys.executable,
                    str(ROOT / "run-tornado-plots.py"),
                    "--inputDir",
                    str(input_dir),
                    "--regions",
                    "Empty.Down2FC.Region.bed",
                    "Empty.Up2FC.Region.bed",
                    "--signals",
                    "XPO1-AB_Mut.singleRep.bw",
                    "XPO1-AB_WT.singleRep.bw",
                    "--outputRoot",
                    str(output_root),
                    "--outputPrefix",
                    "demo",
                    "--dryRun",
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Dry run complete", result.stdout)
            self.assertIn("scripts/link.sh", result.stdout)
            self.assertIn("scripts/plot.sh", result.stdout)
            self.assertIn("--condaEnv tornado_env", result.stdout)
            self.assertIn("--executor local", result.stdout)
            self.assertLess(result.stdout.index("Up2FC"), result.stdout.index("Down2FC"))
            self.assertLess(result.stdout.index("--regionLabel Up2FC"), result.stdout.index("--regionLabel Down2FC"))
            self.assertIn("--labelRotation 45", result.stdout)
            self.assertIn("--sampleLabel XPO1-AB_Mut", result.stdout)
            self.assertIn("--sampleLabel XPO1-AB_WT", result.stdout)
            self.assertFalse(output_root.exists())


if __name__ == "__main__":
    unittest.main()
