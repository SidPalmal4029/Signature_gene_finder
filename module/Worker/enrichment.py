import pandas as pd


def run_enrichment(signature_df, annotation_file):

    annot = pd.read_csv(annotation_file, sep="\t")

    merged = signature_df.merge(
        annot,
        left_on="gene",
        right_on="OG_ID",
        how="left"
    )

    # simple frequency-based enrichment
    counts = merged["gene_name"].value_counts().reset_index()
    counts.columns = ["gene_name", "count"]

    counts["fraction"] = counts["count"] / counts["count"].sum()

    return counts
