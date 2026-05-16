import argparse
import os

from worker.annotate_dfast import run_dfast_batch
from worker.run_orthofinder import run_orthofinder
from worker.reroot_tree import reroot_tree
from worker.build_phylogroups import auto_phylogroups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--outgroup", required=True)

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Step 1–3: Annotation
    ann_dir = os.path.join(args.output, "annotations")
    run_dfast_batch(args.input, ann_dir)

    # Step 4: Orthofinder
    ortho_dir = os.path.join(args.output, "orthofinder")
    run_orthofinder(ann_dir, ortho_dir)

    # Step 5: Re-root tree
    tree_in = os.path.join(of_out, "Species_Tree", "SpeciesTree_rooted.txt")
    tree_out = os.path.join(of_out, "Species_Tree", "SpeciesTree_rerooted.nwk")
    reroot_tree(tree_in, outgroup_name, tree_out)

    # Step 6: Build phylogroups
    phylo_csv = os.path.join(args.output, "phylogroups.csv")
    auto_phylogroups(tree_out, phylo_csv)

    print("\n[DONE] Pipeline complete up to phylogroup generation")


if __name__ == "__main__":
    main()
