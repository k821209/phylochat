"""MCP resource definitions for PhyloChat."""

import sqlite3
from pathlib import Path

from mcp.server import Server
from mcp.types import Resource, ResourceTemplate, TextResourceContents

from app.config import settings

DB_PATH = str(settings.DB_PATH)
STYLE_GUIDE_PATH = settings.BASE_DIR / "docs" / "tree_style_guide.md"


def register_resources(server: Server):

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        resources = [
            Resource(
                uri="phylochat://style-guide",
                name="PhyloChat Tree Style Guide",
                description="ggtree styling rules, default parameters, print-ready sizing, and code templates.",
                mimeType="text/markdown",
            ),
        ]
        # Add tree-specific resources for each uploaded tree
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT id, filename FROM tree_files ORDER BY id").fetchall()
        conn.close()
        for row in rows:
            tid, fname = row
            resources.append(Resource(
                uri=f"phylochat://tree/{tid}/newick",
                name=f"Newick: {fname}",
                description=f"Raw newick string for tree {tid} ({fname})",
                mimeType="text/plain",
            ))
            resources.append(Resource(
                uri=f"phylochat://tree/{tid}/latest-code",
                name=f"Latest R Code: {fname}",
                description=f"Most recent ggtree R code for tree {tid}",
                mimeType="text/x-r-source",
            ))
        return resources

    @server.list_resource_templates()
    async def list_resource_templates() -> list[ResourceTemplate]:
        return [
            ResourceTemplate(
                uriTemplate="phylochat://tree/{tree_id}/newick",
                name="Tree Newick Data",
                description="Raw newick string for a specific tree.",
                mimeType="text/plain",
            ),
            ResourceTemplate(
                uriTemplate="phylochat://tree/{tree_id}/latest-code",
                name="Latest R Code for Tree",
                description="Most recent ggtree R code used to render this tree.",
                mimeType="text/x-r-source",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> list[TextResourceContents]:
        uri_str = str(uri)

        # Style guide
        if uri_str == "phylochat://style-guide":
            if STYLE_GUIDE_PATH.exists():
                content = STYLE_GUIDE_PATH.read_text(encoding="utf-8")
            else:
                content = "Style guide not found."
            return [TextResourceContents(uri=uri_str, text=content, mimeType="text/markdown")]

        # Tree newick
        if "/newick" in uri_str:
            tree_id = _extract_tree_id(uri_str)
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute(
                "SELECT newick FROM tree_files WHERE id = ?", (tree_id,)
            ).fetchone()
            conn.close()
            text = row[0] if row else f"Tree {tree_id} not found"
            return [TextResourceContents(uri=uri_str, text=text, mimeType="text/plain")]

        # Latest R code
        if "/latest-code" in uri_str:
            tree_id = _extract_tree_id(uri_str)
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute(
                "SELECT r_code FROM render_history WHERE tree_id = ? ORDER BY id DESC LIMIT 1",
                (tree_id,),
            ).fetchone()
            conn.close()
            text = row[0] if row and row[0] else "# No R code available yet"
            return [TextResourceContents(uri=uri_str, text=text, mimeType="text/x-r-source")]

        return [TextResourceContents(uri=uri_str, text=f"Unknown resource: {uri_str}", mimeType="text/plain")]


def _extract_tree_id(uri: str) -> int:
    """Extract tree_id from URI like phylochat://tree/15/newick."""
    parts = uri.split("/")
    for i, part in enumerate(parts):
        if part == "tree" and i + 1 < len(parts):
            return int(parts[i + 1])
    raise ValueError(f"Cannot extract tree_id from {uri}")
