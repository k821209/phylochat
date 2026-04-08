from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.config import settings
from app.database import get_db
from app.models.schemas import TreeData, TreeUploadResponse
from app.services.newick_parser import get_tree_info, parse_newick

router = APIRouter(prefix="/tree", tags=["tree"])


@router.post("/upload", response_model=TreeUploadResponse)
async def upload_tree(
    file: UploadFile | None = File(None),
    newick_text: str | None = Form(None),
):
    if file:
        content = (await file.read()).decode("utf-8").strip()
        filename = file.filename
    elif newick_text:
        content = newick_text.strip()
        filename = "pasted.nwk"
    else:
        raise ValueError("Provide either a file or newick_text")

    info = get_tree_info(content)

    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO sessions (name) VALUES (?)", (filename,)
        )
        session_id = cursor.lastrowid

        cursor = await db.execute(
            "INSERT INTO tree_files (session_id, filename, newick) VALUES (?, ?, ?)",
            (session_id, filename, content),
        )
        tree_id = cursor.lastrowid
        await db.commit()
    finally:
        await db.close()

    # Save file to data/uploads/ so Claude Code can access it
    save_path = settings.UPLOAD_DIR / f"tree_{tree_id}_{filename}"
    save_path.write_text(content)

    return TreeUploadResponse(
        tree_id=tree_id,
        session_id=session_id,
        filename=filename,
        tip_count=info["tip_count"],
    )


@router.get("/{tree_id}/data", response_model=TreeData)
async def get_tree_data(tree_id: int):
    db = await get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT id, newick FROM tree_files WHERE id = ?", (tree_id,)
        )
        if not row:
            raise ValueError(f"Tree {tree_id} not found")
        newick = row[0][1]
    finally:
        await db.close()

    tree_json = parse_newick(newick)
    return TreeData(tree_id=tree_id, newick=newick, tree_json=tree_json)


@router.get("/{tree_id}/info")
async def get_tree_info_endpoint(tree_id: int):
    db = await get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT newick FROM tree_files WHERE id = ?", (tree_id,)
        )
        if not row:
            raise ValueError(f"Tree {tree_id} not found")
    finally:
        await db.close()

    return get_tree_info(row[0][0])


@router.get("/list/all")
async def list_trees():
    """Return all uploaded trees."""
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT id, filename, uploaded_at FROM tree_files ORDER BY id DESC"
        )
        return [
            {"tree_id": r[0], "filename": r[1], "uploaded_at": r[2]}
            for r in rows
        ]
    finally:
        await db.close()


@router.delete("/{tree_id}")
async def delete_tree(tree_id: int):
    db = await get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT filename FROM tree_files WHERE id = ?", (tree_id,)
        )
        if not row:
            raise ValueError(f"Tree {tree_id} not found")

        # Delete file from disk
        filename = row[0][0]
        file_path = settings.UPLOAD_DIR / f"tree_{tree_id}_{filename}"
        if file_path.exists():
            file_path.unlink()

        await db.execute("DELETE FROM chat_messages WHERE tree_id = ?", (tree_id,))
        await db.execute("DELETE FROM render_history WHERE tree_id = ?", (tree_id,))
        await db.execute("DELETE FROM tree_files WHERE id = ?", (tree_id,))
        await db.commit()

        return {"deleted": tree_id}
    finally:
        await db.close()
