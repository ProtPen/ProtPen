# protpen/cli_merge.py
import argparse
import csv
from protpen.merge_utils import read_tsv, merge_data


def main():
    parser = argparse.ArgumentParser(
        description="Merge EggNOG and Foldseek TSVs, filtering EggNOG by Foldseek queries."
    )
    parser.add_argument("eggnog", help="Path to EggNOG TSV file")
    parser.add_argument("foldseek", help="Path to Foldseek TSV file")
    parser.add_argument("output", help="Path for merged TSV output")
    args = parser.parse_args()

    eggnog_data, eggnog_headers = read_tsv(args.eggnog)
    foldseek_data, foldseek_headers = read_tsv(args.foldseek)

    merged_headers, merged_rows = merge_data(
        eggnog_data, eggnog_headers, foldseek_data, foldseek_headers
    )

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=merged_headers, delimiter="\t")
        writer.writeheader()
        writer.writerows(merged_rows)

    print(f"Merged {len(merged_rows)} rows written to {args.output}")


if __name__ == "__main__":
    main()
