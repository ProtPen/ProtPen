# protepen/eggnog.py
import os
import subprocess
import pandas as pd


def run_eggnog_mapper(input_fasta, output_dir, output_prefix, emapper_path, cpu=None):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_path = os.path.join(output_dir, output_prefix)
    command = f"{emapper_path} -i {input_fasta} -m diamond -m mmseqs -o {output_path}"
    if cpu:
        command += f" --cpu {cpu}"
    subprocess.run(command, shell=True, check=True, env=os.environ)


def convert_to_tsv(output_dir, output_prefix, output_file):
    annotation_file = os.path.join(output_dir, f"{output_prefix}.emapper.annotations")
    data = []

    with open(annotation_file, "r") as f:
        for line in f:
            if not line.startswith("#"):
                data.append(line.strip().split("\t"))

    columns = [
        "query",
        "seed_ortholog",
        "evalue",
        "score",
        "eggNOG_OGs",
        "max_annot_lvl",
        "COG_category",
        "Description",
        "Preferred_name",
        "GOs",
        "EC",
        "KEGG_ko",
        "KEGG_Pathway",
        "KEGG_Module",
        "KEGG_Reaction",
        "KEGG_rclass",
        "BRITE",
        "KEGG_TC",
        "CAZy",
        "BiGG_Reaction",
        "PFAMs",
    ]
    df = pd.DataFrame(data, columns=columns)
    df.to_csv(output_file, index=False, sep="\t")
