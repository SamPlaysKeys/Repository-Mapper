"""Mermaid flowchart exporter for reference graphs."""

import re
from pathlib import Path
from typing import Optional, Dict, Set

from graph.model import ReferenceGraph


def to_mermaid(
    graph: ReferenceGraph,
    root: Path,
    orientation: str = "LR",
    base: Optional[Path] = None,
    group_by_directory: bool = False,
    include_missing: bool = True,
    include_remote: bool = True,
) -> str:
    """
    Convert a reference graph to Mermaid flowchart syntax.
    
    Args:
        graph: The reference graph to export.
        root: Repository root for relative paths.
        orientation: Flowchart orientation (LR, TD, TB, RL, BT).
        base: Optional base path for relative path display.
        group_by_directory: If True, group nodes by top-level directory.
        include_missing: If True, show missing (unresolved) references.
        include_remote: If True, show remote (URL) references.
    
    Returns:
        Mermaid flowchart string.
    """
    if base is None:
        base = root
    
    lines = [f"flowchart {orientation}"]
    
    # Build node ID mapping
    node_ids: Dict[Path, str] = {}
    for node in sorted(graph.nodes):
        node_ids[node] = _sanitize_id(node, root)
    
    # Build missing node ID mapping
    missing_ids: Dict[str, str] = {}
    if include_missing:
        for source, candidate in graph.iter_missing():
            if candidate not in missing_ids:
                missing_ids[candidate] = _sanitize_id_simple(f"missing_{candidate}")
    
    # Build remote node ID mapping
    remote_ids: Dict[str, str] = {}
    if include_remote:
        for source, url in graph.iter_remote():
            if url not in remote_ids:
                remote_ids[url] = _sanitize_id_simple(f"remote_{url}")
    
    if group_by_directory:
        lines.extend(_generate_grouped_mermaid(graph, root, node_ids, missing_ids, remote_ids, include_missing, include_remote))
    else:
        lines.extend(_generate_flat_mermaid(graph, root, node_ids, missing_ids, remote_ids, include_missing, include_remote))
    
    return "\n".join(lines)


def _generate_flat_mermaid(
    graph: ReferenceGraph,
    root: Path,
    node_ids: Dict[Path, str],
    missing_ids: Dict[str, str],
    remote_ids: Dict[str, str],
    include_missing: bool,
    include_remote: bool,
) -> list:
    """Generate flat (non-grouped) Mermaid output."""
    lines = []
    
    # Add node definitions with labels
    for node in sorted(graph.nodes):
        node_id = node_ids[node]
        label = _get_label(node, root)
        lines.append(f'    {node_id}["{label}"]')
    
    # Add missing node definitions (with different style)
    if include_missing and missing_ids:
        lines.append("")
        lines.append("    %% Missing references")
        for candidate in sorted(missing_ids.keys()):
            missing_id = missing_ids[candidate]
            lines.append(f'    {missing_id}["{candidate} [MISSING]"]')
            lines.append(f"    style {missing_id} stroke:#ff0000,stroke-dasharray: 5 5")
    
    # Add remote node definitions (with different style)
    if include_remote and remote_ids:
        lines.append("")
        lines.append("    %% Remote references")
        for url in sorted(remote_ids.keys()):
            remote_id = remote_ids[url]
            lines.append(f'    {remote_id}["{url} [REMOTE]"]')
            lines.append(f"    style {remote_id} stroke:#0066cc,stroke-dasharray: 5 5")
    
    # Add edges
    lines.append("")
    for source, target in graph.iter_edges():
        source_id = node_ids[source]
        target_id = node_ids[target]
        lines.append(f"    {source_id} --> {target_id}")
    
    # Add missing edges (dashed)
    if include_missing:
        for source, candidate in graph.iter_missing():
            source_id = node_ids[source]
            missing_id = missing_ids[candidate]
            lines.append(f"    {source_id} -.-> {missing_id}")
    
    # Add remote edges (dashed)
    if include_remote:
        for source, url in graph.iter_remote():
            source_id = node_ids[source]
            remote_id = remote_ids[url]
            lines.append(f"    {source_id} -.-> {remote_id}")
    
    return lines


