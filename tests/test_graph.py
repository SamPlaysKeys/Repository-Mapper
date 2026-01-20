"""Tests for graph data model."""

import pytest
from pathlib import Path

from graph.model import ReferenceGraph


class TestReferenceGraph:
    """Tests for ReferenceGraph class."""
    
    def test_empty_graph(self):
        """Test empty graph initialization."""
        graph = ReferenceGraph()
        assert len(graph) == 0
        assert graph.nodes == set()
        assert graph.edges == {}
    
    def test_add_node(self):
        """Test adding nodes."""
        graph = ReferenceGraph()
        path = Path("config/app.yaml")
        
        graph.add_node(path)
        
        assert len(graph) == 1
        assert path in graph
        assert path in graph.nodes
    
    def test_add_edge(self):
        """Test adding edges."""
        graph = ReferenceGraph()
        source = Path("config/app.yaml")
        target = Path("data/users.json")
        
        graph.add_edge(source, target)
        
        assert len(graph) == 2
        assert source in graph
        assert target in graph
        assert target in graph.get_targets(source)
    
    def test_get_roots(self):
        """Test getting root nodes (nodes that are never targets)."""
        graph = ReferenceGraph()
        root1 = Path("config/app.yaml")
        root2 = Path("config/local.yaml")
        shared = Path("data/users.json")
        leaf = Path("schemas/user.json")
        
        graph.add_edge(root1, shared)
        graph.add_edge(root2, shared)
        graph.add_edge(shared, leaf)
        
        roots = graph.get_roots()
        
        assert root1 in roots
        assert root2 in roots
        assert shared not in roots
        assert leaf not in roots
    
    def test_get_sources(self):
        """Test getting sources that reference a target."""
        graph = ReferenceGraph()
        source1 = Path("config/app.yaml")
        source2 = Path("config/local.yaml")
        target = Path("data/users.json")
        
        graph.add_edge(source1, target)
        graph.add_edge(source2, target)
        
        sources = graph.get_sources(target)
        
        assert source1 in sources
        assert source2 in sources
    
    def test_iter_edges(self):
        """Test iterating over edges."""
        graph = ReferenceGraph()
        edges = [
            (Path("a.yaml"), Path("b.yaml")),
            (Path("a.yaml"), Path("c.yaml")),
            (Path("b.yaml"), Path("d.yaml")),
        ]
        
        for source, target in edges:
            graph.add_edge(source, target)
        
        result = list(graph.iter_edges())
        
        # All edges should be present
        for edge in edges:
            assert edge in result
    
    def test_repr(self):
        """Test string representation."""
        graph = ReferenceGraph()
        graph.add_edge(Path("a.yaml"), Path("b.yaml"))
        
        assert "nodes=2" in repr(graph)
        assert "edges=1" in repr(graph)
        assert "missing=0" in repr(graph)
    
    def test_missing_references(self):
        """Test tracking missing (unresolved) references."""
        graph = ReferenceGraph()
        source = Path("config/app.yaml")
        
        graph.add_missing(source, "nonexistent/file.yaml")
        graph.add_missing(source, "another/missing.json")
        
        assert source in graph
        assert graph.has_missing()
        assert "nonexistent/file.yaml" in graph.get_missing(source)
        assert "another/missing.json" in graph.get_missing(source)
        
        # Test iteration
        missing_list = list(graph.iter_missing())
        assert len(missing_list) == 2
        assert (source, "another/missing.json") in missing_list
        assert (source, "nonexistent/file.yaml") in missing_list
    
    def test_missing_property(self):
        """Test the missing property returns a copy."""
        graph = ReferenceGraph()
        source = Path("config/app.yaml")
        graph.add_missing(source, "missing.yaml")
        
        missing = graph.missing
        assert source in missing
        assert "missing.yaml" in missing[source]
        
        # Modifying the copy shouldn't affect the original
        missing[source].add("other.yaml")
        assert "other.yaml" not in graph.get_missing(source)
