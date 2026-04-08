from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import settings
from app.database import get_db
from app.services.r_executor import render_ggtree

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/figure")
async def export_figure(tree_id: int, format: str = "png", dpi: int = 300):
    db = await get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT newick FROM tree_files WHERE id = ?", (tree_id,)
        )
        if not row:
            raise ValueError(f"Tree {tree_id} not found")
        newick = row[0][0]

        # Get latest R code
        code_row = await db.execute_fetchall(
            "SELECT r_code FROM render_history WHERE tree_id = ? ORDER BY id DESC LIMIT 1",
            (tree_id,),
        )
        r_code = code_row[0][0] if code_row else "p <- ggtree(tree) + geom_tiplab()"

        output_path = render_ggtree(newick, r_code, format)
        media = "image/svg+xml" if format == "svg" else "image/png"

        return FileResponse(
            output_path,
            media_type=media,
            filename=f"phylochat_tree.{format}",
        )
    finally:
        await db.close()


@router.get("/code/{tree_id}")
async def export_code(tree_id: int):
    db = await get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT newick FROM tree_files WHERE id = ?", (tree_id,)
        )
        if not row:
            raise ValueError(f"Tree {tree_id} not found")

        code_row = await db.execute_fetchall(
            "SELECT r_code FROM render_history WHERE tree_id = ? ORDER BY id DESC LIMIT 1",
            (tree_id,),
        )
        r_code = code_row[0][0] if code_row else "p <- ggtree(tree) + geom_tiplab()"

        return {
            "tree_id": tree_id,
            "r_code": r_code,
            "newick": row[0][0],
        }
    finally:
        await db.close()
