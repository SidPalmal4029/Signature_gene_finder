import os
import shutil
import subprocess
import tempfile
import glob
import json
import pandas as pd

# MATRIX NORMALIZATION
def normalize_matrix(matrix_file, out_file):
    df = pd.read_csv(matrix_file, sep="\t", index_col=0)

    # Convert to binary presence/absence
    df_binary = df.notnull().astype(int)

    df_binary.to_csv(out_file, sep="\t")

    return df_binary
  
# BUILD INDICES
def build_genome_index(df, out_file):
    mapping = {col: i for i, col in enumerate(df.columns)}
    with open(out_file, "w") as f:
        json.dump(mapping, f, indent=2)


def build_gene_index(df, out_file):
    mapping = {gene: i for i, gene in enumerate(df.index)}
    with open(out_file, "w") as f:
        json.dump(mapping, f, indent=2)

# SUMMARY STATS
def compute_pan_summary(df, out_file):
    freq = df.sum(axis=1)

    summary = pd.DataFrame({
        "gene": df.index,
        "presence_count": freq,
        "presence_fraction": freq / df.shape[1]
    })

    summary.to_csv(out_file, index=False)


#ANNOTATE THE OGs
def build_og_annotations(cluster_dir, faa_dir, out_file):

    gene_to_annot = {}

    # Load annotations from FAA
    for f in os.listdir(faa_dir):
        if not f.endswith(".faa"):
            continue

        with open(os.path.join(faa_dir, f)) as fh:
            for line in fh:
                if line.startswith(">"):
                    header = line.strip()
                    gene_id = header.split()[0][1:]

                    # Try extracting gene symbol
                    m = re.search(r"\[([^\]]+)\]", header)
                    if m:
                        gene_name = m.group(1)
                    else:
                        gene_name = header.split(None, 1)[-1]

                    gene_to_annot[gene_id] = gene_name

    rows = []

    # Parse cluster files
    for file in os.listdir(cluster_dir):

        if not file.endswith(".faa"):
            continue

        og_id = file.replace(".faa", "")
        genes = []

        with open(os.path.join(cluster_dir, file)) as fh:
            for line in fh:
                if line.startswith(">"):
                    gene_id = line.strip().split()[0][1:]
                    genes.append(gene_id)

        annotations = [gene_to_annot.get(g, g) for g in genes]

        # pick most common annotation
        most_common = Counter(annotations).most_common(1)[0][0]

        rows.append([
            og_id,
            most_common,
            len(genes)
        ])

    df = pd.DataFrame(rows, columns=[
        "OG_ID", "gene_name", "cluster_size"
    ])

    df.to_csv(out_file, sep="\t", index=False)


def run_pangenome(ann_dir, out_dir, outgroup, threads, debug=False):

    faa_dir = os.path.join(ann_dir, "pooled", "faa")

    if not os.path.exists(faa_dir):
        raise RuntimeError(f"[ERROR] FAA directory not found: {faa_dir}")

    os.makedirs(out_dir, exist_ok=True)

    # -----------------------------
    # TEMP DIRECTORY
    # -----------------------------
    tmp_dir = tempfile.mkdtemp(prefix="pangenome_")
    print(f"[INFO] Temp directory: {tmp_dir}")

    try:
        # -----------------------------
        # COPY FILES (EXCLUDE OUTGROUP)
        # -----------------------------
        copied = 0

        for f in sorted(os.listdir(faa_dir)):

            if not f.endswith(".faa"):
                continue

            genome_id = os.path.splitext(f)[0]

            if genome_id == outgroup:
                print(f"[INFO] Skipping outgroup: {genome_id}")
                continue

            shutil.copy(
                os.path.join(faa_dir, f),
                os.path.join(tmp_dir, f)
            )
            copied += 1

        if copied == 0:
            raise RuntimeError("[ERROR] No FAA files copied")

        print(f"[INFO] {copied} genomes included in pangenome")

        # -----------------------------
        # RUN get_homologues
        # -----------------------------
        cmd = [
            "get_homologues.pl",
            "-d", tmp_dir,
            "-M",
            "-t", "0",
            "-n", str(threads),
            "-X",
            "-C", "75",
            "-S", "35",
            "-A"
        ]

        print("[INFO] Running get_homologues...")
        subprocess.run(cmd, check=True, cwd=out_dir)

        # -----------------------------
        # LOCATE RESULT (ROBUST)
        # -----------------------------
        result_dirs = sorted(
            glob.glob(os.path.join(out_dir, "*_homologues")),
            key=os.path.getmtime
        )

        if not result_dirs:
            raise RuntimeError("[ERROR] No get_homologues output found")

        result_dir = result_dirs[-1]  # latest run

        # -----------------------------
        # MATRIX EXTRACTION
        # -----------------------------
        matrix_file = os.path.join(
            result_dir,
            "pan-genome_matrix_t0.tab"
        )

        if not os.path.exists(matrix_file):
            raise RuntimeError("[ERROR] Matrix file missing")

        raw_matrix = os.path.join(out_dir, "pan_matrix.tsv")
        shutil.copy(matrix_file, raw_matrix)

        print(f"[INFO] Raw matrix saved: {raw_matrix}")

        # -----------------------------
        # NORMALIZE MATRIX
        # -----------------------------
        binary_matrix = os.path.join(out_dir, "pan_matrix_binary.tsv")

        df = normalize_matrix(raw_matrix, binary_matrix)

        print(f"[INFO] Binary matrix saved: {binary_matrix}")

        # -----------------------------
        # BUILD INDICES
        # -----------------------------
        build_genome_index(df, os.path.join(out_dir, "genome_index.json"))
        build_gene_index(df, os.path.join(out_dir, "gene_index.json"))

        print("[INFO] Index files generated")

        # -----------------------------
        # SUMMARY
        # -----------------------------
        compute_pan_summary(df, os.path.join(out_dir, "pan_summary.tsv"))

        print("[INFO] Summary statistics generated")

        # -----------------------------
        # OG ANNOTATION (NEW)
        # -----------------------------
        cluster_dir = os.path.join(result_dir, "cluster_list")

        if os.path.exists(cluster_dir):

            annotation_file = os.path.join(out_dir, "og_annotations.tsv")

            build_og_annotations(
                cluster_dir,
                faa_dir,
                annotation_file
            )

            print(f"[INFO] OG annotation saved: {annotation_file}")

        else:
            print("[WARNING] cluster_list not found, skipping annotation")

    finally:
        if debug:
            print(f"[DEBUG] Temp retained: {tmp_dir}")
        else:
            shutil.rmtree(tmp_dir)
            print("[INFO] Temp directory removed")

    print("[DONE] Pangenome pipeline complete")
