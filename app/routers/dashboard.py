from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.r_executor import check_r_available

templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    r_available = check_r_available()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        context={
            "app_name": settings.APP_NAME,
            "r_available": r_available,
        },
    )
