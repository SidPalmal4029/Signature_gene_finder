#!/usr/bin/env bash

set -euo pipefail

# -----------------------------
# DEFAULTS
# -----------------------------
THREADS=""

# -----------------------------
# USAGE
# -----------------------------
usage() {
  echo "Signaturegenefinder"
  echo ""
  echo "Usage:"
  echo " Signature-gene-finder.sh -i <genome_dir> -o <output_dir> -g <outgroup_name> [-t threads]"
  echo ""
  exit 1
}

# -----------------------------
# PARSE ARGS
# -----------------------------
while getopts "i:o:g:t:h" opt; do
  case $opt in
    i) INPUT_DIR="$OPTARG" ;;
    o) OUT_DIR="$OPTARG" ;;
    g) OUTGROUP="$OPTARG" ;;
    t) THREADS="$OPTARG" ;;
    h) usage ;;
    *) usage ;;
  esac
done

# -----------------------------
# VALIDATION
# -----------------------------
[ -z "${INPUT_DIR:-}" ] && usage
[ -z "${OUT_DIR:-}" ] && usage
[ -z "${OUTGROUP:-}" ] && usage

if [ ! -d "$INPUT_DIR" ]; then
  echo "[ERROR] Input directory not found: $INPUT_DIR"
  exit 1
fi

# -----------------------------
# SETUP DIRECTORIES
# -----------------------------
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

# -----------------------------
# DETECT FASTA FILES
# -----------------------------
log "[INFO] Scanning input directory..."

mapfile -t GENOME_FILES < <(find "$INPUT_DIR" -maxdepth 1 -type f \
  \( -iname "*.fna" -o -iname "*.fa" -o -iname "*.fasta" \))

GENOME_COUNT=${#GENOME_FILES[@]}

if [ "$GENOME_COUNT" -eq 0 ]; then
  log "[ERROR] No genome fasta files found"
  exit 1
fi

log "[INFO] Found $GENOME_COUNT genome files"

# -----------------------------
# LIST FILES
# -----------------------------
log "[INFO] Input genomes:"
for f in "${GENOME_FILES[@]}"; do
  log "  - $(basename "$f")"
done

# -----------------------------
# COPY FILES
# -----------------------------
log "[INFO] Copying genome files..."

for f in "${GENOME_FILES[@]}"; do
  cp "$f" "$GENOMES/"
done

log "[INFO] Copy complete → $GENOMES"

# -----------------------------
# PIPELINE SUMMARY
# -----------------------------
log "----------------------------------------"
log "[INFO] Pipeline configuration"
log "Input Dir   : $INPUT_DIR"
log "Output Dir  : $OUT_DIR"
log "Threads     : $THREADS"
log "Outgroup    : $OUTGROUP"
log "Genomes     : $GENOME_COUNT"
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

# -----------------------------
# STEP 1: PREPARATION
# -----------------------------
run_step "PREPARATION" \
  python3 -u preperator.py \
    --input "$GENOMES" \
    --output "$PREP" \
    --outgroup "$OUTGROUP" \
    --threads "$THREADS"

# -----------------------------
# STEP 2: SIGNATURE ANALYSIS
# -----------------------------
run_step "SIGNATURE" \
  python3 -u signaturegenefinder.py \
    --input "$PREP" \
    --output "$RESULTS" \
    --outgroup "$OUTGROUP" \
    --threads "$THREADS"

# -----------------------------
# DONE
# -----------------------------
log "[DONE] Pipeline completed successfully"
