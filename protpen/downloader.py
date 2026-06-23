# protpen/downloader.py
import requests
import os
import json
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def _request_with_retry(method, url, retries=5, backoff=1.0, **kwargs):
    """
    Calls requests.get/requests.head with retries on transient connection
    failures (dropped connections, timeouts, 429/5xx). Now that requests
    fan out across many threads instead of one at a time, occasional
    remote disconnects from UniProt/AlphaFoldDB under load are expected
    and shouldn't take down the whole batch.
    """
    func = requests.get if method == "get" else requests.head
    last_exc = None
    for attempt in range(retries):
        try:
            response = func(url, **kwargs)
        except requests.exceptions.RequestException as exc:
            last_exc = exc
        else:
            if response.status_code not in (429, 500, 502, 503, 504):
                return response
            last_exc = None
        if attempt < retries - 1:
            time.sleep(backoff * (2 ** attempt))
    if last_exc:
        raise last_exc
    return response


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
    try:
        response = _request_with_retry("get", url)
    except requests.exceptions.RequestException as exc:
        logging.error(f"UniProt request failed for {uniprot_id} after retries: {exc}")
        return False
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


def download_alphafold_pdb(alphafold_id, output_folder, batch_size=10, max_version=100):
    """
    Finds and downloads the highest-versioned AlphaFoldDB structure for
    alphafold_id. The actual "latest" version number varies over time and
    across entries (e.g. v4 vs v6), so instead of guessing a version or
    scanning 1..100 sequentially (slow, and pathological for IDs with no
    structure at all), versions are probed in small concurrent batches and
    we stop at the first batch containing a hit.
    """
    pdb_path = os.path.join(output_folder, f"{alphafold_id}.pdb")
    base_url = f"https://alphafold.ebi.ac.uk/files/AF-{alphafold_id}-F1-model_v"

    def check_version(version):
        url = base_url + str(version) + ".pdb"
        try:
            response = _request_with_retry("head", url)
        except requests.exceptions.RequestException:
            return None
        return version if response.status_code == 200 else None

    found_version = None
    start = 1
    while start <= max_version:
        batch = range(start, min(start + batch_size, max_version + 1))
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            hits = [v for v in executor.map(check_version, batch) if v is not None]
        if hits:
            found_version = max(hits)
            break
        start += batch_size

    if found_version is None:
        logging.warning(f"No structure found for {alphafold_id} in versions 1-{max_version}.")
        return None

    url = base_url + str(found_version) + ".pdb"
    logging.info(f"Found structure for {alphafold_id} (v{found_version}). Downloading...")
    try:
        response = _request_with_retry("get", url)
    except requests.exceptions.RequestException as exc:
        logging.error(f"Failed to download structure for {alphafold_id} after retries: {exc}")
        return None
    os.makedirs(output_folder, exist_ok=True)
    with open(pdb_path, "wb") as f:
        f.write(response.content)
    return pdb_path


def _process_protein(pid, output_folder):
    try:
        return _process_protein_impl(pid, output_folder)
    except Exception as exc:
        # A single protein's network failure shouldn't take down the whole
        # batch -- log it, mark it failed, and let the rest finish.
        logging.error(f"Unexpected error processing {pid}: {exc}")
        return pid, "error"


def _process_protein_impl(pid, output_folder):
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
        future_to_pid = {executor.submit(_process_protein, pid, output_folder): pid for pid in protein_ids}
        for future in as_completed(future_to_pid):
            pid = future_to_pid[future]
            try:
                pid, status = future.result()
            except Exception as exc:
                logging.error(f"Unexpected error processing {pid}: {exc}")
                status = "error"
            downloaded[pid] = status

    return downloaded