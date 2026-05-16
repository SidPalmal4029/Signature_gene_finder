import os
import re
import shutil
import subprocess


# -----------------------------
# SANITIZE GENOME NAME
# -----------------------------
def sanitize_name(filename):
    name = os.path.splitext(filename)[0]

    # replace all non-safe characters
    name = re.sub(r"[^\w\.]+", "_", name)

    # collapse multiple underscores
    name = re.sub(r"_+", "_", name)

    return name.strip("_")


# -----------------------------
# CREATE POOLED STRUCTURE
# -----------------------------
def create_pool_dirs(base_dir):

    pool_base = os.path.join(base_dir, "pooled")

    mapping = {
        "protein.faa": "faa",
        "genome.gbk": "gbk",
        "genome.gff": "gff",
        "cds.fna": "cds",
        "genome.fna": "genome",
        "rna.fna": "rna",
        "statistics.txt": "stats",
        "application.log": "logs",
        "pseudogene_summary.tsv": "pseudogene"
    }

    pool_dirs = {}

    for fname, folder in mapping.items():
        path = os.path.join(pool_base, folder)
        os.makedirs(path, exist_ok=True)
        pool_dirs[fname] = path

    return pool_dirs


# -----------------------------
# RUN DFAST PER GENOME
# -----------------------------
def run_single_dfast(infile, genome_id, outdir, threads):

    cmd = [
        "dfast",
        "--genome", infile,
        "--out", outdir,
        "--cpu", str(threads),
        "--force",
        "--locus_tag_prefix", genome_id
    ]

    subprocess.run(cmd, check=True)


# -----------------------------
# COPY OUTPUTS TO POOL
# -----------------------------
def collect_outputs(outdir, genome_id, pool_dirs):

    for fname, target_dir in pool_dirs.items():

        src = os.path.join(outdir, fname)

        if os.path.exists(src):

            ext = os.path.splitext(fname)[1]
            if ext == "":
                ext = ".txt"

            dst = os.path.join(target_dir, f"{genome_id}{ext}")

            shutil.copy(src, dst)

        else:
            print(f"[WARNING] Missing {fname} for {genome_id}")


# -----------------------------
# MAIN BATCH FUNCTION
# -----------------------------
def run_dfast_batch(input_dir, output_dir, threads=4):

    dfast_root = os.path.join(output_dir, "dfast")
    os.makedirs(dfast_root, exist_ok=True)

    pool_dirs = create_pool_dirs(output_dir)

    genome_files = [
        f for f in os.listdir(input_dir)
        if f.lower().endswith((".fna", ".fa", ".fasta"))
    ]

    if not genome_files:
        raise RuntimeError("No genome files found")

    print(f"[INFO] Found {len(genome_files)} genomes")

    for f in genome_files:

        infile = os.path.join(input_dir, f)
        genome_id = sanitize_name(f)

        outdir = os.path.join(dfast_root, genome_id)
        os.makedirs(outdir, exist_ok=True)

        print(f"[INFO] Running DFAST → {genome_id}")

        run_single_dfast(infile, genome_id, outdir, threads)

        collect_outputs(outdir, genome_id, pool_dirs)

    print("[INFO] DFAST batch completed")
