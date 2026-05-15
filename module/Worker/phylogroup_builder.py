from Bio import Phylo
import pandas as pd

def auto_phylogroups(tree_file, out_csv, min_size=5):

    tree = Phylo.read(tree_file, "newick")

    clades = []

    for clade in tree.find_clades(order="postorder"):
        leaves = clade.get_terminals()
        names = [l.name for l in leaves]

        if len(names) < min_size:
            continue

        clades.append(names)

    # collapse overlapping
    final = []
    used = set()

    for c in sorted(clades, key=len, reverse=True):
        s = set(c)
        if len(s & used) / len(s) < 0.3:
            final.append(s)
            used |= s

    rows = []
    for i, group in enumerate(final):
        rep = sorted(group)[0]
        name = rep.split("_")[0] + f"_{i}"

        rows.append([name, rep, i+1])

    df = pd.DataFrame(rows, columns=[
        "phylogroup", "species_type", "order_phylogeny"
    ])

    df.to_csv(out_csv, index=False)
