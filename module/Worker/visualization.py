import os
import pandas as pd
import matplotlib.pyplot as plt


def generate_plots(out_dir):

    sig_file = os.path.join(out_dir, "signature_genes.tsv")

    if not os.path.exists(sig_file):
        print("[WARNING] No signature file found")
        return

    df = pd.read_csv(sig_file)

    counts = df["phylogroup"].value_counts()

    plt.figure()
    counts.plot(kind="bar")
    plt.title("Signature genes per phylogroup")
    plt.ylabel("Count")

    plt.tight_layout()

    plot_path = os.path.join(out_dir, "signature_counts.png")
    plt.savefig(plot_path)

    print(f"[INFO] Plot saved: {plot_path}")
