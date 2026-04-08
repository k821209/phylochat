# PhyloChat

AI-powered phylogenetic tree editor. Natural language → ggtree (R) code generation → publication-quality figures.

## Setup

```bash
conda env create -f environment.yml
conda activate phylochat
python run.py
```

Server runs at http://localhost:8000

## Stack

- **Backend**: FastAPI + Jinja2 (no SPA)
- **Tree Viewer**: D3.js (interactive, client-side)
- **Figure Rendering**: ggtree/ggplot2 via Rscript subprocess
- **Database**: SQLite (aiosqlite)
- **Chat**: Claude Code harness integration

## Project Structure

- `app/` — FastAPI application
  - `routers/` — API endpoints (dashboard, tree, chat, render, export)
  - `services/` — Business logic (newick_parser, r_executor, chat_harness)
  - `models/` — Pydantic models
  - `templates/` — Jinja2 HTML templates
  - `static/` — CSS, JS, vendored libs
- `r_scripts/` — R script templates for ggtree rendering
- `data/` — SQLite DB, uploads, renders, exports
- `tests/` — pytest tests

## Rendering Rules

When generating and executing R scripts for tree rendering:

1. **Rscript path**: Always use `/Users/yangjaekang/miniconda3/envs/phylochat/bin/Rscript`
2. **Save R script alongside image**: When saving a rendered PNG to `data/renders/`, also save the R script with the same basename and `.R` extension in the same directory. Example: `tree_15_colored_20260408.png` → `tree_15_colored_20260408.R`
3. **Output directory**: All renders go to `data/renders/`
4. **Style guide**: Follow `docs/tree_style_guide.md` for ggtree defaults

## Conventions

- Python 3.11, type hints
- Async FastAPI handlers
- R code executed via `subprocess.run(["Rscript", ...])`
- Local-only app, no auth needed
