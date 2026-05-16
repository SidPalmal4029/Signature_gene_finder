from Bio import Phylo
import os


def reroot_tree(tree_file, outgroup_name, output_file):

    if not os.path.exists(tree_file):
        raise RuntimeError("Tree file not found")

    tree = Phylo.read(tree_file, "newick")

    # FIND OUTGROUP MATCHES FROM USER INPUT
    matches = []

    for leaf in tree.get_terminals():
        if outgroup_name in leaf.name:
            matches.append(leaf)

    if len(matches) == 0:
        raise RuntimeError(f"Outgroup not found in tree: {outgroup_name}")

    print(f"[INFO] Found {len(matches)} outgroup matches")

    # REROOT
    if len(matches) == 1:
        tree.root_with_outgroup(matches[0])
    else:
        tree.root_with_outgroup(matches)

    # CLEAN BRANCH LENGTH 
    tree.ladderize()

    # WRITE OUTPUT
    Phylo.write(tree, output_file, "newick")

    print(f"[INFO] Rerooted tree written → {output_file}")
