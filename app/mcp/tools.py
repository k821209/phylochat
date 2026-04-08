"""MCP tool definitions for PhyloChat."""

import sqlite3
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent

from app.config import settings
from app.services.r_executor import render_ggtree
from app.services.newick_parser import get_tree_info as _get_tree_info

DB_PATH = str(settings.DB_PATH)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def register_tools(server: Server):

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="render_ggtree",
                description=(
                    "Execute ggtree R code to render a phylogenetic tree. "
                    "The tree object is pre-loaded as `tree`. Assign the final plot to `p`. "
                    "R code is saved to the database and the image appears in the web UI."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "integer", "description": "Tree ID in the database"},
                        "r_code": {"type": "string", "description": "ggtree/ggplot2 R code (user code block only)"},
                        "output_format": {"type": "string", "enum": ["png", "svg", "pdf"], "default": "png"},
                        "width": {"type": "number", "default": 10, "description": "Figure width in inches"},
                        "height": {"type": "number", "default": 8, "description": "Figure height in inches"},
                        "dpi": {"type": "integer", "default": 300, "description": "Resolution"},
                    },
                    "required": ["tree_id", "r_code"],
                },
            ),
            Tool(
                name="list_trees",
                description="List all uploaded phylogenetic trees.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_tree",
                description="Get the newick string and metadata for a tree by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "integer", "description": "Tree ID"},
                    },
                    "required": ["tree_id"],
                },
            ),
            Tool(
                name="get_tree_info",
                description=(
                    "Get detailed structural information about a tree "
                    "(tip count, internal nodes, rooted status, all tip labels)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "integer", "description": "Tree ID"},
                    },
                    "required": ["tree_id"],
                },
            ),
            Tool(
                name="list_renders",
                description="List all renders for a given tree, newest first. Includes R code.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "integer", "description": "Tree ID"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["tree_id"],
                },
            ),
            Tool(
                name="get_render_code",
                description="Get the exact R code that produced a specific render.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "render_id": {"type": "integer", "description": "Render history ID"},
                    },
                    "required": ["render_id"],
                },
            ),
            Tool(
                name="export_figure",
                description="Re-render a tree at publication quality in the requested format.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "integer", "description": "Tree ID"},
                        "format": {"type": "string", "enum": ["png", "svg", "pdf"], "default": "png"},
                        "dpi": {"type": "integer", "default": 300},
                        "width": {"type": "number", "description": "Figure width in inches"},
                        "height": {"type": "number", "description": "Figure height in inches"},
                        "render_id": {"type": "integer", "description": "Use R code from this render; if omitted, uses latest"},
                    },
                    "required": ["tree_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "render_ggtree":
                return _handle_render_ggtree(arguments)
            elif name == "list_trees":
                return _handle_list_trees()
            elif name == "get_tree":
                return _handle_get_tree(arguments)
            elif name == "get_tree_info":
                return _handle_get_tree_info(arguments)
            elif name == "list_renders":
                return _handle_list_renders(arguments)
            elif name == "get_render_code":
                return _handle_get_render_code(arguments)
            elif name == "export_figure":
                return _handle_export_figure(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]


def _handle_render_ggtree(args: dict) -> list[TextContent]:
    tree_id = args["tree_id"]
    r_code = args["r_code"]
    fmt = args.get("output_format", "png")
    width = args.get("width", 10)
    height = args.get("height", 8)
    dpi = args.get("dpi", 300)

    conn = _get_conn()
    row = conn.execute("SELECT newick FROM tree_files WHERE id = ?", (tree_id,)).fetchone()
    if not row:
        conn.close()
        return [TextContent(type="text", text=f"Error: Tree {tree_id} not found")]

    newick = row["newick"]
    try:
        output_path = render_ggtree(newick, r_code, fmt, width, height, dpi)
    except RuntimeError as e:
        conn.close()
        return [TextContent(type="text", text=f"R execution error: {e}")]

    cursor = conn.execute(
        "INSERT INTO render_history (tree_id, r_code, render_path) VALUES (?, ?, ?)",
        (tree_id, r_code, output_path.name),
    )
    render_id = cursor.lastrowid
    conn.commit()
    conn.close()

    import json
    return [TextContent(type="text", text=json.dumps({
        "render_id": render_id,
        "render_url": f"/renders/{output_path.name}",
        "filename": output_path.name,
        "success": True,
    }))]


def _handle_list_trees() -> list[TextContent]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, filename, uploaded_at FROM tree_files ORDER BY id"
    ).fetchall()
    conn.close()

    import json
    trees = []
    for r in rows:
        trees.append({
            "tree_id": r["id"],
            "filename": r["filename"],
            "uploaded_at": r["uploaded_at"],
        })
    return [TextContent(type="text", text=json.dumps(trees))]


