# tests/test_enrich_utils.py
import os
import json
import tempfile
from unittest.mock import patch
from protpen import enrich_utils
from unittest import mock
import csv

def test_get_uniprot_info_reads_cached_json(tmp_path):
    # Create mock UniProt JSON
    uniprot_id = "P12345"
    json_dir = tmp_path / "uniprot_json_enrich"
    json_dir.mkdir()
    data = {
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Mock Protein"}}
        },
        "uniProtKBCrossReferences": [
            {
                "database": "INTERPRO",
                "id": "IPR000001",
                "properties": [{"key": "EntryName", "value": "IPR_MOCK"}]
            },
            {
                "database": "SUPFAM",
                "id": "SF000001",
                "properties": [{"key": "EntryName", "value": "SF_MOCK"}]
            }
        ]
    }
    with open(json_dir / f"{uniprot_id}.json", "w") as f:
        json.dump(data, f)

    with patch("protpen.enrich_utils.download_uniprot_json") as mock_download:
        result = enrich_utils.get_uniprot_info(uniprot_id, str(json_dir))
        assert result["description"] == "Mock Protein"
        assert result["interpro"] == "IPR_MOCK"
        assert result["supfam"] == "SF_MOCK"
        mock_download.assert_not_called()


def test_enrich_tsv(tmp_path):
    input_path = tmp_path / "test.tsv"
    output_path = tmp_path / "enriched.tsv"

    # Write mock input. Real Foldseek targets always include a chain
    # suffix (e.g. "_H"), which enrich_tsv's pair_to_info is keyed on
    # (pdb_id, chain_id), since a single PDB structure's chains can map to
    # different UniProt entries.
    with open(input_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["query", "target"], delimiter="\t")
        writer.writeheader()
        writer.writerow({"query": "Q1", "target": "4is4-assembly1.cif.gz_H||4mdz-assembly1.cif.gz_A"})
        writer.writerow({"query": "Q2", "target": "5abc-assembly1.cif.gz_A"})

    pair_to_info = {
        ("4is4", "H"): {"description": "desc1", "interpro": "ipr1", "supfam": "sf1"},
        ("4mdz", "A"): {"description": "desc2", "interpro": "ipr2", "supfam": "sf2"},
        ("5abc", "A"): {"description": "desc3", "interpro": "ipr3", "supfam": "sf3"},
    }

    enrich_utils.enrich_tsv(input_path, output_path, pair_to_info)

    with open(output_path, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    assert rows[0]["UniProt_Description"] == "desc1||desc2"
    assert rows[0]["UniProt_InterPro"] == "ipr1||ipr2"
    assert rows[0]["UniProt_SUPFAM"] == "sf1||sf2"
    assert rows[1]["UniProt_Description"] == "desc3"
    assert rows[1]["UniProt_InterPro"] == "ipr3"
    assert rows[1]["UniProt_SUPFAM"] == "sf3"


@mock.patch("protpen.enrich_utils.requests.get")
def test_get_uniprot_info_mocked(mock_get, tmp_path):
    sample_response = {
        "proteinDescription": {
            "recommendedName": {
                "fullName": {"value": "Mock Protein"}
            }
        },
        "uniProtKBCrossReferences": [
            {"database": "InterPro", "id": "IPR9999"},
            {"database": "SUPFAM", "id": "SF9999"}
        ]
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = sample_response

    result = enrich_utils.get_uniprot_info("P12345", json_dir=tmp_path)
    assert result["description"] == "Mock Protein"
    assert result["interpro"] == "IPR9999"
    assert result["supfam"] == "SF9999"


