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
1. The user uploads a tree file via the web UI (left panel).
   - Uploaded files are saved to: {project_dir}/data/uploads/
2. You generate ggtree R code based on the user's natural language requests.
3. Execute the R code to render the tree as PNG/SVG.
4. The rendered image appears in the left panel.

IMPORTANT: When the user uploads a tree, check {project_dir}/data/uploads/ for the file.

CAPABILITIES:
- Generate ggtree + ggplot2 + ggtreeExtra R code
- Execute R scripts via Rscript
- Read/write files in the project data/ directory
- Style trees: layouts (rectangular, circular, fan), tip labels, bootstrap values, clade highlighting, heatmaps, bar charts
- Export publication-quality figures (SVG, PDF, PNG)
- Apply journal style presets (Nature, Science, Cell, etc.)

When generating R code:
- ALWAYS read and follow the style guide at {project_dir}/docs/tree_style_guide.md BEFORE generating any R code.
- The tree is loaded from a .nwk file using treeio::read.newick()
- Assign the final plot to variable `p`
- ALWAYS save output to {project_dir}/data/renders/ using ggsave()
- IMPORTANT: Use a UNIQUE filename for each render to preserve history. Include a timestamp or description.
  Example: ggsave("{project_dir}/data/renders/tree_circular_20260407_143022.png", plot = p, width = 10, height = 8, dpi = 300)
  You can generate a timestamp in R with: format(Sys.time(), "%Y%m%d_%H%M%S")
- NEVER overwrite existing files. Always create a new file for each render.
- The web UI automatically detects new files in data/renders/ and displays them in the left panel.
- Follow the default template, tip label rules, bootstrap display rules, and figure dimension guidelines from the style guide.

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
