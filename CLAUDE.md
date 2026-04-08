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

## Conventions

- Python 3.11, type hints
- Async FastAPI handlers
- R code executed via `subprocess.run(["Rscript", ...])`
- Local-only app, no auth needed