def _handle_get_tree(args: dict) -> list[TextContent]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, filename, newick, uploaded_at FROM tree_files WHERE id = ?",
        (args["tree_id"],),
    ).fetchone()
    conn.close()

    if not row:
        return [TextContent(type="text", text=f"Error: Tree {args['tree_id']} not found")]

    import json
    info = _get_tree_info(row["newick"])
    return [TextContent(type="text", text=json.dumps({
        "tree_id": row["id"],
        "filename": row["filename"],
        "newick": row["newick"],
        "tip_count": info["tip_count"],
        "tip_labels": info["tip_labels"],
        "uploaded_at": row["uploaded_at"],
    }))]


def _handle_get_tree_info(args: dict) -> list[TextContent]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT newick FROM tree_files WHERE id = ?", (args["tree_id"],)
    ).fetchone()
    conn.close()

    if not row:
        return [TextContent(type="text", text=f"Error: Tree {args['tree_id']} not found")]

    import json
    info = _get_tree_info(row["newick"])
    return [TextContent(type="text", text=json.dumps(info))]


def _handle_list_renders(args: dict) -> list[TextContent]:
    tree_id = args["tree_id"]
    limit = args.get("limit", 10)

    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, r_code, render_path, created_at FROM render_history "
        "WHERE tree_id = ? ORDER BY id DESC LIMIT ?",
        (tree_id, limit),
    ).fetchall()
    conn.close()

    import json
    renders = []
    for r in rows:
        renders.append({
            "render_id": r["id"],
            "r_code": r["r_code"],
            "render_url": f"/renders/{r['render_path']}",
            "created_at": r["created_at"],
        })
    return [TextContent(type="text", text=json.dumps(renders))]


def _handle_get_render_code(args: dict) -> list[TextContent]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, tree_id, r_code, render_path FROM render_history WHERE id = ?",
        (args["render_id"],),
    ).fetchone()
    conn.close()

    if not row:
        return [TextContent(type="text", text=f"Error: Render {args['render_id']} not found")]

    import json
    return [TextContent(type="text", text=json.dumps({
        "render_id": row["id"],
        "tree_id": row["tree_id"],
        "r_code": row["r_code"],
        "render_url": f"/renders/{row['render_path']}",
    }))]


def _handle_export_figure(args: dict) -> list[TextContent]:
    tree_id = args["tree_id"]
    fmt = args.get("format", "png")
    dpi = args.get("dpi", 300)
    width = args.get("width", 10)
    height = args.get("height", 8)
    render_id = args.get("render_id")

    conn = _get_conn()

    # Get newick
    tree_row = conn.execute(
        "SELECT newick FROM tree_files WHERE id = ?", (tree_id,)
    ).fetchone()
    if not tree_row:
        conn.close()
        return [TextContent(type="text", text=f"Error: Tree {tree_id} not found")]

    # Get R code
    if render_id:
        code_row = conn.execute(
            "SELECT r_code FROM render_history WHERE id = ?", (render_id,)
        ).fetchone()
    else:
        code_row = conn.execute(
            "SELECT r_code FROM render_history WHERE tree_id = ? ORDER BY id DESC LIMIT 1",
            (tree_id,),
        ).fetchone()

    r_code = code_row["r_code"] if code_row else "p <- ggtree(tree) + geom_tiplab()"
    conn.close()

    try:
        output_path = render_ggtree(tree_row["newick"], r_code, fmt, width, height, dpi)
    except RuntimeError as e:
        return [TextContent(type="text", text=f"R execution error: {e}")]

    import json
    return [TextContent(type="text", text=json.dumps({
        "export_url": f"/renders/{output_path.name}",
        "filename": output_path.name,
        "format": fmt,
    }))]
