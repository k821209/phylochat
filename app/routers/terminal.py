"""WebSocket-based PTY terminal for running Claude Code in the browser."""

import asyncio
import fcntl
import os
import pty
import select
import shutil
import struct
import termios

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings

router = APIRouter()

PHYLOCHAT_SYSTEM_PROMPT = """You are PhyloChat, an AI assistant for phylogenetic tree visualization.

You help researchers style and annotate phylogenetic trees using ggtree (R).
The project directory is {project_dir}.

WORKFLOW:
1. Use the `list_trees` MCP tool to see available trees.
2. Read the `phylochat://style-guide` MCP resource for ggtree styling rules.
3. Use `get_tree_info` to understand tree structure (tip count, labels, etc.).
4. Use `list_renders` to see previous render history and R code for iteration.
5. Generate ggtree R code and call the `render_ggtree` MCP tool to execute it.
   - The tree object is pre-loaded as `tree`. Assign the final plot to `p`.
   - The rendered image appears automatically in the web UI.
6. Iterate based on user feedback.

DO NOT run Rscript directly. ALWAYS use the `render_ggtree` MCP tool.

AVAILABLE MCP TOOLS:
- render_ggtree(tree_id, r_code, output_format, width, height, dpi) — render a tree
- list_trees() — list uploaded trees
- get_tree(tree_id) — get newick + metadata
- get_tree_info(tree_id) — tip count, labels, rooted status
- list_renders(tree_id, limit) — render history with R code
- get_render_code(render_id) — R code for a specific render
- export_figure(tree_id, format, dpi, width, height) — publication export

AVAILABLE MCP RESOURCES:
- phylochat://style-guide — ggtree styling rules
- phylochat://tree/{{tree_id}}/newick — raw newick data
- phylochat://tree/{{tree_id}}/latest-code — most recent R code

CAPABILITIES:
- Generate ggtree + ggplot2 + ggtreeExtra R code
- Style trees: layouts, tip labels, bootstrap values, clade highlighting, heatmaps
- Export publication-quality figures (SVG, PDF, PNG)

Start by greeting the user and asking them to upload a tree file or paste a Newick string in the left panel.
""".strip()


def _write_system_prompt():
    """Write system prompt to a temp file for the terminal to reference."""
    prompt = PHYLOCHAT_SYSTEM_PROMPT.format(project_dir=str(settings.BASE_DIR))
    prompt_path = str(settings.DATA_DIR / "system_prompt.txt")
    with open(prompt_path, "w") as f:
        f.write(prompt)
    return prompt_path


def _get_claude_env() -> dict:
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    conda_prefix = os.environ.get("CONDA_PREFIX", "")
    if conda_prefix:
        env["PATH"] = os.path.join(conda_prefix, "bin") + ":" + env.get("PATH", "")
    phylochat_bin = os.path.expanduser("~/miniconda3/envs/phylochat/bin")
    if phylochat_bin not in env.get("PATH", ""):
        env["PATH"] = phylochat_bin + ":" + env.get("PATH", "")
    return env


@router.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()

    # Write system prompt file for claude commands
    _write_system_prompt()

    # Create PTY with a login shell (not claude directly)
    master_fd, slave_fd = pty.openpty()

    pid = os.fork()
    if pid == 0:
        # Child process
        os.close(master_fd)
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        os.close(slave_fd)

        env = _get_claude_env()
        os.chdir(str(settings.BASE_DIR))

        # Start a shell so user can launch claude via buttons
        user_shell = os.environ.get("SHELL", "/bin/zsh")
        shell_name = "-" + os.path.basename(user_shell)
        os.execvpe(user_shell, [shell_name], env)

    # Parent process
    os.close(slave_fd)

    # Set master_fd to non-blocking
    flag = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)

    async def read_from_pty():
        """Read PTY output and send to WebSocket."""
        loop = asyncio.get_event_loop()
        try:
            while True:
                await asyncio.sleep(0.01)
                try:
                    r, _, _ = select.select([master_fd], [], [], 0)
                    if r:
                        data = os.read(master_fd, 4096)
                        if data:
                            await websocket.send_bytes(data)
                except OSError:
                    break
        except (WebSocketDisconnect, Exception):
            pass

    reader_task = asyncio.create_task(read_from_pty())

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                data = message["bytes"]
                os.write(master_fd, data)
            elif "text" in message:
                text = message["text"]
                # Handle resize
                if text.startswith("RESIZE:"):
                    parts = text.split(":")
                    if len(parts) == 3:
                        cols, rows = int(parts[1]), int(parts[2])
                        winsize = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                else:
                    os.write(master_fd, text.encode())
    except WebSocketDisconnect:
        pass
    finally:
        reader_task.cancel()
        os.close(master_fd)
        try:
            os.kill(pid, 9)
            os.waitpid(pid, 0)
        except OSError:
            pass
