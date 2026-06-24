#!/usr/bin/env python3
# protpen/cli_enrich.py

# usage: python -m protpen.cli_enrich -i input.tsv -o enriched_output.tsv

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from protpen import enrich_utils


def run_enrichment_pipeline(input_tsv, output_tsv, max_workers=16):
    # Step 1: Extract all unique (pdb_id, chain_id) pairs from Foldseek target column
    pdb_chain_pairs = set()
    with open(input_tsv, newline="") as infile:
        reader = csv.DictReader(infile, delimiter="\t")
        for row in reader:
            target_field = row.get("target", "")
            for token in target_field.split("||"):
                if token:
                    (pdb_id, chain_id), reason = enrich_utils.parse_pdb_chain(token)
                    if pdb_id and chain_id:
                        pdb_chain_pairs.add((pdb_id, chain_id))
                    else:
                        print(f"[WARN] Skipping unparsable token: {token} — {reason}")

    print(f"[INFO] Found {len(pdb_chain_pairs)} unique PDB+chain combinations.")

    if not pdb_chain_pairs:
        print("[ERROR] No valid PDB+chain pairs extracted. Exiting.")
        return

    # Step 2: Map (pdb_id, chain_id) → UniProt ID via RCSB GraphQL.
    # Each lookup is an independent network call, so run them concurrently.
    pair_to_uniprot = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pair = {
            executor.submit(enrich_utils.get_uniprot_id_from_rcsb, pdb_id, chain_id): (
                pdb_id,
                chain_id,
            )
            for pdb_id, chain_id in sorted(pdb_chain_pairs)
        }
        for future in as_completed(future_to_pair):
            pdb_id, chain_id = future_to_pair[future]
            uniprot_id = future.result()
            if uniprot_id:
                pair_to_uniprot[(pdb_id, chain_id)] = uniprot_id
            else:
                print(f"[WARN] No UniProt ID found for {pdb_id}_{chain_id}")

    print(f"[INFO] Retrieved UniProt IDs for {len(pair_to_uniprot)} pairs.")

    # Step 3: Retrieve UniProt metadata for each unique UniProt ID concurrently.
    unique_uniprot_ids = sorted(set(pair_to_uniprot.values()))
    uniprot_info_cache = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {
            executor.submit(enrich_utils.get_uniprot_info, uniprot_id): uniprot_id
            for uniprot_id in unique_uniprot_ids
        }
        for future in as_completed(future_to_id):
            uniprot_id = future_to_id[future]
            uniprot_info_cache[uniprot_id] = future.result()

    pair_to_info = {
        pair: uniprot_info_cache[uniprot_id]
        for pair, uniprot_id in pair_to_uniprot.items()
    }

    # Step 4: Fallback for any pair that couldn't be resolved
    for pair in pdb_chain_pairs:
        if pair not in pair_to_info:
            pair_to_info[pair] = {
                "description": "n/a",
                "interpro": "n/a",
                "supfam": "n/a",
            }

    # Step 5: Enrich and write TSV
    print(f"[INFO] Writing enriched TSV to {output_tsv}")
    enrich_utils.enrich_tsv(input_tsv, output_tsv, pair_to_info=pair_to_info)
    print("[INFO] Enrichment complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Enrich Foldseek TSVs using PDB+chain-specific UniProt metadata from RCSB GraphQL."
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Input Foldseek TSV (with target column)"
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output TSV with UniProt enrichment"
    )
    parser.add_argument(
        "--max_workers",
        type=int,
        default=16,
        help="Number of concurrent lookup threads",
    )
    args = parser.parse_args()

    run_enrichment_pipeline(args.input, args.output, max_workers=args.max_workers)


if __name__ == "__main__":
    main()
