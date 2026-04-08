import shutil
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "PhyloChat"
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = DATA_DIR / "phylochat.db"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    RENDER_DIR: Path = DATA_DIR / "renders"
    EXPORT_DIR: Path = DATA_DIR / "exports"
    RSCRIPT_PATH: str = shutil.which("Rscript") or "Rscript"

    def ensure_dirs(self):
        for d in [self.UPLOAD_DIR, self.RENDER_DIR, self.EXPORT_DIR]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
