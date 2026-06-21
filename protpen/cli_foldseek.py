# protpen/cli_foldseek.py
import argparse
from protpen.foldseek import run_foldseek_search

def main():
    parser = argparse.ArgumentParser(description="Run Foldseek search on PDB files in a directory.")
    parser.add_argument("pdb_dir", help="Directory containing PDB files.")
    parser.add_argument("output_dir", help="Directory to save output TSV files.")
    parser.add_argument("--tmp_dir", default="tmp", help="Temporary directory for Foldseek.")
    parser.add_argument("--db", default="pdb", help="Database to search against.")
    parser.add_argument("--max_workers", type=int, default=1,
                         help="Number of Foldseek searches to run concurrently "
                              "(only helps if individual searches don't saturate all CPUs alone).")
    args = parser.parse_args()

    run_foldseek_search(args.pdb_dir, args.output_dir, args.tmp_dir, args.db, max_workers=args.max_workers)

if __name__ == "__main__":
    main()
