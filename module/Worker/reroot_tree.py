from Bio import Phylo

def reroot_tree(input_tree, output_tree, outgroup):

    tree = Phylo.read(input_tree, "newick")

    try:
        tree.root_with_outgroup(outgroup)
    except:
        raise ValueError(f"Outgroup '{outgroup}' not found in tree")

    Phylo.write(tree, output_tree, "newick")
