#!/usr/bin/env bash

set -e

usage() {
  echo "Signaturegenefinder"
  echo ""
  echo "Usage:"
  echo " Signature-gene-finder.sh -i <genome_dir> -o <output_dir> -g <outgroup_name> -t <threads> "
  echo ""
  exit 1
}

while getopts "i:o:g:" opt; do
  case $opt in
    i) INPUT_DIR="$OPTARG" ;;
    o) OUT_DIR="$OPTARG" ;;
    g) OUTGROUP="$OPTARG" ;;
    t) THREADS="$OPTARG" ;;
    *) usage ;;
  esac
done

[ -z "$INPUT_DIR" ] && usage
[ -z "$OUT_DIR" ] && usage
[ -z "$OUTGROUP" ] && usage
[ -z "$THREADS" ] && usage

export GENOMES="$OUT_DIR/GENOMES"
export PREP="$OUT_DIR/PREP"
mkdir -p "$OUT_DIR" "$GENOMEs"
cp -r "$INPUT_DIR" "$GENOMEs" "$PREP"

echo "[INFO] Starting preparation of Genomes for Signature gene finding operation." 
python3 -u preperator.py \
  --input "$GENOMEs" \
  --output "$PREP" \
  --outgroup "$OUTGROUP" \
  --threads "$THREADS"

echo "[INFO] Starting Signature gene finding operation."
