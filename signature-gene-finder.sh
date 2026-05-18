#!/usr/bin/env bash

set -euo pipefail

# DEFAULTS
THREADS=""
MODE="all"

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
BASE_DIR="$(dirname "$SCRIPT_PATH")"
MODULE_DIR="$BASE_DIR/module"

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

# MODE VALIDATION
case "$MODE" in
  prep|signature|all) ;;
  *)
    echo "[ERROR] Invalid mode: $MODE"
    usage
    ;;
esac

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


#
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

# LOGGING
LOG="$OUT_DIR/pipeline.log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

log "[INFO] Pipeline started"
log "[INFO] Mode: $MODE"

# THREADS
if [ -z "${THREADS:-}" ]; then
  NPROC=$(nproc)
  THREADS=$(( NPROC > 8 ? NPROC * 95 / 100 : NPROC ))
  [ "$THREADS" -lt 1 ] && THREADS=1
fi

log "[INFO] Threads: $THREADS"

# STEP RUNNER
run_step() {
  local STEP_NAME="$1"
  shift

  log "[INFO] Starting: $STEP_NAME"

  "$@" 2>&1 | while IFS= read -r line; do
    echo "$line"
    echo "[$STEP_NAME] $line" >> "$LOG"
  done

  local status=${PIPESTATUS[0]}

  if [ "$status" -ne 0 ]; then
    log "[ERROR] Failed: $STEP_NAME"
    return "$status"
  fi

  log "[INFO] Completed: $STEP_NAME"
}


# STEP 1: PREP (preparatory  step)
if [[ "$MODE" == "prep" || "$MODE" == "all" ]]; then

  log "[INFO] Scanning genomes..."

  mapfile -t GENOME_FILES < <(find "$INPUT_DIR" -maxdepth 1 -type f \
    \( -iname "*.fna" -o -iname "*.fa" -o -iname "*.fasta" \))

  [ "${#GENOME_FILES[@]}" -eq 0 ] && { log "[ERROR] No genomes found"; exit 1; }
  
  log "[INFO] Copying genomes..."
  rm -rf "$GENOMES"/*
  for f in "${GENOME_FILES[@]}"; do
    cp "$f" "$GENOMES/"
  done

  run_step "PREPARATION" \
    python3 -u "$MODULE_DIR/preperator.py" \
      --input "$GENOMES" \
      --output "$PREP" \
      --outgroup "$OUTGROUP" \
      --threads "$THREADS"
fi

# STEP 2: SIGNATURE GENE FINDING
if [[ "$MODE" == "signature" || "$MODE" == "all" ]]; then

  if [[ "$MODE" == "signature" then
    [ ! -f "$PREP/pangenome/pan_matrix_binary.tsv" ] && { log "[ERROR] PREP incomplete, Required files missing"; exit 1; }
    exit 1
  fi

  PAN_MATRIX="$PREP/pangenome/pan_matrix_binary.tsv"
  PHYLOGROUPS="$PREP/phylogroups.csv"
  ANNOTATIONS="$PREP/pangenome/og_annotations.tsv"

  [ ! -f "$PAN_MATRIX" ] && { log "[ERROR] Missing pan_matrix"; exit 1; }
  [ ! -f "$PHYLOGROUPS" ] && { log "[ERROR] Missing phylogroups"; exit 1; }
  [ ! -f "$ANNOTATIONS" ] && { log "[ERROR] Missing annotations"; exit 1; }

  run_step "SIGNATURE" \
    python3 -u "$MODULE_DIR/signaturegenefinder.py" \
      --pan_matrix "$PAN_MATRIX" \
      --phylogroups "$PHYLOGROUPS" \
      --annotations "$ANNOTATIONS" \
      --outdir "$RESULTS" \
      --mode full
fi

log "[DONE] Pipeline completed"
