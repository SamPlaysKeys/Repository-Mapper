"""Graph data model for storing file reference relationships."""

from pathlib import Path
from typing import Set, Dict, Iterator, Tuple


class ReferenceGraph:
    """
    A directed graph representing file references.
    
    Nodes are file paths, and edges represent 'source -> referenced' relationships.
    Missing references (unresolved paths) are tracked separately.
    """
    
    def __init__(self):
        self._nodes: Set[Path] = set()
        self._edges: Dict[Path, Set[Path]] = {}
        self._missing: Dict[Path, Set[str]] = {}  # source -> set of missing path strings
        self._remote: Dict[Path, Set[str]] = {}  # source -> set of remote URLs
        self._templates: Dict[Path, Set[str]] = {}  # source -> set of template path strings
    
    @property
    def nodes(self) -> Set[Path]:
        """Return all nodes in the graph."""
        return self._nodes.copy()
    
    @property
    def edges(self) -> Dict[Path, Set[Path]]:
        """Return adjacency list representation of edges."""
        return {k: v.copy() for k, v in self._edges.items()}
    
    @property
    def missing(self) -> Dict[Path, Set[str]]:
        """Return missing references (source -> set of unresolved path strings)."""
        return {k: v.copy() for k, v in self._missing.items()}
    
    @property
    def remote(self) -> Dict[Path, Set[str]]:
        """Return remote references (source -> set of URLs)."""
        return {k: v.copy() for k, v in self._remote.items()}
    
    @property
    def templates(self) -> Dict[Path, Set[str]]:
        """Return template references (source -> set of template path strings)."""
        return {k: v.copy() for k, v in self._templates.items()}
    
    def add_node(self, node: Path) -> None:
        """Add a node to the graph."""
        self._nodes.add(node)
    
    def add_edge(self, source: Path, target: Path) -> None:
        """
        Add a directed edge from source to target.
        
        Automatically adds both nodes to the graph.
        """
        self._nodes.add(source)
        self._nodes.add(target)
        
        if source not in self._edges:
            self._edges[source] = set()
        self._edges[source].add(target)
    
    def add_missing(self, source: Path, candidate: str) -> None:
        """
        Record a missing reference (unresolved path).
        
        Args:
            source: The file containing the reference.
            candidate: The unresolved path string.
        """
        self._nodes.add(source)
        if source not in self._missing:
            self._missing[source] = set()
        self._missing[source].add(candidate)
    
    def get_missing(self, source: Path) -> Set[str]:
        """Get all missing references from the source file."""
        return self._missing.get(source, set()).copy()
    
    def has_missing(self) -> bool:
        """Check if there are any missing references."""
        return bool(self._missing)
    
    def add_remote(self, source: Path, url: str) -> None:
        """
        Record a remote reference (URL).
        
        Args:
            source: The file containing the reference.
            url: The URL string.
        """
        self._nodes.add(source)
        if source not in self._remote:
            self._remote[source] = set()
        self._remote[source].add(url)
    
    def get_remote(self, source: Path) -> Set[str]:
        """Get all remote references from the source file."""
        return self._remote.get(source, set()).copy()
    
    def has_remote(self) -> bool:
        """Check if there are any remote references."""
        return bool(self._remote)
    
    def add_template(self, source: Path, candidate: str) -> None:
        """
        Record a template reference (path containing Jinja placeholders).
        
        Args:
            source: The file containing the reference.
            candidate: The template path string (contains {{ }}).
        """
        self._nodes.add(source)
        if source not in self._templates:
            self._templates[source] = set()
        self._templates[source].add(candidate)
    
    def get_templates(self, source: Path) -> Set[str]:
        """Get all template references from the source file."""
        return self._templates.get(source, set()).copy()
    
    def has_templates(self) -> bool:
        """Check if there are any template references."""
        return bool(self._templates)
    
    def get_targets(self, source: Path) -> Set[Path]:
        """Get all files that the source file references."""
        return self._edges.get(source, set()).copy()
    
    def get_roots(self) -> Set[Path]:
        """
        Get nodes that are never referenced by other nodes.
        
        These are 'root' files that reference others but are not
        themselves referenced.
        """
        all_targets: Set[Path] = set()
        for targets in self._edges.values():
            all_targets.update(targets)
        
        return self._nodes - all_targets
    
    def get_sources(self, target: Path) -> Set[Path]:
        """Get all files that reference the target file."""
        sources = set()
        for source, targets in self._edges.items():
            if target in targets:
                sources.add(source)
        return sources
    
    def iter_edges(self) -> Iterator[Tuple[Path, Path]]:
        """Iterate over all edges as (source, target) tuples."""
        for source, targets in self._edges.items():
            for target in sorted(targets):
                yield source, target
    
    def iter_missing(self) -> Iterator[Tuple[Path, str]]:
        """Iterate over all missing references as (source, candidate) tuples."""
        for source, candidates in self._missing.items():
            for candidate in sorted(candidates):
                yield source, candidate
    
    def iter_remote(self) -> Iterator[Tuple[Path, str]]:
        """Iterate over all remote references as (source, url) tuples."""
        for source, urls in self._remote.items():
            for url in sorted(urls):
                yield source, url
    
    def iter_templates(self) -> Iterator[Tuple[Path, str]]:
        """Iterate over all template references as (source, candidate) tuples."""
        for source, candidates in self._templates.items():
            for candidate in sorted(candidates):
                yield source, candidate
    
    def get_connected_nodes(self) -> Set[Path]:
        """
        Get nodes that are connected to other files.
        
        A node is considered connected if:
        - It has outgoing edges (references other files)
        - It is referenced by another file (is a target)
        - It has missing references
        - It has remote/URL references
        - It has template references
        
        Returns:
            Set of connected nodes.
        """
        connected: Set[Path] = set()
        
        # Nodes with outgoing edges
        for source in self._edges:
            if self._edges[source]:  # Has at least one target
                connected.add(source)
        
        # Nodes that are targets of edges
        for targets in self._edges.values():
            connected.update(targets)
        
        # Nodes with missing references
        for source in self._missing:
            if self._missing[source]:
                connected.add(source)
        
        # Nodes with remote references
        for source in self._remote:
            if self._remote[source]:
                connected.add(source)
        
        # Nodes with template references
        for source in self._templates:
            if self._templates[source]:
                connected.add(source)
        
        return connected
    
    def __len__(self) -> int:
        """Return the number of nodes in the graph."""
        return len(self._nodes)
    
    def __contains__(self, node: Path) -> bool:
        """Check if a node is in the graph."""
        return node in self._nodes
    
    def __repr__(self) -> str:
        missing_count = sum(len(m) for m in self._missing.values())
        remote_count = sum(len(r) for r in self._remote.values())
        template_count = sum(len(t) for t in self._templates.values())
        return f"ReferenceGraph(nodes={len(self._nodes)}, edges={sum(len(t) for t in self._edges.values())}, missing={missing_count}, remote={remote_count}, templates={template_count})"
