from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import chat, dashboard, export, render, terminal, tree


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# Static files
app.mount("/static", StaticFiles(directory=str(settings.BASE_DIR / "app" / "static")), name="static")
app.mount("/renders", StaticFiles(directory=str(settings.RENDER_DIR)), name="renders")

# Routers
app.include_router(dashboard.router)
app.include_router(tree.router)
app.include_router(chat.router)
app.include_router(render.router)
app.include_router(export.router)
app.include_router(terminal.router)
