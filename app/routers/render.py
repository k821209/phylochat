import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import settings
from app.database import get_db
from app.models.schemas import RenderRequest, RenderResponse
from app.services.r_executor import render_ggtree

router = APIRouter(prefix="/render", tags=["render"])


@router.post("/ggtree", response_model=RenderResponse)
async def render_ggtree_endpoint(req: RenderRequest):
    db = await get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT newick FROM tree_files WHERE id = ?", (req.tree_id,)
        )
        if not row:
            raise ValueError(f"Tree {req.tree_id} not found")
        newick = row[0][0]

        output_path = render_ggtree(newick, req.r_code, "png")

        await db.execute(
            "INSERT INTO render_history (tree_id, r_code, render_path) VALUES (?, ?, ?)",
            (req.tree_id, req.r_code, str(output_path)),
        )
        await db.commit()

        return RenderResponse(
            render_url=f"/renders/{output_path.name}",
            r_code=req.r_code,
        )
    finally:
        await db.close()


@router.get("/latest")
async def get_latest_render():
    """Return the most recent render file info. Polled by the frontend."""
    render_dir = settings.RENDER_DIR
    if not render_dir.exists():
        return {"file": None}

    files = [
        f for f in render_dir.iterdir()
        if f.suffix in (".png", ".svg", ".pdf") and not f.name.startswith(".")
    ]
    if not files:
        return {"file": None}

    latest = max(files, key=lambda f: f.stat().st_mtime)
    return {
        "file": latest.name,
        "url": f"/renders/{latest.name}",
        "mtime": latest.stat().st_mtime,
    }


@router.get("/list")
async def list_renders():
    """Return all renders sorted by newest first."""
    render_dir = settings.RENDER_DIR
    if not render_dir.exists():
        return []

    files = [
        f for f in render_dir.iterdir()
        if f.suffix in (".png", ".svg", ".pdf") and not f.name.startswith(".")
    ]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    return [
        {
            "file": f.name,
            "url": f"/renders/{f.name}",
            "mtime": f.stat().st_mtime,
            "size": f.stat().st_size,
            "ext": f.suffix[1:],
        }
        for f in files
    ]


@router.post("/associate")
async def associate_render(filename: str, tree_id: int):
    """Associate a render file with a tree (called by frontend when new render detected)."""
    file_path = settings.RENDER_DIR / filename
    if not file_path.exists():
        raise ValueError(f"Render {filename} not found")

    db = await get_db()
    try:
        # Check if already associated
        existing = await db.execute_fetchall(
            "SELECT id FROM render_history WHERE render_path = ?", (filename,)
        )
        if not existing:
            await db.execute(
                "INSERT INTO render_history (tree_id, r_code, render_path) VALUES (?, '', ?)",
                (tree_id, filename),
            )
            await db.commit()
        return {"associated": filename, "tree_id": tree_id}
    finally:
        await db.close()


@router.get("/by-tree")
async def list_renders_by_tree():
    """Return renders grouped by tree file."""
    # Get all renders from filesystem
    render_dir = settings.RENDER_DIR
    fs_files = {}
    if render_dir.exists():
        for f in render_dir.iterdir():
            if f.suffix in (".png", ".svg", ".pdf") and not f.name.startswith("."):
                fs_files[f.name] = {
                    "file": f.name,
                    "url": f"/renders/{f.name}",
                    "mtime": f.stat().st_mtime,
                    "ext": f.suffix[1:],
                }

    # Get associations from DB
    db = await get_db()
    try:
        rows = await db.execute_fetchall("""
            SELECT rh.render_path, rh.tree_id, tf.filename as tree_filename
            FROM render_history rh
            LEFT JOIN tree_files tf ON rh.tree_id = tf.id
            ORDER BY rh.created_at DESC
        """)

        grouped = {}
        associated = set()
        for row in rows:
            render_name = row[0]
            tree_id = row[1]
            tree_filename = row[2] or "Unknown"

            if render_name not in fs_files:
                continue

            associated.add(render_name)
            key = f"{tree_id}"
            if key not in grouped:
                grouped[key] = {
                    "tree_id": tree_id,
                    "tree_filename": tree_filename,
                    "renders": [],
                }
            grouped[key]["renders"].append(fs_files[render_name])

        # Unassociated renders
        unassociated = [
            fs_files[name] for name in fs_files if name not in associated
        ]
        unassociated.sort(key=lambda r: r["mtime"], reverse=True)

        return {
            "grouped": list(grouped.values()),
            "unassociated": unassociated,
        }
    finally:
        await db.close()


@router.get("/code/{filename}")
async def get_render_code(filename: str):
    """Return the R code used to generate a specific render."""
    db = await get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT r_code FROM render_history WHERE render_path = ?", (filename,)
        )
        if not row or not row[0][0]:
            return {"r_code": None}
        return {"r_code": row[0][0], "filename": filename}
    finally:
        await db.close()


@router.delete("/renders/{filename}")
async def delete_render(filename: str):
    file_path = settings.RENDER_DIR / filename
    if file_path.exists():
        file_path.unlink()

    db = await get_db()
    try:
        await db.execute("DELETE FROM render_history WHERE render_path = ?", (filename,))
        await db.commit()
    finally:
        await db.close()

    return {"deleted": filename}


@router.get("/renders/{filename}")
async def serve_render(filename: str):
    file_path = settings.RENDER_DIR / filename
    if not file_path.exists():
        raise ValueError(f"Render {filename} not found")
    media = "image/svg+xml" if filename.endswith(".svg") else "image/png"
    return FileResponse(file_path, media_type=media)
