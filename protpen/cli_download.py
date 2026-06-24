# protpen/cli_download.py

import argparse
from protpen.downloader import download_structures_from_fasta

def main():
    parser = argparse.ArgumentParser(description="Download AlphaFold PDB files from UniProt FASTA.")
    parser.add_argument("file_in", help="Input FASTA file with UniProt IDs")
    parser.add_argument("--output_folder", default="pdb_files", help="Folder to save PDB files")
    parser.add_argument("--max_workers", type=int, default=16, help="Number of concurrent download threads")
    args = parser.parse_args()

    result = download_structures_from_fasta(args.file_in, args.output_folder, max_workers=args.max_workers)
    for pid, status in result.items():
        print(f"{pid}: {status}")

if __name__ == "__main__":
    main()

# python protpen/cli_download.py input.fasta --output_folder pdbs
