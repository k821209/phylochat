#!/bin/bash
# PhyloChat Setup Script
# Prerequisite: Claude Code CLI must be installed and logged in.

set -e

echo "==================================="
echo "  PhyloChat Setup"
echo "==================================="
echo ""

# ── 1. Check Claude Code CLI ─────────────────────────
if ! command -v claude &> /dev/null; then
    echo "[ERROR] Claude Code CLI not found."
    echo ""
    echo "  Install:"
    echo "    npm install -g @anthropic-ai/claude-code"
    echo ""
    echo "  Then log in:"
    echo "    claude login"
    echo ""
    echo "  After login, re-run this script."
    exit 1
fi
echo "[OK] Claude Code CLI found: $(which claude)"

# ── 2. Check conda ───────────────────────────────────
if ! command -v conda &> /dev/null; then
    echo "[ERROR] conda not found."
    echo ""
    echo "  Install Miniconda:"
    echo "    https://docs.anaconda.com/miniconda/install/"
    echo ""
    echo "  After installation, re-run this script."
    exit 1
fi
echo "[OK] conda found: $(which conda)"

# ── 3. Create conda environment ──────────────────────
ENV_NAME="phylochat"

if conda env list | grep -q "^${ENV_NAME} "; then
    echo "[OK] Environment '${ENV_NAME}' already exists."
    read -p "     Recreate it? (y/N): " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        conda env remove -n ${ENV_NAME} -y
    else
        echo "     Updating existing environment..."
        conda env update -n ${ENV_NAME} -f environment.yml --prune
        echo "[OK] Environment updated."
        echo ""
    fi
fi

if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo "[..] Creating conda environment '${ENV_NAME}'..."
    echo "     (This may take a few minutes for R + Bioconductor packages)"
    echo ""
    conda env create -f environment.yml
    echo "[OK] Environment created."
fi

# ── 4. Verify R packages ────────────────────────────
echo "[..] Verifying R packages..."
CONDA_BASE=$(conda info --base)
RSCRIPT="${CONDA_BASE}/envs/${ENV_NAME}/bin/Rscript"

if [ ! -f "$RSCRIPT" ]; then
    echo "[ERROR] Rscript not found in conda env."
    echo "        Try removing and re-creating the environment."
    exit 1
fi

$RSCRIPT -e '
pkgs <- c("ggtree", "ggplot2", "treeio")
missing <- pkgs[!sapply(pkgs, requireNamespace, quietly = TRUE)]
if (length(missing) > 0) {
    cat("[ERROR] Missing R packages:", paste(missing, collapse = ", "), "\n")
    quit(status = 1)
} else {
    cat("[OK] R packages verified: ggtree, ggplot2, treeio\n")
}
'

# ── 5. Create data directories ──────────────────────
mkdir -p data/{uploads,renders,exports}
echo "[OK] Data directories ready."

# ── 6. Generate .mcp.json for Claude Code ───────────
PROJECT_DIR=$(pwd)
PYTHON_PATH="${CONDA_BASE}/envs/${ENV_NAME}/bin/python"
CONDA_BIN="${CONDA_BASE}/envs/${ENV_NAME}/bin"

cat > .mcp.json << MCPEOF
{
  "mcpServers": {
    "phylochat": {
      "command": "${PYTHON_PATH}",
      "args": ["-m", "app.mcp.server"],
      "cwd": "${PROJECT_DIR}",
      "env": {
        "PATH": "${CONDA_BIN}:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
MCPEOF
echo "[OK] .mcp.json generated."

# ── 7. Done ─────────────────────────────────────────
echo ""
echo "==================================="
echo "  Setup complete!"
echo "==================================="
echo ""
echo "  To start PhyloChat:"
echo ""
echo "    conda activate ${ENV_NAME}"
echo "    python run.py"
echo ""
echo "  Server: http://localhost:8008"
echo ""
