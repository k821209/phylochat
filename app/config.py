import os
import shutil
import subprocess
from pathlib import Path

from pydantic_settings import BaseSettings


def _find_conda_rscript() -> str:
    """Find Rscript in the phylochat conda environment."""
    # Try CONDA_PREFIX first (set when env is active)
    prefix = os.environ.get("CONDA_PREFIX")
    if prefix:
        candidate = Path(prefix) / "bin" / "Rscript"
        if candidate.exists():
            return str(candidate)

    # Try `conda info --base` to find conda root, then look in envs/phylochat
    try:
        result = subprocess.run(
            ["conda", "info", "--base"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            base = Path(result.stdout.strip())
            candidate = base / "envs" / "phylochat" / "bin" / "Rscript"
            if candidate.exists():
                return str(candidate)
    except Exception:
        pass

    return "Rscript"


class Settings(BaseSettings):
    APP_NAME: str = "PhyloChat"
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = DATA_DIR / "phylochat.db"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    RENDER_DIR: Path = DATA_DIR / "renders"
    EXPORT_DIR: Path = DATA_DIR / "exports"
    RSCRIPT_PATH: str = shutil.which("Rscript") or _find_conda_rscript()

    def ensure_dirs(self):
        for d in [self.UPLOAD_DIR, self.RENDER_DIR, self.EXPORT_DIR]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
