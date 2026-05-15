import os
import subprocess

def run_dfast_batch(input_dir, output_dir):

    os.makedirs(output_dir, exist_ok=True)

    for f in os.listdir(input_dir):
        if not f.endswith(".fna"):
            continue

        infile = os.path.join(input_dir, f)
        prefix = os.path.splitext(f)[0]
        outdir = os.path.join(output_dir, prefix)

        cmd = [
            "dfast",
            "-g", infile,
            "-o", outdir,
            "--cpu", "4"
        ]

        subprocess.run(cmd, check=True)
