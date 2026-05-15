# modules for annotating the genomes 

import os
import subprocess
import yaml
import argparse

def main(config):

    for genome in os.listdir(config["genomes_dir"]):

        infile = f"{config['genomes_dir']}/{genome}"
        outdir = f"{config['bakta_out']}/{genome}"

        cmd = f"bakta --output {outdir} --threads {config['threads']} {infile}"
        subprocess.run(cmd, shell=True, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config = yaml.safe_load(open(args.config))
    main(config)
