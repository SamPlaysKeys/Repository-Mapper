"""Tests for exporters."""

import json
import pytest
from pathlib import Path

from graph.model import ReferenceGraph
from exporters.mermaid_exporter import to_mermaid
from exporters.ascii_exporter import to_ascii
from exporters.json_exporter import to_json


class TestMermaidExporter:
    """Tests for Mermaid exporter."""
    
    def test_empty_graph(self):
        """Test exporting empty graph."""
        graph = ReferenceGraph()
        root = Path("/repo")
        
        output = to_mermaid(graph, root)
        
        assert output.startswith("flowchart LR")
    
    def test_simple_graph(self):
        """Test exporting simple graph."""
        graph = ReferenceGraph()
        root = Path("/repo")
        source = root / "config" / "app.yaml"
        target = root / "data" / "users.json"
        
        graph.add_edge(source, target)
        
        output = to_mermaid(graph, root)
        
        assert output.startswith("flowchart LR")
        assert "config/app.yaml" in output or "config_app_yaml" in output
        assert "data/users.json" in output or "data_users_json" in output
        assert "-->" in output
    
    def test_orientation(self):
        """Test different orientations."""
        graph = ReferenceGraph()
        root = Path("/repo")
        graph.add_node(root / "test.yaml")
        
        for orientation in ["LR", "TD", "TB", "RL", "BT"]:
            output = to_mermaid(graph, root, orientation=orientation)
            assert output.startswith(f"flowchart {orientation}")
    
    def test_grouped_output(self):
        """Test grouped output by directory."""
        graph = ReferenceGraph()
        root = Path("/repo")
        
        graph.add_edge(root / "config" / "app.yaml", root / "data" / "users.json")
        graph.add_edge(root / "config" / "local.yaml", root / "data" / "users.json")
        
        output = to_mermaid(graph, root, group_by_directory=True)
        
        assert "subgraph" in output
        assert "config" in output
        assert "data" in output


class TestASCIIExporter:
    """Tests for ASCII exporter."""
    
    def test_empty_graph(self):
        """Test exporting empty graph."""
        graph = ReferenceGraph()
        root = Path("/repo")
        
        output = to_ascii(graph, root)
        
        assert output == ""
    
    def test_simple_tree(self):
        """Test simple tree structure."""
        graph = ReferenceGraph()
        root = Path("/repo")
        source = root / "config" / "app.yaml"
        target = root / "data" / "users.json"
        
        graph.add_edge(source, target)
        
        output = to_ascii(graph, root)
        
        assert "config/app.yaml" in output
        assert "data/users.json" in output
        assert "└──" in output or "\\--" in output
    
    def test_unicode_style(self):
        """Test Unicode tree style."""
        graph = ReferenceGraph()
        root = Path("/repo")
        source = root / "app.yaml"
        target1 = root / "a.json"
        target2 = root / "b.json"
        
        graph.add_edge(source, target1)
        graph.add_edge(source, target2)
        
        output = to_ascii(graph, root, style="tree")
        
        # Should have branch characters
        assert "├──" in output or "└──" in output
    
    def test_ascii_style(self):
        """Test pure ASCII tree style."""
        graph = ReferenceGraph()
        root = Path("/repo")
        source = root / "app.yaml"
        target = root / "data.json"
        
        graph.add_edge(source, target)
        
        output = to_ascii(graph, root, style="ascii")
        
        # Should NOT have Unicode characters
        assert "├" not in output
        assert "└" not in output
        assert "│" not in output
    
    def test_cycle_detection(self):
        """Test that cycles are marked with [*]."""
        graph = ReferenceGraph()
        root = Path("/repo")
        a = root / "a.yaml"
        b = root / "b.yaml"
        
        # Create a cycle: a -> b -> a
        graph.add_edge(a, b)
        graph.add_edge(b, a)
        
        output = to_ascii(graph, root)
        
        # Should have cycle marker
        assert "[*]" in output
    
    def test_shared_nodes(self):
        """Test that shared nodes show properly with cycle markers."""
        graph = ReferenceGraph()
        root = Path("/repo")
        
        root1 = root / "config" / "app.yaml"
        root2 = root / "config" / "local.yaml"
        shared = root / "data" / "users.json"
        
        graph.add_edge(root1, shared)
        graph.add_edge(root2, shared)
        
        output = to_ascii(graph, root)
        
        # Both roots should appear
        assert "config/app.yaml" in output
        assert "config/local.yaml" in output
        # Shared node should appear (possibly with [*] in second occurrence)
        assert "data/users.json" in output


class TestJSONExporter:
    """Tests for JSON exporter."""
    
    def test_empty_graph(self):
        """Test exporting empty graph."""
        graph = ReferenceGraph()
        root = Path("/repo")
        
        output = to_json(graph, root)
        data = json.loads(output)
        
        assert data["nodes"] == []
        assert data["edges"] == []
    
    def test_simple_graph(self):
        """Test exporting simple graph."""
        graph = ReferenceGraph()
        root = Path("/repo")
        source = root / "config" / "app.yaml"
        target = root / "data" / "users.json"
        
        graph.add_edge(source, target)
        
        output = to_json(graph, root)
        data = json.loads(output)
        
        assert "config/app.yaml" in data["nodes"]
        assert "data/users.json" in data["nodes"]
        assert ["config/app.yaml", "data/users.json"] in data["edges"]
    
    def test_valid_json(self):
        """Test that output is valid JSON."""
        graph = ReferenceGraph()
        root = Path("/repo")
        
        for i in range(5):
            graph.add_edge(root / f"source{i}.yaml", root / f"target{i}.json")
        
        output = to_json(graph, root)
        
        # Should not raise
        data = json.loads(output)
        assert "nodes" in data
        assert "edges" in data
