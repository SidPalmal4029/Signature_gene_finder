#!/usr/bin/env bash

set -euo pipefail

# DEFAULTS
THREADS=""
MODE="all"

# USAGE
usage() {
  echo "Signature Gene Finder"
  echo ""
  echo "Usage:"
  echo "  Signature-gene-finder.sh -i <genome_dir> -o <output_dir> -g <outgroup> [-t threads] [-m mode]"
  echo ""
  echo "Modes:"
  echo "  prep        Run only preparatory phase"
  echo "  signature   Run only signature detection (requires PREP outputs)"
  echo "  all         Run both phases (default)"
  echo ""
  exit 1
}

while getopts "i:o:g:t:m:h-:" opt; do
  case $opt in
    i) INPUT_DIR="$OPTARG" ;;
    o) OUT_DIR="$OPTARG" ;;
    g) OUTGROUP="$OPTARG" ;;
    t) THREADS="$OPTARG" ;;
    m) MODE="$OPTARG" ;;
    h) SHOW_HELP=1 ;;
    -)
      case "$OPTARG" in
        help) SHOW_HELP=1 ;;
        *) usage ;;
      esac
      ;;
    *) usage ;;
  esac
done

# HELP DISPLAY
if [[ "${SHOW_HELP:-0}" -eq 1 ]]; then

  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  if [ -f "$SCRIPT_DIR/help.md" ]; then
    cat "$SCRIPT_DIR/help.md"
  elif [ -f "$SCRIPT_DIR/help.txt" ]; then
    cat "$SCRIPT_DIR/help.txt"
  else
    echo "[INFO] Help file not found."
    usage
  fi

  exit 0
fi

# VALIDATION
if [[ "$MODE" != "signature" ]]; then
  [ -z "${INPUT_DIR:-}" ] && usage
  [ ! -d "$INPUT_DIR" ] && { echo "[ERROR] Input directory not found: $INPUT_DIR"; exit 1; }
fi

[ -z "${OUT_DIR:-}" ] && usage
[ -z "${OUTGROUP:-}" ] && usage


# SETUP DIRECTORIES
GENOMES="$OUT_DIR/GENOMES"
PREP="$OUT_DIR/PREP"
RESULTS="$OUT_DIR/RESULTS"

mkdir -p "$GENOMES" "$PREP" "$RESULTS"

# -----------------------------
# LOGGING
# -----------------------------
LOG="$OUT_DIR/pipeline.log"

log() {
  echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

log "[INFO] Pipeline started"

# -----------------------------
# AUTO THREAD DETECTION
# -----------------------------
if [ -z "${THREADS:-}" ]; then

  NPROC=$(nproc)

  if [ "$NPROC" -le 4 ]; then
    THREADS=$(( NPROC / 2 ))
    [ "$THREADS" -lt 1 ] && THREADS=1

  elif [ "$NPROC" -le 8 ]; then
    THREADS=$NPROC

  else
    THREADS=$(awk -v n="$NPROC" 'BEGIN { printf "%d", n*0.95 }')
  fi

  log "[INFO] Auto-detected CPUs : $NPROC"
  log "[INFO] Using threads     : $THREADS"

else
  log "[INFO] Using user-defined threads: $THREADS"
fi

# DETECT FASTA FILES
log "[INFO] Scanning input directory..."

mapfile -t GENOME_FILES < <(find "$INPUT_DIR" -maxdepth 1 -type f \
  \( -iname "*.fna" -o -iname "*.fa" -o -iname "*.fasta" \))

GENOME_COUNT=${#GENOME_FILES[@]}

if [ "$GENOME_COUNT" -eq 0 ]; then
  log "[ERROR] No genome fasta files found"
  exit 1
fi

log "[INFO] Found $GENOME_COUNT genome files"

# LIST FILES
log "[INFO] Input genomes:"
for f in "${GENOME_FILES[@]}"; do
  log "  - $(basename "$f")"
done

# COPY FILES
log "[INFO] Copying genome files..."

for f in "${GENOME_FILES[@]}"; do
  cp "$f" "$GENOMES/"
done

log "[INFO] Copy complete :  $GENOMES"


# PIPELINE SUMMARY
log "----------------------------------------"
log "[INFO] Pipeline configuration"
log "Input Dir   : $INPUT_DIR"
log "Output Dir  : $OUT_DIR"
log "Threads     : $THREADS"
log "Outgroup    : $OUTGROUP"
log "Genomes     : $GENOME_COUNT"
log "Mode        : "$MODE"
log "----------------------------------------"

# -----------------------------
# STEP RUNNER
# -----------------------------
run_step() {
  STEP_NAME="$1"
  shift

  log "[INFO] Starting: $STEP_NAME"

  "$@" 2>&1 | while IFS= read -r line; do
    echo "$line"
    echo "[$STEP_NAME] $line" >> "$LOG"
  done

  log "[INFO] Completed: $STEP_NAME"
}

# =========================================================
# STEP 1: PREPARATION
# =========================================================
if [[ "$MODE" == "prep" || "$MODE" == "all" ]]; then
  run_step "PREPARATION" \
    python3 -u preperator.py \
      --input "$GENOMES" \
      --output "$PREP" \
      --outgroup "$OUTGROUP" \
      --threads "$THREADS"
fi

# =========================================================
# STEP 2: SIGNATURE ANALYSIS
# =========================================================
if [[ "$MODE" == "signature" || "$MODE" == "all" ]]; then

  # Ensure PREP exists if signature-only
  if [[ "$MODE" == "signature" && ! -d "$PREP" ]]; then
    log "[ERROR] PREP directory not found. Run prep mode first."
    exit 1
  fi

  PAN_MATRIX="$PREP/pangenome/pan_matrix_binary.tsv"
  PHYLOGROUPS="$PREP/phylogroups.csv"
  ANNOTATIONS="$PREP/pangenome/og_annotations.tsv"

  [ ! -f "$PAN_MATRIX" ] && { log "[ERROR] Missing pan_matrix"; exit 1; }
  [ ! -f "$PHYLOGROUPS" ] && { log "[ERROR] Missing phylogroups"; exit 1; }
  [ ! -f "$ANNOTATIONS" ] && { log "[ERROR] Missing annotations"; exit 1; }

  run_step "SIGNATURE" \
    python3 -u signaturegenefinder.py \
      --pan_matrix "$PAN_MATRIX" \
      --phylogroups "$PHYLOGROUPS" \
      --annotations "$ANNOTATIONS" \
      --outdir "$RESULTS" \
      --mode full

fi

# -----------------------------
# DONE
# -----------------------------
