import os
import subprocess
from modules.parallel_policy import ParallelismPolicy


def run_orthofinder(prep_dir, out_dir):

    os.makedirs(out_dir, exist_ok=True)
    # INPUT: use the pooled FAA directly
    faa_dir = os.path.join(prep_dir, "pooled", "faa")

    if not os.path.exists(faa_dir):
        raise RuntimeError("FAA directory not found")

    faa_files = [f for f in os.listdir(faa_dir) if f.endswith(".faa")]

    if len(faa_files) < 2:
        raise RuntimeError("Need at least 2 genomes for Orthofinder")

    print(f"[INFO] Orthofinder input genomes: {len(faa_files)}")

    # PARALLELISM POLICY
    policy = ParallelismPolicy()
    p = policy.orthofinder_policy()

    total = p["total"]
    t = p["search_threads"]
    a = p["analysis_threads"]

    print(f"[INFO] Total threads: {total}")
    print(f"[INFO] Search threads (-t): {t}")
    print(f"[INFO] Analysis threads (-a): {a}")

    # OUTPUT DIRECTORY
    of_out = os.path.join(out_dir, "orthofinder")

    if os.path.exists(of_out):
        subprocess.run(["rm", "-rf", of_out])

    # ACCURACY-FIRST Orthofinder command support version (3.1.4)
    cmd = [
        "orthofinder",
        "-f", faa_dir,
        "-t", str(t),
        "-a", str(a),
        "-S", "diamond_ultra_sens",
        "-M", "msa",
        "-A", "mafft",
        "-T", "iqtree3",
        "-o", of_out
    ]

    print("[INFO] Running Orthofinder...")

    subprocess.run(cmd, check=True)

    print(f"[INFO] Orthofinder completed : results at  {of_out}")
