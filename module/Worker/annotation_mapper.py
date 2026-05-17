import pandas as pd


def add_annotations(df, annotation_file):

    annot = pd.read_csv(annotation_file, sep="\t")

    return df.merge(
        annot,
        left_on="gene",
        right_on="OG_ID",
        how="left"
    )
