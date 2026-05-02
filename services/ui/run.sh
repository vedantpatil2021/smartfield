#!/bin/bash
# Smartfield Dashboard — environment setup and launcher
# Usage: bash services/ui/run.sh

set -e

ENV_NAME="smartfield"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── locate conda ──────────────────────────────────────────────────────────────
if [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
else
    echo "[ERROR] conda not found. Install Anaconda or Miniconda first."
    exit 1
fi

# ── create env if it doesn't exist ───────────────────────────────────────────
if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo "[*] Creating conda environment: ${ENV_NAME} (Python 3.10)"
    conda create -y -n "$ENV_NAME" python=3.10
fi

conda activate "$ENV_NAME"
echo "[*] Active environment: $CONDA_DEFAULT_ENV"

# ── system deps (vlc + Qt XCB libs) ──────────────────────────────────────────
echo "[*] Installing system dependencies..."
sudo apt-get install -y --no-install-recommends \
    vlc \
    libvlc-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 2>/dev/null || true

# ── pip dependencies ──────────────────────────────────────────────────────────
echo "[*] Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"

# ── launch ────────────────────────────────────────────────────────────────────
echo "[*] Launching Smartfield Dashboard..."
cd "$(dirname "$SCRIPT_DIR")" && cd ..   # run from smartfield root so relative paths resolve
python3 "$SCRIPT_DIR/dashboard.py"
