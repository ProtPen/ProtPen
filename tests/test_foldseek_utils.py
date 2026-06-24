# tests/test_foldseek_utils.py
import tempfile
import os
import pandas as pd
from protpen import foldseek_utils


def test_extract_protein_ids():
    fasta = """>P12345 some header
MAAA
>P67890 another header
MTTT"""
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        f.write(fasta)
        fasta_path = f.name

    result = foldseek_utils.extract_protein_ids(fasta_path)
    os.unlink(fasta_path)

    assert result == {"P12345", "P67890"}


def test_consolidate_includes_proteins_with_valid_hits():
    with tempfile.TemporaryDirectory() as tmpdir:
        fasta_path = os.path.join(tmpdir, "queries.fasta")
        with open(fasta_path, "w") as f:
            f.write(">Q1\nMAA\n>Q2\nMTT")

        df = pd.DataFrame(
            {
                "query": ["Q1", "Q1", "Q2", "Q2"],
                "target": ["T1", "T2", "T3", "T4"],
                "evalue": [1e-5, 1e-3, 1e-4, 0.0],  # Q2 has one valid and one 0
                "other": ["X", "Y", "Z", "W"],
            }
        )
        file_path = os.path.join(tmpdir, "result.tsv")
        df.to_csv(file_path, sep="\t", index=False)

        result_df = foldseek_utils.consolidate_foldseek_results(
            tmpdir, fasta_path, top_x=1
        )

        assert set(result_df["query"]) == {"Q1", "Q2"}  # Both included


def test_consolidate_excludes_proteins_with_only_zero_hits():
    with tempfile.TemporaryDirectory() as tmpdir:
        fasta_path = os.path.join(tmpdir, "queries.fasta")
        with open(fasta_path, "w") as f:
            f.write(">Q1\nMAA\n>Q2\nMTT")

        df = pd.DataFrame(
            {
                "query": ["Q1", "Q1", "Q2", "Q2"],
                "target": ["T1", "T2", "T3", "T4"],
                "evalue": [1e-5, 1e-3, 0.0, 0.0],  # Q2 has only zeros
                "other": ["X", "Y", "Z", "W"],
            }
        )
        file_path = os.path.join(tmpdir, "result.tsv")
        df.to_csv(file_path, sep="\t", index=False)

        result_df = foldseek_utils.consolidate_foldseek_results(
            tmpdir, fasta_path, top_x=1
        )

        assert set(result_df["query"]) == {"Q1"}  # Q2 excluded
