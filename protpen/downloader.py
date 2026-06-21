# protpen/downloader.py
import requests
import os
import json
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Latest known AlphaFoldDB model version. Checked first (then descending) so
# the common case finds a hit on the first HEAD request instead of scanning
# up from v1.
LATEST_ALPHAFOLD_VERSION = 4


def extract_protein_ids_from_fasta(file_in):
    protein_ids = set()
    with open(file_in, "r") as fasta_file:
        for line in fasta_file:
            if line.startswith(">"):
                parts = line.strip().split("|")
                if len(parts) > 2:
                    protein_id = parts[1]
                else:
                    match = re.match(r"^>(\S+)", line)
                    protein_id = match.group(1) if match else None
                if protein_id:
                    protein_ids.add(protein_id)
    return list(protein_ids)


def download_uniprot_json(uniprot_id, output_file):
    url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}"
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_file, "w") as f:
            json.dump(response.json(), f, indent=2)
        return True
    return False


def extract_alphafold_id(data):
    for ref in data.get('uniProtKBCrossReferences', []):
        if ref.get('database') == 'AlphaFoldDB':
            return ref.get('id', '')
    return ''


def download_alphafold_pdb(alphafold_id, output_folder):
    pdb_path = os.path.join(output_folder, f"{alphafold_id}.pdb")
    base_url = f"https://alphafold.ebi.ac.uk/files/AF-{alphafold_id}-F1-model_v"

    # Try the latest known version first, then fall back to scanning the
    # rest. Almost every entry resolves on versions, while a full
    # ascending 1-100 scan made this the slowest part of the pipeline.
    versions = list(range(LATEST_ALPHAFOLD_VERSION, 0, -1)) + \
        [v for v in range(1, 101) if v > LATEST_ALPHAFOLD_VERSION]

    for version in versions:
        url = base_url + str(version) + ".pdb"
        response = requests.head(url)
        if response.status_code == 200:
            logging.info(f"Found structure for {alphafold_id} (v{version}). Downloading...")
            response = requests.get(url)
            os.makedirs(output_folder, exist_ok=True)
            with open(pdb_path, "wb") as f:
                f.write(response.content)
            return pdb_path
    logging.warning(f"No structure found for {alphafold_id} in versions 1-100.")
    return None


def _process_protein(pid, output_folder):
    logging.info(f"Processing {pid}...")
    json_path = os.path.join(output_folder, f"{pid}.json")

    if not os.path.exists(json_path):
        logging.info(f"Downloading UniProt JSON for {pid}")
        success = download_uniprot_json(pid, json_path)
        if not success:
            logging.error(f"Failed to download UniProt JSON for {pid}")
            return pid, "uniprot_json_failed"

    with open(json_path, "r") as f:
        data = json.load(f)

    af_id = extract_alphafold_id(data)
    pdb = None

    if af_id:
        logging.info(f"AlphaFold ID for {pid} is {af_id}")
        pdb = download_alphafold_pdb(af_id, output_folder)
    else:
        logging.warning(f"No AlphaFold ID found in JSON for {pid}")

    if not pdb:
        logging.info(f"Attempting fallback: using UniProt ID {pid} to download structure")
        pdb = download_alphafold_pdb(pid, output_folder)

    if pdb:
        logging.info(f"Downloaded structure for {pid}")
        return pid, pdb
    else:
        logging.error(f"Failed to download structure for {pid}")
        return pid, "pdb_failed"


def download_structures_from_fasta(file_in, output_folder="pdb_files", max_workers=16):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    protein_ids = extract_protein_ids_from_fasta(file_in)
    downloaded = {}

    # These are all independent network I/O calls (UniProt + AlphaFoldDB),
    # so fan them out across threads instead of downloading one protein
    # at a time.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_process_protein, pid, output_folder) for pid in protein_ids]
        for future in as_completed(futures):
            pid, status = future.result()
            downloaded[pid] = status

    return downloaded