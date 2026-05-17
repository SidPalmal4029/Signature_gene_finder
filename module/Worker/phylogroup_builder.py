import sqlite3
from Bio import Phylo
import pandas as pd

# DB ACCESS
def get_pair(conn, g1, g2):
    cur = conn.execute(
        "SELECT ani, aai FROM ogri WHERE (g1=? AND g2=?) OR (g1=? AND g2=?)",
        (g1, g2, g2, g1)
    )
    row = cur.fetchone()
    return row if row else (None, None)

# GLOBAL AAI STATS WITH ADAPTIVE THRESHOLD
def compute_global_aai_stats(conn):
    df = pd.read_sql("SELECT aai FROM ogri WHERE aai IS NOT NULL", conn)

    mean_aai = df["aai"].mean()
    std_aai = df["aai"].std()

    AAI_T = mean_aai - 0.5 * std_aai
    AAI_T = max(0.55, min(0.75, AAI_T))

    return AAI_T, mean_aai, std_aai

# SCORING FUNCTIONS
def mean_aai(conn, g, clade):
    scores = []
    for m in clade:
        if g == m:
            continue
        _, aai = get_pair(conn, g, m)
        if aai is not None:
            scores.append(aai)
    return sum(scores)/len(scores) if scores else 0


def ani_support(conn, g, clade, threshold=80):
    count = 0
    for m in clade:
        if g == m:
            continue
        ani, _ = get_pair(conn, g, m)
        if ani is not None and ani >= threshold:
            count += 1
    return count


def ani_ratio(conn, clade, threshold=80):
    total = 0
    good = 0
    clade = list(clade)

    for i in range(len(clade)):
        for j in range(i+1, len(clade)):
            ani, _ = get_pair(conn, clade[i], clade[j])
            if ani is not None:
                total += 1
                if ani >= threshold:
                    good += 1

    return good / total if total else 0


def score_clade(conn, clade):
    values = []
    clade = list(clade)

    for i in range(len(clade)):
        for j in range(i+1, len(clade)):
            _, aai = get_pair(conn, clade[i], clade[j])
            if aai is not None:
                values.append(aai)

    if not values:
        return 0, 0

    return sum(values)/len(values), min(values)


def compute_confidence(conn, clade, mean_aai_val, min_aai_val):
    ani_r = ani_ratio(conn, clade)
    return 0.6 * mean_aai_val + 0.3 * min_aai_val + 0.1 * ani_r
    
# CLADE EXTRACTION
def extract_clades(tree, min_size):
    clades = []
    for clade in tree.find_clades(order="postorder"):
        leaves = {l.name for l in clade.get_terminals()}
        if len(leaves) >= min_size:
            clades.append(leaves)
    return clades
    
# PRUNING
def prune_clades(clades, conn, AAI_T, ANI_T):
    new_clades = []
    unassigned = set()

    for clade in clades:
        keep = set()

        for g in clade:
            aai_score = mean_aai(conn, g, clade)
            ani_sup = ani_support(conn, g, clade, ANI_T)

            if aai_score >= AAI_T and ani_sup >= 1:
                keep.add(g)
            else:
                unassigned.add(g)

        if keep:
            new_clades.append(keep)

    return new_clades, unassigned

# GLOBAL EVALUATION
def evaluate_unassigned(unassigned, clades, conn, AAI_T, ANI_T, moved_once):

    decisions = {}

    for g in unassigned:

        scores = []
        for i, c in enumerate(clades):
            s = mean_aai(conn, g, c)
            scores.append((i, s))

        scores.sort(key=lambda x: x[1], reverse=True)

        best_id, best_score = scores[0]
        second_score = scores[1][1] if len(scores) > 1 else 0
        ani_sup = ani_support(conn, g, clades[best_id], ANI_T)

        move = True
        reason = ""

        if best_score < AAI_T:
            move = False
            reason = "LOW_AAI"

        elif abs(best_score - second_score) < 0.02:
            move = False
            reason = "AMBIGUOUS_ASSIGNMENT"

        elif ani_sup < 1:
            move = False
            reason = "LOW_ANI_SUPPORT"

        elif g in moved_once:
            move = False
            reason = "ALREADY_MOVED"

        decisions[g] = {
            "target": best_id,
            "best_score": best_score,
            "second_score": second_score,
            "ani_support": ani_sup,
            "move": move,
            "reason": reason
        }

    return decisions
    
