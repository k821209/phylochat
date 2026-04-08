import asyncio
import json
import os
import re

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.database import get_db
from app.models.schemas import RenderRequest, RenderResponse
from app.services.r_executor import render_ggtree


def _extract_tree_id_from_filename(filename: str) -> int | None:
    """Extract tree_id from render filename like 'tree_15_xxx.png'."""
    m = re.match(r"tree_(\d+)_", filename)
    return int(m.group(1)) if m else None

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
            (req.tree_id, req.r_code, output_path.name),
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
async def associate_render(filename: str, tree_id: int | None = None):
    """Associate a render file with a tree. Auto-detects tree_id from filename if not provided."""
    file_path = settings.RENDER_DIR / filename
    if not file_path.exists():
        raise ValueError(f"Render {filename} not found")

    # Auto-detect tree_id from filename (e.g. tree_15_xxx.png → 15)
    if tree_id is None:
        tree_id = _extract_tree_id_from_filename(filename)
    if tree_id is None:
        return {"associated": False, "reason": "Cannot determine tree_id"}

    db = await get_db()
    try:
        # Verify tree exists
        tree_row = await db.execute_fetchall(
            "SELECT id FROM tree_files WHERE id = ?", (tree_id,)
        )
        if not tree_row:
            return {"associated": False, "reason": f"Tree {tree_id} not found"}

        # Try to read R code from companion .R file (exact match or closest recent .R)
        r_code = ""
        r_file = file_path.with_suffix(".R")
        if r_file.exists():
            r_code = r_file.read_text(encoding="utf-8")
        else:
            # Find the most recent .R file with the same tree prefix
            prefix = f"tree_{tree_id}_"
            r_files = sorted(
                [f for f in settings.RENDER_DIR.iterdir()
                 if f.suffix == ".R" and f.name.startswith(prefix)],
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if r_files:
                r_code = r_files[0].read_text(encoding="utf-8")

        # Check if already associated
        existing = await db.execute_fetchall(
            "SELECT id, r_code FROM render_history WHERE render_path = ?", (filename,)
        )
        if existing:
            # Update r_code if it was empty and we now have it
            if r_code and not existing[0][1]:
                await db.execute(
                    "UPDATE render_history SET r_code = ? WHERE id = ?",
                    (r_code, existing[0][0]),
                )
                await db.commit()
        else:
            await db.execute(
                "INSERT INTO render_history (tree_id, r_code, render_path) VALUES (?, ?, ?)",
                (tree_id, r_code, filename),
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
        if row and row[0][0]:
            return {"r_code": row[0][0], "filename": filename}

        # Fallback: read companion .R file or most recent .R with same tree prefix
        file_path = settings.RENDER_DIR / filename
        r_file = file_path.with_suffix(".R")
        if r_file.exists():
            return {"r_code": r_file.read_text(encoding="utf-8"), "filename": filename}

        tree_id = _extract_tree_id_from_filename(filename)
        if tree_id:
            prefix = f"tree_{tree_id}_"
            r_files = sorted(
                [f for f in settings.RENDER_DIR.iterdir()
                 if f.suffix == ".R" and f.name.startswith(prefix)],
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if r_files:
                return {"r_code": r_files[0].read_text(encoding="utf-8"), "filename": filename}

        return {"r_code": None}
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


@router.get("/events")
async def render_events(request: Request):
    """SSE endpoint — push new render events to the frontend."""
    async def event_generator():
        db = await get_db()
        try:
            row = await db.execute_fetchall(
                "SELECT MAX(id) FROM render_history"
            )
            last_id = row[0][0] or 0
        finally:
            await db.close()

        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(1)

            db = await get_db()
            try:
                rows = await db.execute_fetchall(
                    "SELECT id, tree_id, render_path, created_at FROM render_history "
                    "WHERE id > ? ORDER BY id",
                    (last_id,),
                )
                for r in rows:
                    last_id = r[0]
                    yield {
                        "event": "new_render",
                        "data": json.dumps({
                            "render_id": r[0],
                            "tree_id": r[1],
                            "filename": r[2],
                            "url": f"/renders/{r[2]}",
                            "created_at": r[3],
                        }),
                    }
            finally:
                await db.close()

    return EventSourceResponse(event_generator())
