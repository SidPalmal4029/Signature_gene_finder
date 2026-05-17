import pandas as pd


def load_data(pan_matrix, phylogroups):
    df = pd.read_csv(pan_matrix, sep="\t", index_col=0)
    phylo = pd.read_csv(phylogroups)
    return df, phylo


def build_phylo_map(phylo_df):
    groups = {}
    for _, row in phylo_df.iterrows():
        groups.setdefault(row["phylogroup"], []).append(row["species_type"])
    return groups


def filter_orthogroups(df):
    total = df.shape[1]
    counts = df.sum(axis=1)
    return df[(counts > 1) & (counts < total)]


def build_patterns(df):
    patterns = {}
    for gene, row in df.iterrows():
        key = tuple(row.values)
        patterns.setdefault(key, []).append(gene)
    return patterns


def detect_signature_patterns(pan_matrix, phylogroups, freq_min=3):

    df, phylo_df = load_data(pan_matrix, phylogroups)
    phylo_map = build_phylo_map(phylo_df)

    df = filter_orthogroups(df)
    patterns = build_patterns(df)

    genomes = list(df.columns)
    results = []

    for pattern, genes in patterns.items():

        if len(genes) < freq_min:
            continue

        pattern_series = pd.Series(pattern, index=genomes)

        for pg, members in phylo_map.items():

            outside = [g for g in genomes if g not in members]

            if not members:
                continue

            if all(pattern_series[members] == 1) and all(pattern_series[outside] == 0):

                for g in genes:
                    results.append({
                        "gene": g,
                        "phylogroup": pg,
                        "pattern_freq": len(genes),
                        "type": "STRICT"
                    })

    return pd.DataFrame(results)
