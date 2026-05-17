import argparse
import os

from Worker.annotate_dfast import run_dfast_batch
from Worker.ogri_calc import run_ogri
from Worker.run_orthofinder import run_orthofinder
from Worker.reroot_tree import reroot_tree
from Worker.build_phylogroups import auto_phylogroups
from Worker.run_pangenome import run_pangenome


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--outgroup", required=True)
    parser.add_argument("--threads", type=int, default=8)

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # STEP 1: DFAST ANNOTATION
    ann_dir = os.path.join(args.output, "annotations")
    run_dfast_batch(args.input, ann_dir)

    # pooled FAA directory (from your DFAST design)
    faa_dir = os.path.join(ann_dir, "pooled", "faa")

    # STEP 2: OGRI (ANI + AAI)
    ogri_dir = os.path.join(args.output, "validation")

    run_ogri(
        genome_dir=args.input,
        faa_dir=faa_dir,
        out_dir=ogri_dir,
        threads=args.threads
    )


    # STEP 3: ORTHOFINDER
    ortho_dir = os.path.join(args.output, "orthofinder")

    run_orthofinder(
        ann_dir=ann_dir,
        out_dir=ortho_dir,
        threads=args.threads
    )

    # STEP 4: LOCATE TREE (robust)
    results_dirs = [
        d for d in os.listdir(ortho_dir)
        if d.startswith("Results")
    ]

    if not results_dirs:
        raise RuntimeError("Orthofinder results not found")

    results_path = os.path.join(ortho_dir, results_dirs[0])

    tree_in = os.path.join(
        results_path,
        "Species_Tree",
        "SpeciesTree_rooted.txt"
    )

    tree_out = os.path.join(
        ortho_dir,
        "SpeciesTree_rerooted.nwk"
    )

    # STEP 5: REROOT TREE
    reroot_tree(
        tree_in,
        args.outgroup,
        tree_out
    )

    # STEP 6: PHYLOGROUP BUILDING
    phylo_csv = os.path.join(args.output, "phylogroups.csv")

    auto_phylogroups(
        tree_file=tree_out,
        out_csv=phylo_csv
        # future:
        # ogri_db=os.path.join(ogri_dir, "db", "ogri.db")
    )
    
     # STEP 7: PANGENOME
     pangenome_dir = os.path.join(args.output, "pangenome")
     run_pangenome(
         ann_dir=ann_dir,
         out_dir=pangenome_dir,
         outgroup=args.outgroup,
         threads=args.threads
     )   

    print("\n[DONE] Pipeline complete up to phylogroup generation")


if __name__ == "__main__":
    main()
