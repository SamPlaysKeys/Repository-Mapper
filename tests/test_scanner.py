"""Tests for scanner module."""

import pytest
from pathlib import Path
import tempfile
import os

from scanner.parser import (
    extract_candidate_paths,
    _is_likely_path,
    _clean_path,
    _is_command_with_path_target,
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


class TestCommandFiltering:
    """Tests for filtering out commands with path targets."""
    
    def test_chmod_command(self):
        """Test that chmod commands are filtered out."""
        assert _is_command_with_path_target("chmod 600 /test/issues/permissions.yaml")
        assert _is_command_with_path_target("chmod +x script.sh")
        assert not _is_likely_path("chmod 600 /test/issues/permissions.yaml")
    
    def test_sudo_prefix(self):
        """Test commands with sudo prefix."""
        assert _is_command_with_path_target("sudo rm -rf /some/path")
        assert _is_command_with_path_target("sudo chmod 755 /var/log/app.log")
        assert not _is_likely_path("sudo cat /etc/config.yaml")
    
    def test_file_operation_commands(self):
        """Test various file operation commands."""
        assert _is_command_with_path_target("cp source.yaml dest.yaml")
        assert _is_command_with_path_target("mv old.json new.json")
        assert _is_command_with_path_target("rm /tmp/cache.yaml")
        assert _is_command_with_path_target("cat /etc/app.conf")
        assert _is_command_with_path_target("mkdir /var/data")
    
    def test_interpreter_commands(self):
        """Test interpreter commands."""
        assert _is_command_with_path_target("python script.py")
        assert _is_command_with_path_target("bash /scripts/deploy.sh")
        assert _is_command_with_path_target("node app.js")
    
    def test_not_a_command(self):
        """Test that regular paths are not flagged as commands."""
        assert not _is_command_with_path_target("config/app.yaml")
        assert not _is_command_with_path_target("/var/data/app.json")
        assert not _is_command_with_path_target("../relative/path.toml")
    
    def test_command_with_full_path(self):
        """Test commands specified with full path."""
        assert _is_command_with_path_target("/usr/bin/chmod 600 /file.yaml")
        assert _is_command_with_path_target("/bin/cat /etc/config.yaml")
    
    def test_single_word_not_command(self):
        """Test that single commands without args are not filtered."""
        # A command alone without a path target should not be filtered
        assert not _is_command_with_path_target("chmod")
        assert not _is_command_with_path_target("cat")
    
    def test_extract_skips_commands(self):
        """Test that extract_candidate_paths skips command strings."""
        data = {
            "config_path": "config/app.yaml",
            "setup_cmd": "chmod 600 /test/issues/permissions.yaml",
            "cleanup": "rm -rf /tmp/cache.json",
        }
        
        paths = extract_candidate_paths(data)
        
        assert "config/app.yaml" in paths
        # Command strings should not be extracted as paths
        assert "chmod 600 /test/issues/permissions.yaml" not in paths
        assert "/test/issues/permissions.yaml" not in paths
        assert "rm -rf /tmp/cache.json" not in paths


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
