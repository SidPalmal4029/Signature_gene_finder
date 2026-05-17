#!/usr/bin/env bash

set -euo pipefail

CONFIG="config/install_config.yaml"

echo "[INFO] Starting installation..."

# 1. VALIDATE REPOSITORY STRUCTURE
echo "[INFO] Validating repository structure..."

MISSING=0

check_file() {
  if [ ! -f "$1" ]; then
    echo "[ERROR] Missing file: $1"
    MISSING=1
  else
    echo "[OK] $1"
  fi
}

check_dir() {
  if [ ! -d "$1" ]; then
    echo "[ERROR] Missing directory: $1"
    MISSING=1
  else
    echo "[OK] $1"
  fi
}

# Root
check_file "signature-gene-finder.sh"
check_file "help.txt"

# YAML
if [ -f "$CONFIG" ]; then
  echo "[OK] $CONFIG"
elif [ -f "conda.yaml" ]; then
  CONFIG="conda.yaml"
  echo "[OK] conda.yaml"
else
  echo "[ERROR] No config YAML found"
  exit 1
fi

# Core
check_dir "module"
check_file "module/preperator.py"
check_file "module/signaturegenefinder.py"

# Worker
check_dir "module/Worker"

REQUIRED_WORKERS=(
  "Annotator_DFAST.py"
  "run_orthofinder.py"
  "phylogroup_builder.py"
  "pangenome.py"
  "ogri_calc.py"
  "signature_core.py"
)

for f in "${REQUIRED_WORKERS[@]}"; do
  check_file "module/Worker/$f"
done

WORKER_COUNT=$(find module/Worker -type f -name "*.py" | wc -l)

if [ "$WORKER_COUNT" -lt 8 ]; then
  echo "[ERROR] Too few worker modules ($WORKER_COUNT)"
  MISSING=1
else
  echo "[OK] Worker count: $WORKER_COUNT"
fi

if [ "$MISSING" -eq 1 ]; then
  echo "[ERROR] Repository validation failed"
  exit 1
fi

echo "[INFO] Repository validation passed"

# 2. CHECK CONDA ENV
if [ -z "${CONDA_PREFIX:-}" ]; then
  echo "[ERROR] No conda environment active"
  exit 1
fi

echo "[INFO] Using environment: $CONDA_PREFIX"

# 3. PARSE YAML (LIGHTWEIGHT)
parse_list() {
  grep -A50 "$1" "$CONFIG" | grep "-" | sed 's/.*- //'
}

CONDA_DEPS=$(parse_list "conda:")
REQUIRED_TOOLS=$(parse_list "required_tools:")
OPTIONAL_TOOLS=$(parse_list "optional_tools:")

# 4. INSTALL DEPENDENCIES
echo "[INFO] Installing dependencies..."

mamba install -y -c bioconda -c conda-forge $CONDA_DEPS

# 5. DEPLOY PIPELINE
BASE="$CONDA_PREFIX"
BIN="$CONDA_PREFIX/bin"
SHARE="$CONDA_PREFIX/share/SignatureGeneFinder"

echo "[INFO] Deploying to: $SHARE"
mkdir -p "$SHARE"

cp -r module "$SHARE/"
cp signature-gene-finder.sh "$SHARE/"

[ -f "help.txt" ] && cp help.txt "$SHARE/"

# Wrapper
ln -sf "$SHARE/signature-gene-finder.sh" "$BIN/Signature-gene-finder"
chmod +x "$SHARE/signature-gene-finder.sh"

# 6. VALIDATE TOOLS
echo "[INFO] Validating tools..."

FAILED=0

check_tool() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "[OK] $1"
  else
    echo "[FAIL] $1"
    FAILED=1
  fi
}

for tool in $REQUIRED_TOOLS; do
  check_tool "$tool"
done

echo "[INFO] Checking optional tools..."

for tool in $OPTIONAL_TOOLS; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "[OK] $tool"
  else
    echo "[WARN] Missing optional tool: $tool"
  fi
done

# 6. DFAST DATABASE SETUP 
echo "[INFO] Setting up DFAST databases..."

if command -v dfast_file_downloader.py >/dev/null 2>&1; then

  DFAST_DB_DIR="$CONDA_PREFIX/share/dfast"

  # Check for actual DB content (not just folder)
  if [ -d "$DFAST_DB_DIR" ] && find "$DFAST_DB_DIR" -type f | grep -q .; then
    echo "[INFO] DFAST DB already present, skipping download"
  else
    echo "[INFO] Downloading DFAST DB (protein + COG + TIGR)..."

    if dfast_file_downloader.py \
        --protein dfast \
        --cdd Cog \
        --hmm TIGR; then

      echo "[OK] DFAST DB setup complete."
    else
      echo "[ERROR] DFAST DB setup failed."
      exit 1
    fi
  fi

else
  echo "[ERROR] dfast_file_downloader.py not found"
  exit 1
fi


# 7. JAVA CHECK (EzAAI)
echo "[INFO] Checking Java..."

JAVA_VER=$(java -version 2>&1 | head -n 1 || true)
echo "[INFO] $JAVA_VER"

if [[ "$JAVA_VER" != *"1.8"* ]]; then
  echo "[WARNING] Java 8 recommended for EzAAI"
fi

# 8. TEST COMMANDS
echo "[INFO] Running sanity tests..."

run_test() {
  if eval "$1" >/dev/null 2>&1; then
    echo "[OK] $1"
  else
    echo "[WARN] Failed: $1"
  fi
}

run_test "get_homologues.pl -h"
run_test "fastANI --help"
run_test "diamond help"
run_test "mmseqs -h"
run_test "java -version"

# FINAL
if [ "$FAILED" -eq 1 ]; then
  echo "[ERROR] Installation incomplete"
  exit 1
fi

echo ""
echo "[SUCCESS] Installation complete"
echo "Run: Signature-gene-finder -h"
