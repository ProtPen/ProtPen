# ProtPen: Protein Function Prediction Pipeline

This repository contains a pipeline for predicting and analyzing protein function using structure- and sequence-based methods. ProtPen integrates EggNOG-mapper, AlphaFold structure retrieval, Foldseek structural searches, and result enrichment to investigate differentially abundant proteins of unknown function in a proteomic dataset.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Pipeline Workflow](#pipeline-workflow)
- [Scripts](#scripts)
- [Usage](#usage)
- [Output](#output)
- [Modular Design](#modular-design-and-extensibility)

## Overview

ProtPen takes a FASTA file containing UniProt protein identifiers as input, retrieves AlphaFold PDB structures, performs EggNOG-mapper and Foldseek searches, filters and consolidates Foldseek results, enriches them with UniProt annotations, and merges the outputs for downstream functional interpretation.

## Installation

The pipeline is intended to run on a Unix-based HPC system using SLURM and virtual environments.

### Prerequisites

- Python 3.x
- SLURM scheduler
- EggNOG-mapper v2
- Foldseek
- `psutil` ≥ 6.0
- Python packages: `pandas`, `requests`, `biopython`, `pytest`

### Clone the Repository

```bash
git clone https://github.com/dmath21/ProtPen.git
```
## Pipeline Workflow

1. **Run EggNOG-mapper** (`cli_eggnog.py`)  
   Annotates proteins using the EggNOG orthology database.

2. **Download AlphaFold PDB files** (`cli_download.py`)  
   Retrieves AlphaFold-predicted structures from UniProt based on FASTA input.

3. **Run Foldseek search** (`cli_foldseek.py`)  
   Compares AlphaFold structures to a preprocessed Foldseek database.

4. **Filter and consolidate Foldseek results** (`cli_consolidate_foldseek.py`)  
   Keeps top hits per query and filters based on the input FASTA file.

5. **Enrich Foldseek results** (`cli_enrich.py`)  
   Adds UniProt annotations to Foldseek hits using PDB-to-UniProt mapping.

6. **Merge EggNOG and Foldseek results** (`cli_merge.py`)  
   Joins both result tables on query ID for final annotation output.

## Scripts

| Script                         | Description                                              |
|--------------------------------|----------------------------------------------------------|
| `cli_eggnog.py`                | Runs EggNOG-mapper with UniProt ID input                 |
| `cli_download.py`              | Downloads AlphaFold PDB files from UniProt              |
| `cli_foldseek.py`              | Runs Foldseek structural search on PDBs                 |
| `cli_consolidate_foldseek.py`  | Filters and consolidates Foldseek search results        |
| `cli_enrich.py`                | Enriches Foldseek results with UniProt metadata         |
| `cli_merge.py`                 | Merges enriched Foldseek and EggNOG-mapper results      |

## Usage

Example SLURM-based workflow for a sample dataset:

```bash
# Step 1: EggNOG-mapper
sbatch run_eggnog_mapper.sh

# Step 2: Download AlphaFold PDBs
sbatch run_download_alphafold.sh

# Step 3: Run Foldseek search
sbatch run_foldseek.sh

# Step 4: Consolidate Foldseek results
sbatch run_consolidate.sh

# Step 5: Enrich Foldseek results
sbatch run_enrich.sh

# Step 6: Merge Foldseek and EggNOG-mapper results
sbatch run_merge.sh
```

## Output

- `merged_annotations.tsv`: Final merged annotations from EggNOG and Foldseek.
- `enriched_foldseek_results.tsv`: Foldseek results with added UniProt metadata.
- `consolidated_foldseek_results.tsv`: Filtered and top Foldseek matches.
- `eggnog_results.tsv`: Raw output from EggNOG-mapper.
- AlphaFold `.pdb` files downloaded for input UniProt IDs.
  
## Modular Design and Extensibility

ProtPen is designed as a **modular pipeline**, where each analysis step is implemented as an independent module that can be added, removed, or replaced without modifying the core codebase. Modules communicate exclusively through file-based inputs and outputs (primarily TSV and FASTA files), allowing users to customize the workflow for different datasets or analysis goals.

### What Is a Module?

Each ProtPen module:

- Performs a single logical task (e.g., annotation, structure search, enrichment)
- Is implemented as a Python module within the `protpen/` package
- Exposes a command-line interface (CLI) via a `cli_*.py` wrapper
- Accepts standardized input files and produces standardized output files

The overall workflow is orchestrated by a shell script (e.g., `run_pipeline.sh`) that sequentially calls these CLI modules. There are no hard-coded dependencies between modules beyond expected input/output formats.

### Removing a Module

To remove a module from the pipeline, simply delete or comment out the corresponding CLI call in your pipeline script. Ensure that downstream steps do not require the removed module’s output.

**Example: Skipping Foldseek enrichment**

Remove the following line from your pipeline script:

```bash
python -m protpen.cli_enrich -i consolidated_foldseek_results.tsv -o enriched_foldseek_results.tsv
```
