# protpen/enrich_utils.py
import csv
import requests
import time
import argparse
import os
import json
import re
from itertools import islice

# ----------------------------
# UniProt Metadata Functions
# ----------------------------


def download_uniprot_json(uniprot_id, output_file):
    url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.json"
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_file, "w") as file_object:
            json.dump(response.json(), file_object, sort_keys=True, indent=2)
        print(f"Downloaded UniProt JSON for {uniprot_id}")
    else:
        print(f"Failed to download UniProt JSON for {uniprot_id}")


def get_uniprot_info(uniprot_id, json_dir="uniprot_json_enrich"):
    # exist_ok=True avoids a race when called concurrently from multiple
    # threads (cli_enrich.py now fetches metadata for several UniProt IDs
    # in parallel) where two threads pass the exists() check before either
    # has created the directory.
    os.makedirs(json_dir, exist_ok=True)
    output_file = os.path.join(json_dir, f"{uniprot_id}.json")
    if not os.path.exists(output_file):
        download_uniprot_json(uniprot_id, output_file)
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            data = json.load(f)
    else:
        print(f"Unable to retrieve JSON for {uniprot_id}")
        return {"description": "n/a", "interpro": "n/a", "supfam": "n/a"}

    info = {"description": "", "interpro": [], "supfam": []}
    try:
        info["description"] = data["proteinDescription"]["recommendedName"]["fullName"][
            "value"
        ]
    except KeyError:
        try:
            submission_names = data["proteinDescription"].get("submissionNames", [])
            if submission_names:
                info["description"] = submission_names[0]["fullName"]["value"]
        except (KeyError, IndexError):
            info["description"] = ""
    if not info["description"]:
        info["description"] = "n/a"

    for ref in data.get("uniProtKBCrossReferences", []):
        db = ref.get("database", "").upper()
        entry_name = ""
        for prop in ref.get("properties", []):
            if prop.get("key") == "EntryName":
                entry_name = prop.get("value")
                break
        if not entry_name:
            entry_name = ref.get("id", "")

        if db == "INTERPRO":
            info["interpro"].append(entry_name)
        elif db == "SUPFAM":
            info["supfam"].append(entry_name)

    info["interpro"] = ", ".join(info["interpro"]) if info["interpro"] else "n/a"
    info["supfam"] = ", ".join(info["supfam"]) if info["supfam"] else "n/a"
    return info


# ----------------------------
# RCSB Utilities
# ----------------------------


def parse_pdb_chain(raw_id, verbose_log=False):
    """
    Extract (pdb_id, chain_id) from Foldseek target entries like:
    '1jwb-assembly1.cif.gz_D-2' → ('1jwb', 'D')
    '5wva-assembly1.cif.gz_A' → ('5wva', 'A')

    Returns:
        (pdb_id, chain_id), reason (str or None)
    """
    raw_id = raw_id.strip()

    if "_" not in raw_id:
        return (None, None), "malformed (missing '_')"
    if "-assembly" not in raw_id or ".cif.gz" not in raw_id:
        return (None, None), "missing 'assemblyX.cif.gz'"

    # Match format with optional '-2', '-3', etc. after chain ID
    match = re.match(
        r"([0-9a-zA-Z]{4})-assembly\d+\.cif\.gz_([A-Za-z0-9]+)(-\d+)?$", raw_id
    )
    if match:
        pdb_id = match.group(1).lower()
        chain_id = match.group(2)
        return (pdb_id, chain_id), None
    else:
        return (None, None), "regex match failed"


def get_uniprot_id_from_rcsb(pdb_id, chain_id):
    url = "https://data.rcsb.org/graphql"
    query = f"""
    {{
      entries(entry_ids: ["{pdb_id.upper()}"]) {{
        polymer_entities {{
          rcsb_polymer_entity_container_identifiers {{
            auth_asym_ids
            reference_sequence_identifiers {{
              database_name
              database_accession
            }}
          }}
        }}
      }}
    }}
    """
    try:
        response = requests.post(url, json={"query": query})
        response.raise_for_status()
        data = response.json()
        entities = data["data"]["entries"][0]["polymer_entities"]
        for entity in entities:
            chains = entity["rcsb_polymer_entity_container_identifiers"].get(
                "auth_asym_ids", []
            )
            refs = entity["rcsb_polymer_entity_container_identifiers"].get(
                "reference_sequence_identifiers", []
            )
            if chain_id in chains:
                for ref in refs:
                    if ref["database_name"] == "UniProt":
                        return ref["database_accession"]
    except Exception as e:
        print(f"[ERROR] Failed to query RCSB for {pdb_id}_{chain_id}: {e}")
    return None


