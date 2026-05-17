import pandas as pd


def compute_core_genes(pan_matrix, phylogroups):

    df = pd.read_csv(pan_matrix, sep="\t", index_col=0)
    phylo = pd.read_csv(phylogroups)

    groups = {}
    for _, row in phylo.iterrows():
        groups.setdefault(row["phylogroup"], []).append(row["species_type"])

    results = []

    for pg, members in groups.items():

        sub = df[members]

        core_mask = sub.sum(axis=1) == len(members)

        for gene in df.index[core_mask]:
            results.append({
                "gene": gene,
                "phylogroup": pg
            })

    return pd.DataFrame(results)
