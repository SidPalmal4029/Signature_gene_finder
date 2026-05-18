#!/usr/bin/env bash
set -euo pipefail

# CONFIGURATION AND USER MODE FOR FRESH INSTALLATION AS WELL SELECTED UPGRADES

ENV_NAME="SignatureGeneFinder"
MODE="${MODE:-create}"   # create | use | upgrade
LOG_FILE="install_$(date +%Y%m%d_%H%M%S).log"

CONFIG="config/install_config.yaml"
[ -f "$CONFIG" ] || CONFIG="conda.yaml"

# LOGGING (clean UI + full log)

exec 3>&1 4>&2
exec 1>>"$LOG_FILE" 2>&1

log() { echo -e "$1" >&3; }
section() { echo -e "\n=== $1 ===" >&3; }

trap 'log "[ERROR] Installation failed. Check log: $LOG_FILE"' ERR
log "[INFO] Starting installation"
log "[INFO] Log file: $LOG_FILE"

#  VALIDATION OF DOWNLOADED REPOSITORY
section "Validating repository"

MISSING=0
check_file() { [ -f "$1" ] || { log "[ERROR] Missing $1"; MISSING=1; }; }
check_dir()  { [ -d "$1" ] || { log "[ERROR] Missing $1"; MISSING=1; }; }

check_file "signature-gene-finder.sh"
check_dir "module"
check_file "module/preperator.py"
check_file "module/signaturegenefinder.py"
check_dir "module/Worker"

[ "$MISSING" -eq 1 ] && exit 1
log "[OK] Repository valid"

# 2. ENVIRONMENT HANDLING

section "Environment setup"

source "$(conda info --base)/etc/profile.d/conda.sh"

if [ "$MODE" = "create" ]; then

  if conda env list | grep -q "^$ENV_NAME "; then
    log "[INFO] Using existing env: $ENV_NAME"
  else
    log "[INFO] Creating env: $ENV_NAME"
    conda create -y -n "$ENV_NAME" python=3.12
  fi

  conda activate "$ENV_NAME"

elif [ "$MODE" = "use" ]; then

  [ -z "${CONDA_PREFIX:-}" ] && {
    log "[ERROR] Activate env first"
    exit 1
  }

  log "[INFO] Using active env: $CONDA_PREFIX"

elif [ "$MODE" = "upgrade" ]; then

  if conda env list | grep -q "^$ENV_NAME "; then
    conda activate "$ENV_NAME"
    log "[INFO] Upgrading env: $ENV_NAME"
  else
    log "[ERROR] Env not found"
    exit 1
  fi
fi

# Prevent base install
if [[ "$CONDA_PREFIX" == *"/base" && "$MODE" != "use" ]]; then
  log "[ERROR] Refusing to install into base"
  exit 1
fi

#  PARSE YAML

section "Parsing configuration"

parse_block() {
  local start="$1" stop="$2"
  awk -v s="$start" -v e="$stop" '
    $0 ~ s {flag=1; next}
    $0 ~ e {flag=0}
    flag && $0 ~ /^[[:space:]]*-/ {
      gsub(/^[[:space:]]*-[[:space:]]*/, "", $0)
      print
    }
  ' "$CONFIG"
}

CONDA_DEPS=$(parse_block "conda:" "pip:")
mapfile -t REQUIRED_TOOLS < <(parse_block "required_tools:" "optional_tools:")
mapfile -t OPTIONAL_TOOLS < <(parse_block "optional_tools:" "databases:")

[ -z "$CONDA_DEPS" ] && { log "[ERROR] No dependencies found"; exit 1; }

#  INSTALL DEPENDENCIES

section "Installing dependencies"

mamba install -y \
  -c conda-forge \
  -c bioconda \
  --strict-channel-priority \
  $CONDA_DEPS

log "[OK] Dependencies installed"

# DFAST DATABASE

section "Setting up DFAST DB"

if command -v dfast_file_downloader.py >/dev/null 2>&1; then

  DB="$CONDA_PREFIX/share/dfast"

  if [ -d "$DB" ] && find "$DB" -type f | grep -q .; then
    log "[OK] DFAST DB present"
  else
    log "[INFO] Downloading DFAST DB..."
    dfast_file_downloader.py --protein dfast --cdd Cog --hmm TIGR
  fi
else
  log "[ERROR] dfast downloader missing"
  exit 1
fi

#  DEPLOY

section "Deploying pipeline"

BASE="$CONDA_PREFIX"
BIN="$BASE/bin"
SHARE="$BASE/share/SignatureGeneFinder"

mkdir -p "$SHARE"

cp -r module "$SHARE/"
cp signature-gene-finder.sh "$SHARE/"
[ -f help.txt ] && cp help.txt "$SHARE/"

ln -sf "$SHARE/signature-gene-finder.sh" "$BIN/Signature-gene-finder"
chmod +x "$SHARE/signature-gene-finder.sh"

# install stamp
cat > "$SHARE/install.meta" <<EOF
version=1.0
date=$(date)
env=$CONDA_PREFIX
EOF

log "[OK] Deployment complete"

# VALIDATION

section "Validating tools"

normalize() {
  case "$1" in
    python3) echo "python" ;;
    *) echo "$1" ;;
  esac
}

FAILED=0

for tool in "${REQUIRED_TOOLS[@]:-}"; do
  t=$(normalize "$tool")
  command -v "$t" >/dev/null 2>&1 \
    && log "[OK] $tool" \
    || { log "[FAIL] $tool"; FAILED=1; }
done

# SANITY TESTS

section "Running tests"

run_test() {
  eval "$1" >/dev/null 2>&1 \
    && log "[OK] $1" \
    || log "[WARN] $1"
}

run_test "get_homologues.pl -h"
run_test "fastANI --help"
run_test "diamond help"
run_test "mmseqs -h"
run_test "java -version"

# FINAL

if [ "$FAILED" -eq 1 ]; then
  log "[ERROR] Installation incomplete"
  exit 1
fi

log "[SUCCESS] Installation complete"
log "Run: Signature-gene-finder -h"