def _generate_grouped_mermaid(
    graph: ReferenceGraph,
    root: Path,
    node_ids: Dict[Path, str],
    missing_ids: Dict[str, str],
    remote_ids: Dict[str, str],
    include_missing: bool,
    include_remote: bool,
) -> list:
    """Generate Mermaid output with subgraphs grouped by top-level directory."""
    lines = []
    
    # Group nodes by top-level directory
    groups: Dict[str, Set[Path]] = {}
    for node in graph.nodes:
        try:
            rel_path = node.resolve().relative_to(root.resolve())
            top_dir = rel_path.parts[0] if len(rel_path.parts) > 1 else "root"
        except ValueError:
            top_dir = "external"
        
        if top_dir not in groups:
            groups[top_dir] = set()
        groups[top_dir].add(node)
    
    # Generate subgraphs
    for group_name in sorted(groups.keys()):
        group_nodes = groups[group_name]
        subgraph_id = _sanitize_id_simple(group_name)
        lines.append(f"    subgraph {subgraph_id}[{group_name}]")
        
        for node in sorted(group_nodes):
            node_id = node_ids[node]
            label = _get_label(node, root)
            lines.append(f'        {node_id}["{label}"]')
        
        lines.append("    end")
        lines.append("")
    
    # Add missing nodes in their own group
    if include_missing and missing_ids:
        lines.append("    subgraph missing[Missing References]")
        for candidate in sorted(missing_ids.keys()):
            missing_id = missing_ids[candidate]
            lines.append(f'        {missing_id}["{candidate} [MISSING]"]')
            lines.append(f"        style {missing_id} stroke:#ff0000,stroke-dasharray: 5 5")
        lines.append("    end")
        lines.append("")
    
    # Add remote nodes in their own group
    if include_remote and remote_ids:
        lines.append("    subgraph remote[Remote References]")
        for url in sorted(remote_ids.keys()):
            remote_id = remote_ids[url]
            lines.append(f'        {remote_id}["{url} [REMOTE]"]')
            lines.append(f"        style {remote_id} stroke:#0066cc,stroke-dasharray: 5 5")
        lines.append("    end")
        lines.append("")
    
    # Add edges
    for source, target in graph.iter_edges():
        source_id = node_ids[source]
        target_id = node_ids[target]
        lines.append(f"    {source_id} --> {target_id}")
    
    # Add missing edges (dashed)
    if include_missing:
        for source, candidate in graph.iter_missing():
            source_id = node_ids[source]
            missing_id = missing_ids[candidate]
            lines.append(f"    {source_id} -.-> {missing_id}")
    
    # Add remote edges (dashed)
    if include_remote:
        for source, url in graph.iter_remote():
            source_id = node_ids[source]
            remote_id = remote_ids[url]
            lines.append(f"    {source_id} -.-> {remote_id}")
    
    return lines


def _sanitize_id(path: Path, root: Path) -> str:
    """
    Convert a file path to a valid Mermaid node ID.
    
    Mermaid IDs can only contain letters, digits, and underscores.
    """
    try:
        rel_path = path.resolve().relative_to(root.resolve())
    except ValueError:
        rel_path = path
    
    return _sanitize_id_simple(str(rel_path))


def _sanitize_id_simple(value: str) -> str:
    """Sanitize a string to be a valid Mermaid ID."""
    # Replace path separators and dots with underscores
    sanitized = re.sub(r"[/\\.\-]", "_", value)
    # Remove any remaining invalid characters
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "", sanitized)
    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = "n_" + sanitized
    return sanitized or "unknown"


def _get_label(path: Path, root: Path) -> str:
    """Get the display label for a node."""
    try:
        rel_path = path.resolve().relative_to(root.resolve())
        return str(rel_path).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")
