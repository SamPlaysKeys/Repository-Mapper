"""Tests for scanner module."""

import pytest
from pathlib import Path
import tempfile
import os

from scanner.parser import (
    extract_candidate_paths,
    _is_likely_path,
    _clean_path,
)
from scanner.resolver import resolve_candidate_path, _is_within_repo


class TestPathExtraction:
    """Tests for path extraction from parsed data."""
    
    def test_extract_from_dict(self):
        """Test extracting paths from dictionary."""
        data = {
            "config_path": "config/app.yaml",
            "data_file": "data/users.json",
            "name": "my-app",  # Should not be extracted
        }
        
        paths = extract_candidate_paths(data)
        
        assert "config/app.yaml" in paths
        assert "data/users.json" in paths
        assert "my-app" not in paths
    
    def test_extract_from_nested_dict(self):
        """Test extracting paths from nested structure."""
        data = {
            "database": {
                "schema_file": "schemas/db.json",
                "migrations": {
                    "path": "migrations/001.yaml"
                }
            }
        }
        
        paths = extract_candidate_paths(data)
        
        assert "schemas/db.json" in paths
        assert "migrations/001.yaml" in paths
    
    def test_extract_from_list(self):
        """Test extracting paths from lists."""
        data = {
            "imports": [
                "lib/utils.yaml",
                "lib/helpers.yaml",
            ]
        }
        
        paths = extract_candidate_paths(data)
        
        assert "lib/utils.yaml" in paths
        assert "lib/helpers.yaml" in paths
    
    def test_skip_urls(self):
        """Test that URLs are not extracted as paths."""
        data = {
            "api_url": "https://api.example.com/v1",
            "file_path": "config/api.yaml",
        }
        
        paths = extract_candidate_paths(data)
        
        assert "https://api.example.com/v1" not in paths
        assert "config/api.yaml" in paths


class TestPathHeuristics:
    """Tests for path detection heuristics."""
    
    def test_is_likely_path_with_extension(self):
        """Test paths with extensions."""
        assert _is_likely_path("config/app.yaml")
        assert _is_likely_path("data/users.json")
        assert _is_likely_path("schema.toml")
    
    def test_is_likely_path_skip_urls(self):
        """Test that URLs are rejected."""
        assert not _is_likely_path("https://example.com")
        assert not _is_likely_path("http://localhost:8080")
    
    def test_is_likely_path_skip_special(self):
        """Test that special strings are rejected."""
        assert not _is_likely_path("$HOME/config")
        assert not _is_likely_path("{template}")
        assert not _is_likely_path("#anchor")
    
    def test_clean_path(self):
        """Test path cleaning."""
        assert _clean_path("./config/app.yaml") == "config/app.yaml"
        assert _clean_path("  config/app.yaml  ") == "config/app.yaml"
        assert _clean_path("'config/app.yaml'") == "config/app.yaml"
        assert _clean_path("config\\app.yaml") == "config/app.yaml"
    
    def test_clean_path_skip_json_refs(self):
        """Test that JSON references are skipped."""
        assert _clean_path("#/definitions/User") is None


class TestPathResolution:
    """Tests for path resolution."""
    
    def test_resolve_relative_to_source(self):
        """Test resolving path relative to source file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create directory structure
            config_dir = root / "config"
            config_dir.mkdir()
            data_dir = root / "data"
            data_dir.mkdir()
            
            source = config_dir / "app.yaml"
            target = data_dir / "users.json"
            source.touch()
            target.touch()
            
            # Test resolution from config/ to ../data/users.json
            resolved = resolve_candidate_path(source, "../data/users.json", root)
            
            assert resolved is not None
            assert resolved.name == "users.json"
    
    def test_resolve_relative_to_root(self):
        """Test resolving path relative to repository root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Create files
            source = root / "config" / "app.yaml"
            target = root / "data" / "users.json"
            source.parent.mkdir(parents=True)
            target.parent.mkdir(parents=True)
            source.touch()
            target.touch()
            
            # Test resolution using root-relative path
            resolved = resolve_candidate_path(source, "data/users.json", root)
            
            assert resolved is not None
            assert resolved.name == "users.json"
    
    def test_is_within_repo(self):
        """Test checking if path is within repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            inside = root / "config" / "app.yaml"
            outside = Path("/etc/passwd")
            
            assert _is_within_repo(inside, root)
            assert not _is_within_repo(outside, root)
