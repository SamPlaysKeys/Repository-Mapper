"""JSON exporter for reference graphs (machine-friendly format)."""

import json
from pathlib import Path
from typing import Optional, Dict, List, Any

from graph.model import ReferenceGraph


def to_json(
    graph: ReferenceGraph,
    root: Path,
    base: Optional[Path] = None,
    indent: int = 2,
    include_missing: bool = True,
    include_remote: bool = True,
) -> str:
    """
    Convert a reference graph to JSON format.
    
    Args:
        graph: The reference graph to export.
        root: Repository root for relative paths.
        base: Optional base path for relative path display.
        indent: JSON indentation level.
        include_missing: If True, include missing (unresolved) references.
        include_remote: If True, include remote (URL) references.
    
    Returns:
        JSON string representation of the graph.
    """
    if base is None:
        base = root
    
    # Build nodes list
    nodes: List[str] = []
    for node in sorted(graph.nodes):
        nodes.append(_get_path_str(node, base, root))
    
    # Build edges list
    edges: List[Dict[str, Any]] = []
    for source, target in graph.iter_edges():
        source_str = _get_path_str(source, base, root)
        target_str = _get_path_str(target, base, root)
        edges.append({"source": source_str, "target": target_str})
    
    # Add missing edges if enabled
    if include_missing:
        for source, candidate in graph.iter_missing():
            source_str = _get_path_str(source, base, root)
            edges.append({"source": source_str, "target": candidate, "missing": True})
    
    # Add remote edges if enabled
    if include_remote:
        for source, url in graph.iter_remote():
            source_str = _get_path_str(source, base, root)
            edges.append({"source": source_str, "target": url, "remote": True})
    
    data: Dict[str, Any] = {
        "nodes": nodes,
        "edges": edges,
    }
    
    return json.dumps(data, indent=indent)


def _get_path_str(path: Path, base: Path, root: Path) -> str:
    """Get the string representation of a path."""
    try:
        rel_path = path.resolve().relative_to(base.resolve())
        return str(rel_path).replace("\\", "/")
    except ValueError:
        try:
            rel_path = path.resolve().relative_to(root.resolve())
            return str(rel_path).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")
