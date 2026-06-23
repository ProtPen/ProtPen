#!/bin/bash -l

##############################################
# SLURM Job Configuration
##############################################

#SBATCH --job-name=sample_search_protpen          # Descriptive job name
#SBATCH --output=logs/%x_%j.out                   # Standard output log (%x = job name, %j = job ID)
#SBATCH --error=logs/%x_%j.err                    # Standard error log
#SBATCH --nodes=1                                 # Number of nodes requested
#SBATCH --ntasks=1                                # Number of tasks (1 = serial job)
#SBATCH --cpus-per-task=16                        # Number of CPU cores
#SBATCH --mem=50G                                 # Total memory required
#SBATCH --time=2:00:00                            # Maximum walltime (hh:mm:ss)
#SBATCH --account=proteome                        # SLURM account name
#SBATCH --partition=debug                         # SLURM partition (queue)

##############################################
# Environment Setup
##############################################

# Activate the Python virtual environment where ProtPen is installed
source /shared/rc/proteome/protpen/protpen_venv/bin/activate

# Load DIAMOND for EggNOG-mapper functionality
spack load diamond@2.1.7/uoz3ai4

# Activate the Spack environment for Foldseek
spack env activate default-genomics-x86_64-24120601

# Ensure Python can locate the ProtPen module
export PYTHONPATH="/shared/rc/proteome/protpen/ProtPen:$PYTHONPATH"

##############################################
# File and Directory Paths
##############################################

INPUT_FASTA="sample_proteins.fasta"                   # Input FASTA with UniProt-style protein headers
EGGNOG_DIR="eggnog_output"                            # Output directory for EggNOG-mapper
EGGNOG_TSV="eggnog_results.tsv"                       # Final EggNOG-mapper TSV file
PDB_DIR="sample_pdb"                                  # Folder to store downloaded AlphaFold PDBs
FOLDSEEK_OUT="sample_foldseek_output"                 # Output directory for raw Foldseek results
FOLDSEEK_TMP="foldseek_tmp"                           # Temporary working directory for Foldseek
FOLDSEEK_CONSOLIDATED="consolidated_foldseek_results.tsv"  # Filtered and ranked Foldseek output
FOLDSEEK_ENRICHED="enriched_foldseek_results.tsv"     # Foldseek results enriched with UniProt info
MERGED_OUTPUT="merged_annotations.tsv"                # Final merged annotations from EggNOG and Foldseek
FOLDSEEK_DB="/shared/rc/proteome/protpen/run_pipeline/pdb" # Path to pre-built Foldseek structure database
EMAPPER_PATH="/shared/rc/proteome/BASIL/eggnog-mapper/emapper.py" # Path to EggNOG-mapper's emapper.py
TOTAL_CPUS="${SLURM_CPUS_PER_TASK:-16}"               # Total CPUs allocated by SBATCH --cpus-per-task

# EggNOG-mapper (Step 1) and Foldseek (Step 3) are both CPU-bound and run
# concurrently (EggNOG in the background while the Foldseek branch
# proceeds), so the CPU budget is split between them rather than letting
# each claim all of it. In practice Foldseek is the long pole by far, so
# EggNOG gets just 1 CPU and Foldseek gets the rest. The other steps
# (download/consolidate/enrich) are I/O-bound and run sequentially within
# the Foldseek branch, so they get the full CPU count as a thread-pool size.
EGGNOG_CPUS=1
FOLDSEEK_THREADS=$(( TOTAL_CPUS - EGGNOG_CPUS ))
if [ "$FOLDSEEK_THREADS" -lt 1 ]; then FOLDSEEK_THREADS=1; fi
MAX_WORKERS="$TOTAL_CPUS"                             # Thread pool size for the I/O-bound download/consolidate/enrich steps

# Create necessary directories if they do not exist
mkdir -p logs "$EGGNOG_DIR" "$PDB_DIR" "$FOLDSEEK_OUT" "$FOLDSEEK_TMP"
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Pipeline initialization complete."

