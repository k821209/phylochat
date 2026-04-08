#!/bin/bash
# PhyloChat Setup Script
# Creates conda environment with Python + R + ggtree

set -e

echo "==================================="
echo "  PhyloChat Setup"
echo "==================================="
echo ""

# Check conda
if ! command -v conda &> /dev/null; then
    echo "❌ conda not found. Install Miniconda first:"
    echo "   https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create conda environment
ENV_NAME="phylochat"

if conda env list | grep -q "^${ENV_NAME} "; then
    echo "⚠️  Environment '${ENV_NAME}' already exists."
    read -p "Recreate it? (y/N): " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        conda env remove -n ${ENV_NAME} -y
    else
        echo "Updating existing environment..."
        conda env update -n ${ENV_NAME} -f environment.yml --prune
        echo ""
        echo "✅ Environment updated. Run: ./start.sh"
        exit 0
    fi
fi

echo "📦 Creating conda environment '${ENV_NAME}'..."
echo "   (This may take a few minutes for R + Bioconductor packages)"
echo ""

conda env create -f environment.yml

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start PhyloChat:"
echo "  ./start.sh"
echo ""
echo "Or manually:"
echo "  conda activate ${ENV_NAME}"
echo "  python run.py"
echo ""
