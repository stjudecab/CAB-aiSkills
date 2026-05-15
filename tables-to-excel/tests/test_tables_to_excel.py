"""Tests for tables_to_excel CLI and helpers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from tables_to_excel import (
    MAX_SHEET_NAME_LENGTH,
    build_name_dictionary,
    deduplicate_sheet_names,
    detect_separator,
    excel_output_path,
    main,
    resolve_input_files,
    truncate_sheet_name,
    write_excel,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_truncate_sheet_name_no_op() -> None:
    """Name shorter than max is returned unchanged."""
    assert truncate_sheet_name("abc", 10) == "abc"


def test_truncate_sheet_name_exact() -> None:
    """Name at exactly max length is returned unchanged."""
    s = "a" * 5
    assert truncate_sheet_name(s, 5) == s


def test_truncate_sheet_name_over() -> None:
    """Name longer than max is truncated correctly."""
    assert truncate_sheet_name("abcdefghij", 4) == "abcd"


def test_deduplicate_no_collisions() -> None:
    """Unique names returned unchanged."""
    names = ["a", "b", "c"]
    assert deduplicate_sheet_names(list(names), 31) == names


def test_deduplicate_single_collision() -> None:
    """Second occurrence gets `(1)` suffix."""
    out = deduplicate_sheet_names(["dup", "dup"], 31)
    assert out[0] == "dup"
    assert out[1] == "dup(1)"


def test_deduplicate_multiple_collisions() -> None:
    """Third occurrence gets `(2)` suffix, etc."""
    out = deduplicate_sheet_names(["x", "x", "x"], 31)
    assert out[0] == "x"
    assert out[1] == "x(1)"
    assert out[2] == "x(2)"


def test_deduplicate_suffix_truncates_base() -> None:
    """When suffix would exceed max length, base is truncated to fit."""
    max_len = 5
    base = "abcde"
    out = deduplicate_sheet_names([base, base], max_len)
    assert out[0] == "abcde"
    assert out[1] == "ab(1)"
    assert len(out[1]) == max_len


def test_detect_separator_csv(tmp_path: Path) -> None:
    """`.csv` maps to comma."""
    p = tmp_path / "t.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    assert detect_separator(p) == ","


def test_detect_separator_tsv(tmp_path: Path) -> None:
    """`.tsv` maps to tab."""
    p = tmp_path / "t.tsv"
    p.write_text("a\tb\n1\t2\n", encoding="utf-8")
    assert detect_separator(p) == "\t"


def test_detect_separator_txt(tmp_path: Path) -> None:
    """`.txt` maps to tab."""
    p = tmp_path / "t.txt"
    p.write_text("a\tb\n1\t2\n", encoding="utf-8")
    assert detect_separator(p) == "\t"


def test_detect_separator_unsupported(tmp_path: Path) -> None:
    """Unsupported extension raises ValueError."""
    p = tmp_path / "x.xml"
    p.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError, match=r"unsupported extension"):
        detect_separator(p)


def test_resolve_input_files_direct(tmp_path: Path) -> None:
    """Comma-separated list parsed correctly."""
    a = tmp_path / "one.csv"
    b = tmp_path / "two.tsv"
    a.write_text("x\n1\n", encoding="utf-8")
    b.write_text("y\tz\n1\t2\n", encoding="utf-8")
    spec = f"{a},{b}"
    paths = resolve_input_files(spec, base_dir=tmp_path)
    assert len(paths) == 2
    assert paths[0] == a.resolve()
    assert paths[1] == b.resolve()


def test_resolve_input_files_lst(tmp_path: Path) -> None:
    """`.lst` file parsed correctly; paths resolved relative to list parent."""
    sub = tmp_path / "data"
    sub.mkdir()
    tbl = sub / "inside.csv"
    tbl.write_text("c\nv\n", encoding="utf-8")
    lst = tmp_path / "files.lst"
    lst.write_text(f"data/{tbl.name}\n", encoding="utf-8")
    paths = resolve_input_files(str(lst), base_dir=tmp_path)
    assert len(paths) == 1
    assert paths[0] == tbl.resolve()


def test_resolve_input_files_missing_file(tmp_path: Path) -> None:
    """Missing file raises error with path in message."""
    missing = tmp_path / "nope.csv"
    spec = str(missing)
    with pytest.raises(FileNotFoundError) as exc:
        resolve_input_files(spec, base_dir=tmp_path)
    assert str(missing.resolve()) in str(exc.value)


def test_write_excel_creates_file(tmp_path: Path) -> None:
    """Output `.xlsx` file is created."""
    excel_path = tmp_path / "out.xlsx"
    name_df = build_name_dictionary(["s1"], [tmp_path / "a.csv"])
    table = pd.DataFrame({"a": [1]})
    write_excel(excel_path, name_df, [("s1", table)], overwrite=False)
    assert excel_path.is_file()


def test_write_excel_name_dictionary_first(tmp_path: Path) -> None:
    """First sheet is `NameDictionary`."""
    excel_path = tmp_path / "book.xlsx"
    dummy = tmp_path / "d.csv"
    dummy.write_text("k\n1\n", encoding="utf-8")
    name_df = build_name_dictionary(["d"], [dummy.resolve()])
    write_excel(
        excel_path,
        name_df,
        [("d", pd.DataFrame({"k": [1]}))],
        overwrite=False,
    )
    xl = pd.ExcelFile(excel_path)
    assert xl.sheet_names[0] == "NameDictionary"


def test_write_excel_name_dictionary_columns(tmp_path: Path) -> None:
    """NameDictionary has correct column headers."""
    excel_path = tmp_path / "book.xlsx"
    p = tmp_path / "q.csv"
    p.write_text("h\n0\n", encoding="utf-8")
    name_df = build_name_dictionary(["q"], [p.resolve()])
    write_excel(
        excel_path,
        name_df,
        [("q", pd.DataFrame({"h": [0]}))],
        overwrite=False,
    )
    nd = pd.read_excel(excel_path, sheet_name="NameDictionary")
    assert list(nd.columns) == ["short name", "path to original file"]


def test_write_excel_name_dictionary_content(tmp_path: Path) -> None:
    """Rows match expected short names and absolute paths."""
    excel_path = tmp_path / "book.xlsx"
    p = tmp_path / "alpha.csv"
    p.write_text("v\n9\n", encoding="utf-8")
    p_res = p.resolve()
    name_df = build_name_dictionary(["alpha"], [p_res])
    write_excel(
        excel_path,
        name_df,
        [("alpha", pd.DataFrame({"v": [9]}))],
        overwrite=False,
    )
    nd = pd.read_excel(excel_path, sheet_name="NameDictionary")
    assert nd.iloc[0]["short name"] == "alpha"
    assert nd.iloc[0]["path to original file"] == str(p_res)


def test_write_excel_sheet_count(tmp_path: Path) -> None:
    """Workbook has correct number of sheets (inputs + 1)."""
    excel_path = tmp_path / "book.xlsx"
    p1 = tmp_path / "t1.csv"
    p2 = tmp_path / "t2.csv"
    p1.write_text("a\n1\n", encoding="utf-8")
    p2.write_text("b\n2\n", encoding="utf-8")
    name_df = build_name_dictionary(["t1", "t2"], [p1.resolve(), p2.resolve()])
    write_excel(
        excel_path,
        name_df,
        [
            ("t1", pd.DataFrame({"a": [1]})),
            ("t2", pd.DataFrame({"b": [2]})),
        ],
        overwrite=False,
    )
    xl = pd.ExcelFile(excel_path)
    assert len(xl.sheet_names) == 3


def test_write_excel_no_overwrite(tmp_path: Path) -> None:
    """Raises error if output exists and overwrite is False."""
    excel_path = tmp_path / "exists.xlsx"
    excel_path.write_bytes(b"")
    name_df = build_name_dictionary(["s"], [tmp_path / "a.csv"])
    with pytest.raises(FileExistsError, match="already exists"):
        write_excel(excel_path, name_df, [("s", pd.DataFrame())], overwrite=False)


def test_write_excel_overwrite_flag(tmp_path: Path) -> None:
    """Succeeds if output exists and overwrite is True."""
    excel_path = tmp_path / "exists.xlsx"
    excel_path.write_bytes(b"")
    name_df = build_name_dictionary(["s"], [tmp_path / "a.csv"])
    write_excel(
        excel_path,
        name_df,
        [("s", pd.DataFrame({"x": [1]}))],
        overwrite=True,
    )
    assert excel_path.stat().st_size > 0


def test_end_to_end_csv(tmp_path: Path) -> None:
    """Full run with CSV input produces correct workbook."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("col1,col2\n1,2\n", encoding="utf-8")
    out = tmp_path / "combined"
    code = main(["-i", str(csv_path), "-o", str(out)])
    assert code == 0
    xlsx = excel_output_path(out)
    xl = pd.ExcelFile(xlsx)
    assert "NameDictionary" in xl.sheet_names
    assert "data" in xl.sheet_names
    df = pd.read_excel(xlsx, sheet_name="data")
    assert list(df.columns) == ["col1", "col2"]


