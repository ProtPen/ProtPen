# tests/test_foldseek.py
import os
import tempfile
from unittest.mock import patch
from protpen import foldseek


@patch("protpen.foldseek.subprocess.run")
def test_run_foldseek_search_invokes_command(mock_subprocess):
    with (
        tempfile.TemporaryDirectory() as pdb_dir,
        tempfile.TemporaryDirectory() as out_dir,
    ):
        # Create fake PDB file
        pdb_file = os.path.join(pdb_dir, "sample.pdb")
        with open(pdb_file, "w") as f:
            f.write("ATOM FAKE DATA\n")

        foldseek.run_foldseek_search(pdb_dir, out_dir, tmp_dir="tmp_test", db="mock_db")

        output_file = os.path.join(out_dir, "sample.tsv")
        expected_cmd = [
            "foldseek",
            "easy-search",
            pdb_file,
            "mock_db",
            output_file,
            "tmp_test",
            "--format-mode",
            "4",
        ]

        mock_subprocess.assert_called_once_with(expected_cmd, check=True)
