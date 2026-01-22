"""Graph builder that orchestrates scanning and graph construction."""

from pathlib import Path
from typing import Optional, Set

from graph.model import ReferenceGraph
from .discovery import iter_files, DEFAULT_EXTENSIONS, DEFAULT_EXCLUDE_DIRS
from .parser import parse_file, extract_candidate_paths, extract_urls
from .resolver import resolve_candidate_path, get_relative_path


def is_template_path(candidate: str) -> bool:
    """
    Check if a candidate path is a Jinja template (contains {{ }} placeholders).
    
    Args:
        candidate: The candidate path string to check.
    
    Returns:
        True if the path contains Jinja template placeholders.
    """
    return "{{ " in candidate and " }}" in candidate


def build_graph(
    root: Path,
    include_ext: Optional[Set[str]] = None,
    exclude_dirs: Optional[Set[str]] = None,
    max_depth: Optional[int] = None,
) -> ReferenceGraph:
    """
    Scan a repository and build a reference graph.
    
    Args:
        root: Repository root directory.
        include_ext: File extensions to scan (default: yaml, yml, json, toml).
        exclude_dirs: Directory names to exclude (default: .git, node_modules, etc.).
        max_depth: Maximum directory depth to scan.
    
    Returns:
        ReferenceGraph containing all discovered file references.
    """
    graph = ReferenceGraph()
    root = root.resolve()
    
    # Iterate over all matching files
    for file_path in iter_files(
        root=root,
        include_ext=include_ext,
        exclude_dirs=exclude_dirs,
        max_depth=max_depth,
    ):
        # Add the file as a node
        graph.add_node(file_path)
        
        # Parse the file
        data = parse_file(file_path)
        if data is None:
            continue
        
        # Extract candidate paths
        candidates = extract_candidate_paths(data)
        
        # Resolve each candidate and add edges
        for candidate in candidates:
            resolved = resolve_candidate_path(file_path, candidate, root)
            if resolved is not None and resolved != file_path:
                graph.add_edge(file_path, resolved)
            elif resolved is None:
                # Check if this is a template path (contains Jinja placeholders)
                if is_template_path(candidate):
                    graph.add_template(file_path, candidate)
                else:
                    # Track unresolved references as missing
                    graph.add_missing(file_path, candidate)
        
        # Extract and track remote references (URLs)
        # Note: A URL can also be a template if it contains Jinja placeholders
        urls = extract_urls(data)
        for url in urls:
            graph.add_remote(file_path, url)
            # Also track as template if it contains Jinja placeholders
            if is_template_path(url):
                graph.add_template(file_path, url)
    
    return graph