def test_end_to_end_tsv(tmp_path: Path) -> None:
    """Full run with TSV input produces correct workbook."""
    tsv_path = tmp_path / "tab.tsv"
    tsv_path.write_text("c1\tc2\n3\t4\n", encoding="utf-8")
    out = tmp_path / "out"
    assert main(["-i", str(tsv_path), "-o", str(out)]) == 0
    xlsx = excel_output_path(out)
    df = pd.read_excel(xlsx, sheet_name="tab")
    assert list(df.columns) == ["c1", "c2"]


def test_end_to_end_lst_mode(tmp_path: Path) -> None:
    """Full run via `.lst` file produces correct workbook."""
    a = tmp_path / "first.csv"
    a.write_text("n\n7\n", encoding="utf-8")
    lst = tmp_path / "all.lst"
    lst.write_text(f"{a.name}\n", encoding="utf-8")
    out = tmp_path / "merged"
    assert main(["-i", str(lst), "-o", str(out)]) == 0
    xlsx = excel_output_path(out)
    xl = pd.ExcelFile(xlsx)
    assert "first" in xl.sheet_names


def test_end_to_end_repo_fixtures_comma_list(tmp_path: Path) -> None:
    """Bundle CSV + TSV + tab-separated TXT fixtures via comma-separated ``-i``."""
    csv_p = FIXTURES_DIR / "sample_alpha.csv"
    tsv_p = FIXTURES_DIR / "sample_beta.tsv"
    txt_p = FIXTURES_DIR / "sample_gamma.txt"
    spec = f"{csv_p},{tsv_p},{txt_p}"
    out = tmp_path / "fixture_bundle"
    assert main(["-i", spec, "-o", str(out)]) == 0
    xlsx = excel_output_path(out)
    xl = pd.ExcelFile(xlsx)
    assert xl.sheet_names[:4] == [
        "NameDictionary",
        "sample_alpha",
        "sample_beta",
        "sample_gamma",
    ]
    alpha = pd.read_excel(xlsx, sheet_name="sample_alpha")
    assert list(alpha.columns) == ["protein", "log2FC", "p_value"]
    assert len(alpha) == 3
    beta = pd.read_excel(xlsx, sheet_name="sample_beta")
    assert list(beta.columns) == ["sample_id", "condition", "read_count"]


def test_end_to_end_repo_fixtures_lst_file(tmp_path: Path) -> None:
    """Load CSV/TSV/TXT via ``tests/fixtures/three_tables.lst``."""
    lst = FIXTURES_DIR / "three_tables.lst"
    out = tmp_path / "from_lst"
    assert main(["-i", str(lst), "-o", str(out)]) == 0
    xlsx = excel_output_path(out)
    xl = pd.ExcelFile(xlsx)
    assert xl.sheet_names == [
        "NameDictionary",
        "sample_alpha",
        "sample_beta",
        "sample_gamma",
    ]
    gamma = pd.read_excel(xlsx, sheet_name="sample_gamma")
    assert list(gamma.columns) == ["peak_id", "span_bp", "q_value"]
    assert len(gamma) == 2


def test_module_constant_matches_excel_limit() -> None:
    """Guardrail: documented Excel limit stays 31."""
    assert MAX_SHEET_NAME_LENGTH == 31


def test_help_runs() -> None:
    """CLI help exits zero."""
    skill_root = Path(__file__).resolve().parent.parent
    script = skill_root / "scripts" / "tables_to_excel.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "maxSheetNameLen" in proc.stdout
    assert "logLevel" in proc.stdout
