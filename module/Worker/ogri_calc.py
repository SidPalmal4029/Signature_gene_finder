import os
import sqlite3
import subprocess
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
import networkx as nx

# DIRECTORY SETUP
def setup_dirs(base):

    dirs = {
        "raw": os.path.join(base, "raw"),
        "db": os.path.join(base, "db"),
        "normalized": os.path.join(base, "normalized"),
        "stats": os.path.join(base, "stats"),
        "clustering": os.path.join(base, "clustering")
    }

    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    return dirs

# FASTANI
def run_fastani(genome_dir, out_file, threads):

    genomes = [
        os.path.join(genome_dir, f)
        for f in os.listdir(genome_dir)
        if f.endswith((".fna", ".fa", ".fasta"))
    ]

    list_file = out_file + ".list"
    with open(list_file, "w") as f:
        for g in genomes:
            f.write(g + "\n")

    cmd = [
        "fastANI",
        "--ql", list_file,
        "--rl", list_file,
        "-t", str(threads),
        "--matrix",
        "-o", out_file
    ]

    subprocess.run(cmd, check=True)

# EZAAI CONVERT
def _convert_one(faa, db_dir):

    name = os.path.splitext(os.path.basename(faa))[0]
    out_db = os.path.join(db_dir, name)

    cmd = [
        "ezaai", "convert",
        "-i", faa,
        "-s", "prot",
        "-o", out_db
    ]

    subprocess.run(cmd, check=True)

    return name

# EZAAI
def run_ezaai(faa_dir, out_dir, threads):

    db_dir = os.path.join(out_dir, "ezaai_db")
    os.makedirs(db_dir, exist_ok=True)

    faa_files = [
        os.path.join(faa_dir, f)
        for f in os.listdir(faa_dir)
        if f.endswith(".faa")
    ]

    # parallel convert
    with ProcessPoolExecutor(max_workers=min(len(faa_files), threads)) as ex:
        futures = [ex.submit(_convert_one, f, db_dir) for f in faa_files]
        for f in as_completed(futures):
            f.result()

    aai_out = os.path.join(out_dir, "aai.tsv")

    cmd = [
        "ezaai",
        "calculate",
        "-i", db_dir,
        "-j", db_dir,
        "-o", aai_out,
        "-self", "1",
        "-t", str(threads)
    ]

    subprocess.run(cmd, check=True)

    return aai_out


# LOAD + NORMALIZE
def load_ani(file):

    df = pd.read_csv(file, sep="\t", header=None)
    df.columns = ["g1", "g2", "ani", "frags", "total"]
    return df[["g1", "g2", "ani"]]


def load_aai(file):

    df = pd.read_csv(file, sep="\t")
    df.columns = ["g1", "g2", "aai"]
    return df


def normalize_names(df):

    df["g1"] = df["g1"].apply(lambda x: os.path.basename(x).split(".")[0])
    df["g2"] = df["g2"].apply(lambda x: os.path.basename(x).split(".")[0])
    return df

# BUILD DB
def build_db(ani_df, aai_df, db_path):

    conn = sqlite3.connect(db_path)

    df = pd.merge(ani_df, aai_df, on=["g1", "g2"], how="outer")

    # make symmetric
    rev = df.rename(columns={"g1": "g2", "g2": "g1"})
    df = pd.concat([df, rev]).drop_duplicates()

    df.to_sql("ogri", conn, if_exists="replace", index=False)

    conn.execute("CREATE INDEX idx_g1 ON ogri(g1)")
    conn.execute("CREATE INDEX idx_g2 ON ogri(g2)")

    conn.commit()
    conn.close()

# COMPLETENESS
def compute_completeness(ani_df, aai_df, out_file):

    ani_df["has_ani"] = True
    aai_df["has_aai"] = True

    df = pd.merge(ani_df, aai_df, on=["g1", "g2"], how="outer")

    df[["g1", "g2", "has_ani", "has_aai"]].to_csv(out_file, index=False)

# GENOME STATS
def genome_stats(df, out_file):

    stats = []

    for g in set(df["g1"]):

        sub = df[df["g1"] == g]

        stats.append({
            "genome": g,
            "mean_aai": sub["aai"].mean(),
            "min_aai": sub["aai"].min(),
            "mean_ani": sub["ani"].mean()
        })

    pd.DataFrame(stats).to_csv(out_file, index=False)

# CLUSTERING
def cluster_aai(df, threshold, out_file):

    G = nx.Graph()

    for _, r in df.iterrows():
        if pd.notna(r["aai"]) and r["aai"] >= threshold:
            G.add_edge(r["g1"], r["g2"])

    clusters = list(nx.connected_components(G))

    rows = []
    for i, c in enumerate(clusters):
        for g in c:
            rows.append([i, g])

    pd.DataFrame(rows, columns=["cluster", "genome"]).to_csv(out_file, index=False)

# MAIN DRIVER
def run_ogri(genome_dir, faa_dir, out_dir, threads=8):

    dirs = setup_dirs(out_dir)

    print("[INFO] Running ANI")
    ani_file = os.path.join(dirs["raw"], "ani.tsv")
    run_fastani(genome_dir, ani_file, threads)

    print("[INFO] Running AAI")
    aai_file = run_ezaai(faa_dir, dirs["raw"], threads)

    print("[INFO] Loading data")
    ani = normalize_names(load_ani(ani_file))
    aai = normalize_names(load_aai(aai_file))

    print("[INFO] Building DB")
    db_path = os.path.join(dirs["db"], "ogri.db")
    build_db(ani, aai, db_path)

    print("[INFO] Computing completeness")
    compute_completeness(
        ani, aai,
        os.path.join(dirs["stats"], "ogri_completeness.tsv")
    )

    print("[INFO] Computing genome stats")
    merged = pd.merge(ani, aai, on=["g1", "g2"], how="outer")
    genome_stats(
        merged,
        os.path.join(dirs["stats"], "genome_stats.tsv")
    )

    print("[INFO] Clustering AAI")
    cluster_aai(
        merged,
        threshold=0.65,
        out_file=os.path.join(dirs["clustering"], "aai_clusters.tsv")
    )

    print("[INFO] OGRI pipeline complete")

    return db_path
