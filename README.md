# PhyloChat

AI-powered phylogenetic tree editor. Natural language to publication-quality figures via ggtree (R).

## Prerequisites

- **Claude Code CLI** — powers the AI chat interface
- **conda** (Miniconda or Anaconda) — manages Python + R dependencies

### 1. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Log in (one-time):

```bash
claude login
```

### 2. Install conda

If you don't have conda, install [Miniconda](https://docs.anaconda.com/miniconda/install/).

## Setup

```bash
git clone <repo-url>
cd phylochat
chmod +x setup.sh
./setup.sh
```

`setup.sh` will:
- Verify Claude Code CLI and conda are installed
- Create the `phylochat` conda environment (Python 3.11, R 4.3, ggtree)
- Verify R packages (ggtree, ggplot2, treeio)
- Create data directories

## Run

```bash
conda activate phylochat
python run.py
```

Open http://localhost:8008

## Usage

1. Upload a tree file (`.treefile`, `.nwk`, Newick format)
2. Chat with the AI to customize your visualization
3. Export publication-quality figures (PNG/SVG)

A sample tree is included at `tests/data/sample_primate_18tips.treefile` for testing.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `claude: command not found` | `npm install -g @anthropic-ai/claude-code && claude login` |
| `conda: command not found` | Install [Miniconda](https://docs.anaconda.com/miniconda/install/), restart terminal |
| `Rscript not found` | Run `./setup.sh` again — R is installed inside the conda env |
| R package errors during setup | `conda env remove -n phylochat -y && ./setup.sh` |
| Port 8008 in use | Edit `run.py` to change the port |
