"""ASCII tree-style exporter for reference graphs."""

from pathlib import Path
from typing import Optional, Set, List, Tuple

from graph.model import ReferenceGraph


# Unicode tree characters
UNICODE_BRANCH = "├── "
UNICODE_LAST = "└── "
UNICODE_VERTICAL = "│   "
UNICODE_SPACE = "    "

# ASCII fallback characters
ASCII_BRANCH = "|-- "
ASCII_LAST = "\\-- "
ASCII_VERTICAL = "|   "
ASCII_SPACE = "    "


def to_ascii(
    graph: ReferenceGraph,
    root: Path,
    base: Optional[Path] = None,
    style: str = "tree",
    include_missing: bool = True,
    include_remote: bool = True,
    include_templates: bool = False,
    show_all: bool = False,
) -> str:
    """
    Convert a reference graph to ASCII tree representation.
    
    Args:
        graph: The reference graph to export.
        root: Repository root for relative paths.
        base: Optional base path for relative path display.
        style: Output style - "tree" (Unicode) or "ascii" (pure ASCII).
        include_missing: If True, show missing (unresolved) references.
        include_remote: If True, show remote (URL) references.
        include_templates: If True, show template (Jinja placeholder) references.
        show_all: If True, include nodes with no connections. Default False.
    
    Returns:
        ASCII tree string.
    """
    if base is None:
        base = root
    
    # Select character set based on style
    if style == "ascii":
        chars = (ASCII_BRANCH, ASCII_LAST, ASCII_VERTICAL, ASCII_SPACE)
    else:
        chars = (UNICODE_BRANCH, UNICODE_LAST, UNICODE_VERTICAL, UNICODE_SPACE)
    
    branch, last, vertical, space = chars
    
    # Get the set of nodes to consider
    if show_all:
        nodes_to_show = graph.nodes
    else:
        nodes_to_show = graph.get_connected_nodes()
    
    # Get root nodes (nodes that are never targets) from the filtered set
    all_targets: Set[Path] = set()
    for node in nodes_to_show:
        all_targets.update(graph.get_targets(node))
    root_nodes = sorted(nodes_to_show - all_targets)
    
    # If no root nodes, fall back to all nodes with outgoing edges
    if not root_nodes:
        root_nodes = sorted(node for node in nodes_to_show if graph.get_targets(node))
    
    # If still no nodes, show all nodes from filtered set
    if not root_nodes:
        root_nodes = sorted(nodes_to_show)
    
    lines: List[str] = []
    
    for i, root_node in enumerate(root_nodes):
        visited: Set[Path] = set()
        _render_node(
            graph=graph,
            node=root_node,
            base=base,
            root=root,
            prefix="",
            is_last=True,
            chars=(branch, last, vertical, space),
            visited=visited,
            lines=lines,
            is_root=True,
            include_missing=include_missing,
            include_remote=include_remote,
            include_templates=include_templates,
        )
        
        # Add blank line between root trees (except after last)
        if i < len(root_nodes) - 1:
            lines.append("")
    
    return "\n".join(lines)


def _render_node(
    graph: ReferenceGraph,
    node: Path,
    base: Path,
    root: Path,
    prefix: str,
    is_last: bool,
    chars: Tuple[str, str, str, str],
    visited: Set[Path],
    lines: List[str],
    is_root: bool = False,
    include_missing: bool = True,
    include_remote: bool = True,
    include_templates: bool = False,
) -> None:
    """
    Recursively render a node and its children.
    
    Args:
        graph: The reference graph.
        node: Current node to render.
        base: Base path for display.
        root: Repository root.
        prefix: Current line prefix for indentation.
        is_last: Whether this is the last child of its parent.
        chars: Character set (branch, last, vertical, space).
        visited: Set of already visited nodes (to detect cycles).
        lines: Output lines list (modified in place).
        is_root: Whether this is a root-level node.
        include_missing: If True, show missing (unresolved) references.
        include_remote: If True, show remote (URL) references.
        include_templates: If True, show template (Jinja placeholder) references.
    """
    branch, last, vertical, space = chars
    
    # Get display path
    display_path = _get_display_path(node, base, root)
    
    # Check for cycles
    is_cycle = node in visited
    cycle_marker = " [*]" if is_cycle else ""
    
    # Build the line
    if is_root:
        lines.append(f"{display_path}{cycle_marker}")
    else:
        connector = last if is_last else branch
        lines.append(f"{prefix}{connector}{display_path}{cycle_marker}")
    
    # Don't recurse if we've already visited this node
    if is_cycle:
        return
    
    visited.add(node)
    
    # Get children (resolved targets)
    children = sorted(graph.get_targets(node))
    
    # Get missing references if enabled
    missing_refs: List[str] = []
    if include_missing:
        missing_refs = sorted(graph.get_missing(node))
    
    # Get remote references if enabled
    remote_refs: List[str] = []
    if include_remote:
        remote_refs = sorted(graph.get_remote(node))
    
    # Get template references if enabled
    template_refs: List[str] = []
    if include_templates:
        template_refs = sorted(graph.get_templates(node))
    
    total_items = len(children) + len(missing_refs) + len(remote_refs) + len(template_refs)
    item_index = 0
    
    # Render resolved children
    for child in children:
        item_index += 1
        child_is_last = (item_index == total_items)
        
        # Calculate new prefix for children
        if is_root:
            new_prefix = ""
        else:
            new_prefix = prefix + (space if is_last else vertical)
        
        _render_node(
            graph=graph,
            node=child,
            base=base,
            root=root,
            prefix=new_prefix,
            is_last=child_is_last,
            chars=chars,
            visited=visited,
            lines=lines,
            is_root=False,
            include_missing=include_missing,
            include_remote=include_remote,
            include_templates=include_templates,
        )
    
    # Render missing references
    for missing in missing_refs:
        item_index += 1
        missing_is_last = (item_index == total_items)
        
        # Calculate new prefix for missing items
        if is_root:
            new_prefix = ""
        else:
            new_prefix = prefix + (space if is_last else vertical)
        
        connector = last if missing_is_last else branch
        lines.append(f"{new_prefix}{connector}{missing} [MISSING]")
    
    # Render remote references
    for url in remote_refs:
        item_index += 1
        remote_is_last = (item_index == total_items)
        
        # Calculate new prefix for remote items
        if is_root:
            new_prefix = ""
        else:
            new_prefix = prefix + (space if is_last else vertical)
        
        connector = last if remote_is_last else branch
        lines.append(f"{new_prefix}{connector}{url} [REMOTE]")
    
    # Render template references
    for template in template_refs:
        item_index += 1
        template_is_last = (item_index == total_items)
        
        # Calculate new prefix for template items
        if is_root:
            new_prefix = ""
        else:
            new_prefix = prefix + (space if is_last else vertical)
        
        connector = last if template_is_last else branch
        lines.append(f"{new_prefix}{connector}{template} [TEMPLATE]")
    
    # Remove from visited when backtracking (to allow the same node
    # to appear in different branches, but still detect immediate cycles)
    visited.discard(node)


def _get_display_path(node: Path, base: Path, root: Path) -> str:
    """Get the display path for a node."""
    try:
        # Try relative to base first
        rel_path = node.resolve().relative_to(base.resolve())
        return str(rel_path).replace("\\", "/")
    except ValueError:
        try:
            # Fall back to relative to root
            rel_path = node.resolve().relative_to(root.resolve())
            return str(rel_path).replace("\\", "/")
        except ValueError:
            return str(node).replace("\\", "/")
