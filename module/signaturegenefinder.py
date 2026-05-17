import argparse
import os

from worker.signature_core import detect_signature_patterns
from worker.core_genes import compute_core_genes
from worker.annotation_mapper import add_annotations
from worker.enrichment import run_enrichment
from worker.visualization import generate_plots


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--pan_matrix", required=True)
    parser.add_argument("--phylogroups", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--mode", choices=["basic", "enrichment", "full"], default="basic")

    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # STEP 1: SIGNATURE DETECTION
    strict_df = detect_signature_patterns(
        args.pan_matrix,
        args.phylogroups
    )

   # STEP 2: CORE GENES
    core_df = compute_core_genes(
        args.pan_matrix,
        args.phylogroups
    )

    # STEP 3: ANNOTATION
    strict_df = add_annotations(strict_df, args.annotations)
    core_df = add_annotations(core_df, args.annotations)

    strict_df.to_csv(os.path.join(args.outdir, "signature_genes.tsv"), index=False)
    core_df.to_csv(os.path.join(args.outdir, "core_genes.tsv"), index=False)

    # STEP 4: ENRICHMENT
    if args.mode in ["enrichment", "full"]:
        enrich_df = run_enrichment(strict_df, args.annotations)
        enrich_df.to_csv(os.path.join(args.outdir, "enrichment.tsv"), index=False)

    # STEP 5: VISUALIZATION
    if args.mode == "full":
        generate_plots(args.outdir)

    print("[DONE] Signature analysis complete")


if __name__ == "__main__":
    main()
