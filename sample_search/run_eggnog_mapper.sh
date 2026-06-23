#!/bin/bash -l

# The name of your job; be descriptive
#SBATCH --job-name=run_egg_sample

# Where to save the output and error messages for your job?
# %x will fill in your job name, %j will fill in your job ID
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

#SBATCH --nodes=1

# How many tasks does your job need?
# This option advises the Slurm controller that job steps run within the
# allocation will launch a maximum of number tasks and to provide for
# sufficient resources. Defaults to one CPU per task.
#SBATCH --ntasks=1

# How much time does your job need to run?
# Format: Days-Hours:Minutes:Seconds
# Max: 5 days (tier3), 1 day (debug)
#SBATCH --time=0-11:00:00

# How much memory per CPU: MB=m (default), GB=g, TB=t
#SBATCH --cpus-per-task=8    
#SBATCH --mem=128G 

# Your slurm account (created when you fill out the questionnaire)
#SBATCH --account=proteome

# The partition to run your job on.
# Debug is for troubleshooting your code and getting your job to run.
# When your job runs successfully, switch to tier3.
# We reserve the right to kill jobs running on debug without warning if we need
# to debug with or train a researcher.
#SBATCH --partition=debug 

source /shared/rc/proteome/protpen/protpen_venv/bin/activate
spack load diamond@2.1.7/uoz3ai4

ROOT_DIR="/shared/rc/proteome/protpen/ProtPen"
INPUT_FASTA="sample_proteins.fasta"       # Place this file in sample_search/
OUTPUT_PREFIX="search_run"
EGGNOG_DIR="eggnog_output"
EGGNOG_TSV="eggnog_results.tsv"
EMAPPER_PATH="/shared/rc/proteome/BASIL/eggnog-mapper/emapper.py" # Path to EggNOG-mapper's emapper.py

python -m protpen.cli_eggnog \
  -i "${INPUT_FASTA}" \
  -o "${EGGNOG_DIR}" \
  -p "${OUTPUT_PREFIX}" \
  -t "${EGGNOG_TSV}" \
  --emapper_path "${EMAPPER_PATH}" \
  --cpu "${SLURM_CPUS_PER_TASK:-8}"
if [ $? -ne 0 ]; then
    echo "EggNOG-mapper failed."
    exit 1
