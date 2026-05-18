import os
import re
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from module.paralle_policy import ParallelismPolicy

# SANITIZE GENOME NAME
def sanitize_name(filename):
    name = os.path.splitext(filename)[0]
    # replace all non-safe characters
    name = re.sub(r"[^\w\.]+", "_", name)
    # collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    return name.strip("_")

# CREATE POOLED STRUCTURE
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

# RUN DFAST PER GENOME
def run_single_dfast(task):

    infile, genome_id, outdir, threads = task

    cmd = [
        "dfast",
        "--genome", infile,
        "--out", outdir,
        "--cpu", str(threads),
        "--force",
        "--locus_tag_prefix", genome_id
    ]

    subprocess.run(cmd, check=True)

    return genome_id

# COPY OUTPUTS TO POOL
def collect_outputs(outdir, genome_id, pool_dirs):

    for fname, target_dir in pool_dirs.items():

        src = os.path.join(outdir, fname)

        if os.path.exists(src):

            ext = os.path.splitext(fname)[1] or ".txt"
            dst = os.path.join(target_dir, f"{genome_id}{ext}")

            shutil.copy(src, dst)

        else:
            print(f"[WARNING] Missing {fname} for {genome_id}")

# MAIN BATCH FUNCTION
def run_dfast_batch(input_dir, output_dir):

    dfast_root = os.path.join(output_dir, "dfast")
    os.makedirs(dfast_root, exist_ok=True)

    pool_dirs = create_pool_dirs(output_dir)

    genome_files = sorted([
        f for f in os.listdir(input_dir)
        if f.lower().endswith((".fna", ".fa", ".fasta"))
    ])

    if not genome_files:
        raise RuntimeError("No genome files found")

    print(f"[INFO] Found {len(genome_files)} genomes")
    
    # APPLY PARALLELISM POLICY
    policy = ParallelismPolicy()
    p = policy.dfast_policy(len(genome_files))

    jobs = p["jobs"]
    thread_list = p["threads"]

    print(f"[INFO] Parallel jobs: {jobs}")
    print(f"[INFO] Threads per job: {thread_list}")

    # PREP TASKS
    tasks = []

    for i, f in enumerate(genome_files):

        infile = os.path.join(input_dir, f)
        genome_id = sanitize_name(f)

        outdir = os.path.join(dfast_root, genome_id)
        os.makedirs(outdir, exist_ok=True)

        # round-robin thread assignment
        threads = thread_list[i % jobs]

        tasks.append((infile, genome_id, outdir, threads))

    # PARALLEL EXECUTION
    with ProcessPoolExecutor(max_workers=jobs) as executor:

        futures = [executor.submit(run_single_dfast, t) for t in tasks]

        for future in as_completed(futures):

            genome_id = future.result()
            outdir = os.path.join(dfast_root, genome_id)

            print(f"[INFO] Completed: {genome_id}")

            collect_outputs(outdir, genome_id, pool_dirs)

    print("[INFO] DFAST batch completed")
