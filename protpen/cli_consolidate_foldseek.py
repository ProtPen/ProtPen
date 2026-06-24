# protpen/cli_consolidate_foldseek.py
import argparse
from protpen.foldseek_utils import consolidate_foldseek_results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", help="Directory with Foldseek .tsv files")
    parser.add_argument("output_file", help="Output consolidated .tsv file")
    parser.add_argument("query_fasta", help="FASTA file with query protein IDs")
    parser.add_argument("--top_x", type=int, default=5, help="Top X hits per query (default: 5)")
    parser.add_argument("--max_workers", type=int, default=8, help="Number of concurrent file-reading threads")
    args = parser.parse_args()

    df = consolidate_foldseek_results(args.input_dir, args.query_fasta, args.top_x, max_workers=args.max_workers)
    if not df.empty:
        df.to_csv(args.output_file, sep="\t", index=False)
        print(f"Saved {len(df)} entries to {args.output_file}")
    else:
        print("No valid results found. No output written.")

if __name__ == "__main__":
    main()
