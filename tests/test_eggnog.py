# tests/test_eggnog.py
import os
import tempfile
import pandas as pd
from unittest.mock import patch, MagicMock
from protpen import eggnog


@patch("subprocess.run")
def test_run_eggnog_mapper_calls_subprocess(mock_subproc):
    with tempfile.TemporaryDirectory() as tmpdir:
        fasta_path = os.path.join(tmpdir, "test.faa")
        with open(fasta_path, "w") as f:
            f.write(">P1\nMAKAKAQWERTY")

        eggnog.run_eggnog_mapper(
            fasta_path, tmpdir, "test_prefix", emapper_path="mock_emapper.py"
        )

        expected_out = os.path.join(tmpdir, "test_prefix")
        mock_subproc.assert_called_once()
        assert "mock_emapper.py" in mock_subproc.call_args[0][0]
        assert f"-i {fasta_path}" in mock_subproc.call_args[0][0]
        assert f"-o {expected_out}" in mock_subproc.call_args[0][0]


def test_convert_to_tsv_reads_annotation_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        annotation_file = os.path.join(tmpdir, "test.emapper.annotations")
        output_tsv = os.path.join(tmpdir, "output.tsv")

        content = """# comment line
Q1\tortholog1\t1e-10\t200\tOG1\t5\tC\tDescription1\tName1\tGO1\t1.1.1.1\tKO1\tPath1\tMod1\tReact1\tClass1\tBrite1\tTC1\tCAZy1\tBigg1\tPFAM1
"""

        with open(annotation_file, "w") as f:
            f.write(content)

        eggnog.convert_to_tsv(tmpdir, "test", output_tsv)

        df = pd.read_csv(output_tsv, sep="\t")
        assert df.shape == (1, 21)
        assert df["query"].iloc[0] == "Q1"
