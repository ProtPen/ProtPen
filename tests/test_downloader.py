import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from protpen import downloader


# Test cases for the downloader module
# Test for download_structures_from_fasta function
@patch("protpen.downloader.requests.get")
@patch("protpen.downloader.requests.head")
@patch("protpen.downloader.extract_alphafold_id")
def test_download_structures_from_fasta(mock_extract_af_id, mock_head, mock_get):
    mock_extract_af_id.return_value = "AF-P12345-F1"
    mock_head.return_value.status_code = 200
    mock_get.return_value.content = b"MOCK_PDB"

    # Create temporary working dir and FASTA file
    with tempfile.TemporaryDirectory() as tmpdir:
        fasta_path = os.path.join(tmpdir, "test.fasta")
        json_path = os.path.join(tmpdir, "P12345.json")

        # Write FASTA file
        with open(fasta_path, "w") as f:
            f.write(
                """>sp|P12345|AATM_RABIT Aspartate aminotransferase, mitochondrial OS=Oryctolagus cuniculus OX=9986 GN=GOT2 PE=1 SV=2\nMALLHSARVLSGVASAFHPGLAAAASARASSWWAHVEMGPPDPILGVTEAYKRDTNSKKM
    NLGVGAYRDDNGKPYVLPSVRKAEAQIAAKGLDKEYLPIGGLAEFCRASAELALGENSEV
    VKSGRFVTVQTISGTGALRIGASFLQRFFKFSRDVFLPKPSWGNHTPIFRDAGMQLQSYR
    YYDPKTCGFDFTGALEDISKIPEQSVLLLHACAHNPTGVDPRPEQWKEIATVVKKRNLFA
    FFDMAYQGFASGDGDKDAWAVRHFIEQGINVCLCQSYAKNMGLYGERVGAFTVICKDADE
    AKRVESQLKILIRPMYSNPPIHGARIASTILTSPDLRKQWLQEVKGMADRIIGMRTQLVS
    NLKKEGSTHSWQHITDQIGMFCFTGLKPEQVERLTKEFSIYMTKDGRISVAGVTSGNVGY
    LAHAIHQVTK\n"""
            )

        # Manually write the fake UniProt JSON file
        with open(json_path, "w") as f:
            json.dump(
                {
                    "uniProtKBCrossReferences": [
                        {"database": "AlphaFoldDB", "id": "AF-P12345-F1"}
                    ]
                },
                f,
            )

        # Run function
        result = downloader.download_structures_from_fasta(fasta_path, tmpdir)

        # Assertions
        assert "P12345" in result
        pdb_path = result["P12345"]
        assert pdb_path.endswith(".pdb")
        assert os.path.exists(pdb_path)

        mock_extract_af_id.assert_called_once()


# Test for extract_protein_ids_from_fasta function
def test_extract_protein_ids_from_fasta():
    fasta_content = """>sp|P12345|AATM_RABIT Aspartate aminotransferase, mitochondrial OS=Oryctolagus cuniculus OX=9986 GN=GOT2 PE=1 SV=2
MALLHSARVLSGVASAFHPGLAAAASARASSWWAHVEMGPPDPILGVTEAYKRDTNSKKM
NLGVGAYRDDNGKPYVLPSVRKAEAQIAAKGLDKEYLPIGGLAEFCRASAELALGENSEV
VKSGRFVTVQTISGTGALRIGASFLQRFFKFSRDVFLPKPSWGNHTPIFRDAGMQLQSYR
YYDPKTCGFDFTGALEDISKIPEQSVLLLHACAHNPTGVDPRPEQWKEIATVVKKRNLFA
FFDMAYQGFASGDGDKDAWAVRHFIEQGINVCLCQSYAKNMGLYGERVGAFTVICKDADE
AKRVESQLKILIRPMYSNPPIHGARIASTILTSPDLRKQWLQEVKGMADRIIGMRTQLVS
NLKKEGSTHSWQHITDQIGMFCFTGLKPEQVERLTKEFSIYMTKDGRISVAGVTSGNVGY
LAHAIHQVTK
>tr|Q67890|Q67890_HBV Large envelope protein OS=Hepatitis B virus OX=10407 GN=Pre S1,Pre S2,S PE=3 SV=1
MGQNLSTSNPLGFFPDHQLDPAFRANTANPDWDFNPNKDTWPDANKVGAGAFGLGFTPPH
GGLLGWSPQAQGILQTLPANPPPASTNRQSGRQPTPLSPPLRNTHPQAMQWNSTTFHQTL
QDPRVRGLYFPAGGSSSGTVNPVLTTASPLSSISARTGDPVTIMENITSGFLGPLLVLEA
GFFLLTRILTIPQSLDSWWTSLNFLGGTTVCLGQNSQSPTSHHSPTSCPPICPGYRWMCL
RRFIIFLFILLLCLIFLLVLLDYQGMLPVCPLIPGTSTTSTGPCRTCTTPAQGTSMYPSC
CCTKPSDGNCTCIPIPSSWAFGKFLWQWASARFSWLSLLVPFVQWFVGLSPTVWVSAIWM
MWYWGPSLYSIVSPFIPLLPIFFCLWVYI
"""
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        f.write(fasta_content)
        f_path = f.name

    ids = downloader.extract_protein_ids_from_fasta(f_path)
    os.unlink(f_path)

    assert set(ids) == {"P12345", "Q67890"}


# Test for download_uniprot_json function
@patch("protpen.downloader.requests.get")
def test_download_uniprot_json_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"mock": "data"}
    mock_get.return_value = mock_response

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "P12345.json")
        success = downloader.download_uniprot_json("P12345", out_path)

        assert success is True
        assert os.path.exists(out_path)
        with open(out_path) as f:
            data = json.load(f)
        assert data == {"mock": "data"}


@patch("protpen.downloader.requests.get")

# Test for download_uniprot_json failure
def test_download_uniprot_json_failure(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "FAIL.json")
        success = downloader.download_uniprot_json("FAIL", out_path)
        assert success is False
        assert not os.path.exists(out_path)


# Test for extract_alphafold_id function
@patch("protpen.downloader.requests.head")
@patch("protpen.downloader.requests.get")
def test_download_alphafold_pdb(mock_get, mock_head):
    mock_head.return_value.status_code = 200
    mock_get.return_value.content = b"FAKE_PDB"

    with tempfile.TemporaryDirectory() as tmpdir:
        path = downloader.download_alphafold_pdb("P12345", tmpdir)
        assert path.endswith(".pdb")
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert f.read() == b"FAKE_PDB"