##############################################
# Step 1 and Steps 2-5 are independent of each other (EggNOG-mapper only
# needs the input FASTA; the Foldseek branch doesn't need EggNOG output
# until the final merge). EggNOG-mapper's runtime doesn't scale with CPU
# count, so run it in the background while the Foldseek branch proceeds
# on the rest of the allocated CPUs, and only join them before Step 6.
##############################################

echo "$(date +"[%Y-%m-%d %H:%M:%S]") Step 1: Running EggNOG-mapper (in background, using $EGGNOG_CPUS CPUs)..."
python -m protpen.cli_eggnog -i "$INPUT_FASTA" -o "$EGGNOG_DIR" -p "eggnog" -t "$EGGNOG_TSV" --emapper_path "$EMAPPER_PATH" --cpu "$EGGNOG_CPUS" \
  > logs/eggnog_step.log 2>&1 &
EGGNOG_PID=$!

##############################################
# Step 2: Download AlphaFold Structures for Input Proteins
##############################################
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Step 2: Downloading AlphaFold PDBs (using $MAX_WORKERS workers)..."
python -m protpen.cli_download "$INPUT_FASTA" --output_folder "$PDB_DIR" --max_workers "$MAX_WORKERS"
if [ $? -ne 0 ]; then echo "Download failed." && exit 1; fi
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Download completed."

##############################################
# Step 3: Run Foldseek for Structure Similarity Search
##############################################
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Step 3: Running Foldseek (using $FOLDSEEK_THREADS threads)..."
python -m protpen.cli_foldseek "$PDB_DIR" "$FOLDSEEK_OUT" --db "$FOLDSEEK_DB" --tmp_dir "$FOLDSEEK_TMP" --threads "$FOLDSEEK_THREADS"
if [ $? -ne 0 ]; then echo "Foldseek failed." && exit 1; fi
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Foldseek structural search completed."

##############################################
# Step 4: Consolidate Foldseek Results (Filter & Rank Top Hits)
##############################################
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Step 4: Consolidating Foldseek results (using $MAX_WORKERS workers)..."
python -m protpen.cli_consolidate_foldseek "$FOLDSEEK_OUT" "$FOLDSEEK_CONSOLIDATED" "$INPUT_FASTA" --top_x 5 --max_workers "$MAX_WORKERS"
if [ $? -ne 0 ]; then echo "Consolidation failed." && exit 1; fi
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Consolidation completed."

##############################################
# Step 5: Enrich Foldseek Output with UniProt Annotations
##############################################
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Step 5: Enriching Foldseek results (using $MAX_WORKERS workers)..."
python -m protpen.cli_enrich -i "$FOLDSEEK_CONSOLIDATED" -o "$FOLDSEEK_ENRICHED" --max_workers "$MAX_WORKERS"
if [ $? -ne 0 ]; then echo "Enrichment failed." && exit 1; fi
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Enrichment completed."

##############################################
# Wait for the background EggNOG-mapper job before merging
##############################################
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Waiting for EggNOG-mapper (Step 1) to finish..."
wait "$EGGNOG_PID"
if [ $? -ne 0 ]; then echo "EggNOG-mapper failed (see logs/eggnog_step.log)." && exit 1; fi
echo "$(date +"[%Y-%m-%d %H:%M:%S]") EggNOG-mapper completed."

##############################################
# Step 6: Merge EggNOG and Foldseek Annotations
##############################################
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Step 6: Merging EggNOG and Foldseek results..."
python -m protpen.cli_merge "$EGGNOG_TSV" "$FOLDSEEK_ENRICHED" "$MERGED_OUTPUT"
if [ $? -ne 0 ]; then echo "Merge failed." && exit 1; fi
echo "$(date +"[%Y-%m-%d %H:%M:%S]") Merge completed."

echo "$(date +"[%Y-%m-%d %H:%M:%S]") Pipeline completed successfully."