# APPLY MOVES
def apply_moves(clades, decisions, moved_once):
    changes = 0

    for g, d in decisions.items():
        if d["move"]:
            clades[d["target"]].add(g)
            moved_once.add(g)
            changes += 1

    return clades, moved_once, changes

# MAIN PIPELINE
def auto_phylogroups(tree_file, ogri_db, out_csv,
                     out_reject="unplaced_genomes.tsv",
                     out_meta="phylogroups_metadata.txt",
                     outgroup=None,
                     min_size=5,
                     ANI_T=80,
                     MAX_ITER=6):

    conn = sqlite3.connect(ogri_db)

    # Adaptive threshold
    AAI_T, global_mean, global_std = compute_global_aai_stats(conn)

    print(f"[INFO] AAI threshold: {AAI_T:.3f}")

    tree = Phylo.read(tree_file, "newick")
    clades = extract_clades(tree, min_size)

    if outgroup:
        clades = [{g for g in c if g != outgroup} for c in clades]

    moved_once = set()
    final_unassigned = set()

    # ITERATIONS
    for it in range(MAX_ITER):

        clades, unassigned = prune_clades(clades, conn, AAI_T, ANI_T)

        decisions = evaluate_unassigned(
            unassigned, clades, conn,
            AAI_T, ANI_T, moved_once
        )

        clades, moved_once, changes = apply_moves(
            clades, decisions, moved_once
        )

        print(f"[ITER {it+1}] moves: {changes}")

        if changes == 0:
            final_unassigned = {
                g for g, d in decisions.items() if not d["move"]
            }
            break

    # FILTER FINAL CLADES
    clades = [c for c in clades if len(c) >= min_size]

    # OUTPUT CSV
    rows = []

    for i, c in enumerate(clades):

        rep = sorted(c)[0]
        mean_aai_val, min_aai_val = score_clade(conn, c)
        conf = compute_confidence(conn, c, mean_aai_val, min_aai_val)

        rows.append([
            f"group_{i+1}",
            rep,
            i+1,
            mean_aai_val,
            min_aai_val,
            len(c),
            conf
        ])

    df = pd.DataFrame(rows, columns=[
        "phylogroup",
        "species_type",
        "order_phylogeny",
        "mean_aai",
        "min_aai",
        "size",
        "confidence"
    ])

    df.to_csv(out_csv, index=False)

    # REJECTION LOG
    rej_rows = []
    for g in final_unassigned:
        d = decisions[g]
        rej_rows.append([
            g,
            d["target"],
            d["best_score"],
            d["second_score"],
            d["ani_support"],
            d["reason"]
        ])

    pd.DataFrame(rej_rows, columns=[
        "genome",
        "best_clade",
        "best_aai",
        "second_best_aai",
        "ani_support",
        "reason"
    ]).to_csv(out_reject, index=False)

    # METADATA FILE
    with open(out_meta, "w") as f:
        f.write(f"""
PHYLOGROUP METADATA

Adaptive AAI threshold: {AAI_T:.3f}
Global mean AAI: {global_mean:.3f}
Global std AAI: {global_std:.3f}

Confidence = 0.6*mean_aai + 0.3*min_aai + 0.1*ANI_ratio

Interpretation:
>0.75 strong
0.6–0.75 moderate
<0.6 weak

See unplaced_genomes.tsv for rejected genomes.
""")

    conn.close()

    print("[DONE] Phylogroups generated successfully")
