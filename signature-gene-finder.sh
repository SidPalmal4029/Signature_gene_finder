#!/usr/bin/env bash

set -e

usage() {
  echo "Signaturegenefinder"
  echo ""
  echo "Usage:"
  echo "  run_signaturegenefinder.sh -i <genome_dir> -o <output_dir> -g <outgroup_name>"
  echo ""
  exit 1
}

while getopts "i:o:g:" opt; do
  case $opt in
    i) INPUT_DIR="$OPTARG" ;;
    o) OUT_DIR="$OPTARG" ;;
    g) OUTGROUP="$OPTARG" ;;
    *) usage ;;
  esac
done

[ -z "$INPUT_DIR" ] && usage
[ -z "$OUT_DIR" ] && usage
[ -z "$OUTGROUP" ] && usage

mkdir -p "$OUT_DIR"

python3 signaturegenefinder.py \
  --input "$INPUT_DIR" \
  --output "$OUT_DIR" \
  --outgroup "$OUTGROUP"
