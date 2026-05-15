import os
import subprocess
import shutil

def run_orthofinder(ann_dir, out_dir):

    os.makedirs(out_dir, exist_ok=True)

    faa_dir = os.path.join(out_dir, "faa_inputs")
    os.makedirs(faa_dir, exist_ok=True)

    # collect .faa files
    for root, _, files in os.walk(ann_dir):
        for f in files:
            if f.endswith(".faa"):
                shutil.copy(os.path.join(root, f), faa_dir)

    cmd = [
        "orthofinder",
        "-f", faa_dir,
        "-t", "8"
    ]

    subprocess.run(cmd, check=True)