# ----------------------------
# Enrichment Function
# ----------------------------


def enrich_tsv(input_tsv, output_tsv, pair_to_info=None, log_failed=True):
    """
    Enriches Foldseek TSV using RCSB and UniProt metadata.

    If pair_to_info is provided, skips RCSB/UniProt API calls and uses it directly.
    Logs failures unless explicitly disabled.
    """
    failed_log = []

    with (
        open(input_tsv, newline="") as infile,
        open(output_tsv, "w", newline="") as outfile,
    ):
        reader = csv.DictReader(infile, delimiter="\t")
        new_fields = ["UniProt_Description", "UniProt_InterPro", "UniProt_SUPFAM"]
        fieldnames = reader.fieldnames + new_fields
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for row in reader:
            target_field = row.get("target", "")
            descs, interpros, supfams = [], [], []

            for token in target_field.split("||"):
                if not token:
                    continue

                (pdb_id, chain_id), reason = parse_pdb_chain(token)
                if not pdb_id or not chain_id:
                    print(f"[WARN] Could not parse token: {token} — {reason}")
                    failed_log.append({"token": token, "reason": reason})
                    info = {"description": "n/a", "interpro": "n/a", "supfam": "n/a"}

                elif pair_to_info:
                    info = pair_to_info.get(
                        (pdb_id, chain_id),
                        {"description": "n/a", "interpro": "n/a", "supfam": "n/a"},
                    )
                    if info["description"] == "n/a":
                        failed_log.append(
                            {
                                "token": token,
                                "reason": f"uniprot_info_missing ({pdb_id}_{chain_id})",
                            }
                        )

                else:
                    uniprot_id = get_uniprot_id_from_rcsb(pdb_id, chain_id)
                    if not uniprot_id:
                        print(f"[WARN] No UniProt ID for {pdb_id}_{chain_id}")
                        failed_log.append(
                            {"token": token, "reason": f"uniprot_not_found"}
                        )
                        info = {
                            "description": "n/a",
                            "interpro": "n/a",
                            "supfam": "n/a",
                        }
                    else:
                        info = get_uniprot_info(uniprot_id)
                        if info["description"] == "n/a":
                            print(
                                f"[WARN] UniProt ID {uniprot_id} retrieved but no metadata found"
                            )
                            failed_log.append(
                                {
                                    "token": token,
                                    "reason": f"uniprot_no_metadata ({uniprot_id})",
                                }
                            )

                descs.append(info.get("description", "n/a"))
                interpros.append(info.get("interpro", "n/a"))
                supfams.append(info.get("supfam", "n/a"))

            row["UniProt_Description"] = "||".join(descs)
            row["UniProt_InterPro"] = "||".join(interpros)
            row["UniProt_SUPFAM"] = "||".join(supfams)
            writer.writerow(row)

    if log_failed and failed_log:
        # Save failure log to logs/ directory
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(output_tsv))[0]
        failed_log_file = os.path.join(log_dir, f"{base_name}_failures.log")

        with open(failed_log_file, "w") as f:
            for entry in failed_log:
                f.write(json.dumps(entry) + "\n")
        print(f"[INFO] Wrote {len(failed_log)} failed lookups to {failed_log_file}")


# ----------------------------
# Optional CLI
# ----------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enrich Foldseek TSV results with UniProt metadata from PDB+chain matches."
    )
    parser.add_argument("-i", "--input", required=True, help="Input TSV from Foldseek")
    parser.add_argument("-o", "--output", required=True, help="Output enriched TSV")
    args = parser.parse_args()

    enrich_tsv(args.input, args.output)
