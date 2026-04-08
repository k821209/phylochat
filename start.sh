#!/bin/bash
# PhyloChat Start Script

set -e

ENV_NAME="phylochat"
PORT=${PHYLOCHAT_PORT:-8008}

# Check conda environment exists
if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo "❌ Environment '${ENV_NAME}' not found. Run setup first:"
    echo "   ./setup.sh"
    exit 1
fi

# Activate environment
eval "$(conda shell.bash hook)"
conda activate ${ENV_NAME}

# Check R + ggtree
echo "Checking R + ggtree..."
if Rscript -e 'library(ggtree); cat("OK\n")' 2>/dev/null | grep -q "OK"; then
    echo "✅ R + ggtree ready"
else
    echo "⚠️  R or ggtree not available. Tree rendering will be limited to D3.js view."
    echo "   To fix: conda install -c bioconda bioconductor-ggtree"
fi

echo ""
echo "🌳 Starting PhyloChat on http://localhost:${PORT}"
echo "   Press Ctrl+C to stop"
echo ""

python run.py
