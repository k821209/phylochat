"""Claude Code harness integration for natural language → ggtree code."""

import asyncio
import json
import subprocess


SYSTEM_PROMPT = """You are PhyloChat, an AI assistant that generates ggtree (R) code for phylogenetic tree visualization.

The user has uploaded a phylogenetic tree and wants to style/annotate it using natural language.

RULES:
1. Generate valid R code using ggtree, ggtreeExtra, ggplot2, and treeio packages.
2. The tree object is already loaded as `tree` (treeio::read.newick). Do NOT reload it.
3. Assign the final plot to variable `p`.
4. Use standard ggtree functions: ggtree(), geom_tiplab(), geom_nodepoint(), geom_hilight(), geom_cladelab(), etc.
5. Always respond with BOTH an explanation and the R code.

OUTPUT FORMAT:
Return a JSON object with two fields:
```json
{
  "explanation": "What the code does in plain language",
  "r_code": "the R code to execute"
}
```

AVAILABLE TREE INFO:
{tree_info}

CURRENT R CODE (if any):
{current_code}
"""


async def generate_ggtree_code(
    message: str,
    tree_info: dict,
    current_code: str = "",
) -> dict:
    """Use Claude to generate ggtree R code from natural language."""
    prompt = SYSTEM_PROMPT.format(
        tree_info=json.dumps(tree_info, indent=2),
        current_code=current_code or "(default: ggtree(tree) + geom_tiplab())",
    )

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            [
                "claude",
                "-p", f"{prompt}\n\nUser request: {message}",
                "--output-format", "text",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            return {
                "explanation": f"Error calling Claude: {result.stderr}",
                "r_code": None,
            }

        return _parse_response(result.stdout)
    except subprocess.TimeoutExpired:
        return {"explanation": "Request timed out.", "r_code": None}
    except FileNotFoundError:
        return {
            "explanation": "Claude CLI not found. Please install Claude Code.",
            "r_code": None,
        }


def _parse_response(response: str) -> dict:
    """Extract explanation and R code from Claude's response."""
    # Try to parse as JSON first
    try:
        # Find JSON block in response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(response[start:end])
            if "r_code" in parsed:
                return parsed
    except json.JSONDecodeError:
        pass

    # Fallback: extract R code from markdown code blocks
    r_code = None
    if "```r" in response or "```R" in response:
        parts = response.split("```")
        for i, part in enumerate(parts):
            if part.startswith("r") or part.startswith("R"):
                r_code = part[1:].strip()  # Remove 'r' prefix
                break

    explanation = response.split("```")[0].strip() if "```" in response else response.strip()

    return {
        "explanation": explanation,
        "r_code": r_code,
    }
