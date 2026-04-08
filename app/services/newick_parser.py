"""Newick string → D3-compatible JSON tree structure."""

from io import StringIO

from Bio import Phylo


def parse_newick(newick_str: str) -> dict:
    """Parse a Newick string into a nested dict for D3.js hierarchy."""
    tree = Phylo.read(StringIO(newick_str), "newick")
    return _clade_to_dict(tree.root)


def _clade_to_dict(clade) -> dict:
    node = {
        "name": clade.name or "",
        "branch_length": clade.branch_length or 0.0,
    }
    if clade.confidence is not None:
        node["bootstrap"] = float(clade.confidence)
    if clade.clades:
        node["children"] = [_clade_to_dict(c) for c in clade.clades]
    return node


def get_tip_labels(newick_str: str) -> list[str]:
    """Return all tip (leaf) labels from a Newick string."""
    tree = Phylo.read(StringIO(newick_str), "newick")
    return [tip.name for tip in tree.get_terminals() if tip.name]


def get_tree_info(newick_str: str) -> dict:
    """Return summary info about a tree."""
    tree = Phylo.read(StringIO(newick_str), "newick")
    terminals = tree.get_terminals()
    nonterminals = tree.get_nonterminals()
    return {
        "tip_count": len(terminals),
        "internal_node_count": len(nonterminals),
        "total_nodes": len(terminals) + len(nonterminals),
        "is_rooted": tree.rooted,
        "tip_labels": [t.name for t in terminals if t.name],
    }


def validate_newick(newick_str: str) -> bool:
    """Check if a string is valid Newick format."""
    try:
        Phylo.read(StringIO(newick_str), "newick")
        return True
    except Exception:
        return False
