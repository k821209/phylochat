"""Execute ggtree R code via Rscript subprocess."""

import subprocess
import tempfile
import uuid
from pathlib import Path

from app.config import settings


def render_ggtree(newick: str, r_code: str, output_format: str = "png") -> Path:
    """Run ggtree R code and return path to rendered image."""
    render_id = uuid.uuid4().hex[:12]
    ext = "svg" if output_format == "svg" else "png"
    output_path = settings.RENDER_DIR / f"{render_id}.{ext}"

    # Write newick to temp file
    newick_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".nwk", delete=False, dir=settings.RENDER_DIR
    )
    newick_file.write(newick)
    newick_file.close()

    # Build full R script
    full_script = _build_r_script(newick_file.name, str(output_path), r_code, output_format)

    script_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".R", delete=False, dir=settings.RENDER_DIR
    )
    script_file.write(full_script)
    script_file.close()

    try:
        result = subprocess.run(
            [settings.RSCRIPT_PATH, script_file.name],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"R execution failed:\n{result.stderr}")

        # Clean up temp files
        Path(newick_file.name).unlink(missing_ok=True)
        Path(script_file.name).unlink(missing_ok=True)

        return output_path
    except subprocess.TimeoutExpired:
        raise RuntimeError("R execution timed out (60s)")


def _build_r_script(newick_path: str, output_path: str, user_code: str, fmt: str) -> str:
    """Build a complete R script wrapping user's ggtree code."""
    device = "svg" if fmt == "svg" else "png"
    dpi_line = "" if fmt == "svg" else ", dpi = 300"

    return f"""
suppressPackageStartupMessages({{
  library(ggtree)
  library(treeio)
  library(ggplot2)
}})

tree <- read.newick("{newick_path}")

# User code starts here
{user_code}
# User code ends here

# If user code didn't assign to 'p', create default plot
if (!exists("p")) {{
  p <- ggtree(tree) + geom_tiplab()
}}

ggsave("{output_path}", plot = p, device = "{device}"{dpi_line}, width = 10, height = 8)
"""


def check_r_available() -> bool:
    """Check if Rscript is available and ggtree is installed."""
    try:
        result = subprocess.run(
            [settings.RSCRIPT_PATH, "-e", 'library(ggtree); cat("OK")'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0 and "OK" in result.stdout
    except Exception:
        return False
