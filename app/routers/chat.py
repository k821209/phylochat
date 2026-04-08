from fastapi import APIRouter

from app.database import get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_harness import generate_ggtree_code
from app.services.newick_parser import get_tree_info
from app.services.r_executor import render_ggtree

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send", response_model=ChatResponse)
async def send_message(req: ChatRequest):
    db = await get_db()
    try:
        # Get tree data
        row = await db.execute_fetchall(
            "SELECT newick FROM tree_files WHERE id = ?", (req.tree_id,)
        )
        if not row:
            raise ValueError(f"Tree {req.tree_id} not found")
        newick = row[0][0]

        # Get current R code (latest render)
        code_row = await db.execute_fetchall(
            "SELECT r_code FROM render_history WHERE tree_id = ? ORDER BY id DESC LIMIT 1",
            (req.tree_id,),
        )
        current_code = code_row[0][0] if code_row else ""

        # Save user message
        cursor = await db.execute(
            "INSERT INTO chat_messages (session_id, tree_id, role, content) VALUES (?, ?, 'user', ?)",
            (req.session_id, req.tree_id, req.message),
        )
        await db.commit()

        # Generate ggtree code via Claude
        tree_info = get_tree_info(newick)
        result = await generate_ggtree_code(req.message, tree_info, current_code)

        render_url = None
        r_code = result.get("r_code")

        # Execute R code if generated
        if r_code:
            try:
                output_path = render_ggtree(newick, r_code, "png")
                render_url = f"/renders/{output_path.name}"

                # Save render history — upsert in case polling already created the row
                existing = await db.execute_fetchall(
                    "SELECT id FROM render_history WHERE render_path = ?",
                    (output_path.name,),
                )
                if existing:
                    await db.execute(
                        "UPDATE render_history SET r_code = ? WHERE render_path = ?",
                        (r_code, output_path.name),
                    )
                else:
                    await db.execute(
                        "INSERT INTO render_history (tree_id, r_code, render_path) VALUES (?, ?, ?)",
                        (req.tree_id, r_code, output_path.name),
                    )
                await db.commit()
            except RuntimeError as e:
                result["explanation"] += f"\n\n⚠️ R execution error: {e}"

        # Save assistant message
        cursor = await db.execute(
            "INSERT INTO chat_messages (session_id, tree_id, role, content, r_code, render_path) VALUES (?, ?, 'assistant', ?, ?, ?)",
            (req.session_id, req.tree_id, result["explanation"], r_code, render_url),
        )
        msg_id = cursor.lastrowid
        await db.commit()

        return ChatResponse(
            message_id=msg_id,
            role="assistant",
            content=result["explanation"],
            r_code=r_code,
            render_url=render_url,
        )
    finally:
        await db.close()
