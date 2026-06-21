#protpen/foldseek.py
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

def _run_one(pdb_file, pdb_dir, output_dir, tmp_dir, db, isolate_tmp=False):
    pdb_path = os.path.join(pdb_dir, pdb_file)
    output_file = os.path.join(output_dir, f"{os.path.splitext(pdb_file)[0]}.tsv")
    # When running concurrently, each job needs its own tmp subdir —
    # foldseek's tmp directory layout isn't safe to share between
    # simultaneous easy-search invocations.
    job_tmp_dir = os.path.join(tmp_dir, os.path.splitext(pdb_file)[0]) if isolate_tmp else tmp_dir
    if isolate_tmp:
        os.makedirs(job_tmp_dir, exist_ok=True)
    command = [
        "foldseek",
        "easy-search",
        pdb_path,
        db,
        output_file,
        job_tmp_dir,
        "--format-mode", "4"
    ]

    print(f"Running Foldseek for {pdb_file}...")
    try:
        subprocess.run(command, check=True)
        print(f"Results saved to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error running Foldseek for {pdb_file}: {e}")


def run_foldseek_search(pdb_dir, output_dir, tmp_dir="tmp", db="pdb", max_workers=1):
    """
    Runs Foldseek easy-search for all .pdb files in pdb_dir.

    Args:
        pdb_dir (str): Input directory containing .pdb files.
        output_dir (str): Directory to write output .tsv files.
        tmp_dir (str): Temporary directory for Foldseek processing.
        db (str): Database to search against (default: "pdb").
        max_workers (int): Number of Foldseek searches to run concurrently.
            Foldseek itself already scales well with --threads for a single
            search, so this should only be raised above 1 when individual
            searches (e.g. one small structure each) don't saturate all
            available CPUs on their own; keep total concurrent threads used
            by foldseek within the machine's CPU budget.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    pdb_files = [f for f in os.listdir(pdb_dir) if f.endswith(".pdb")]
    if not pdb_files:
        print("No PDB files found in the specified directory.")
        return

    if max_workers <= 1:
        for pdb_file in pdb_files:
            _run_one(pdb_file, pdb_dir, output_dir, tmp_dir, db)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(
                lambda f: _run_one(f, pdb_dir, output_dir, tmp_dir, db, isolate_tmp=True), pdb_files
            ))
