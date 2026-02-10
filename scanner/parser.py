"""Parsers for extracting data from configuration files."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Optional, Union

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib  # type: ignore
        HAS_TOML = True
    except ImportError:
        HAS_TOML = False
else:
    HAS_TOML = True


# Keys that often contain file paths
PATH_KEY_HINTS = {
    "path", "file", "filepath", "filename",
    "import", "include", "source", "src",
    "config", "schema", "template",
    "input", "output", "dir", "directory",
    "extends", "inherits", "base",
    "ref", "reference", "$ref",
}

# Common shell commands that take file/path arguments
# These should be filtered out when they appear with path targets
PATH_COMMANDS = {
    # File permission/ownership commands
    "chmod", "chown", "chgrp",
    # File operations
    "mv", "cp", "rm", "rmdir", "mkdir", "touch", "ln",
    # File viewing
    "cat", "head", "tail", "less", "more", "stat",
    # File listing
    "ls", "dir", "find",
    # Archive commands
    "tar", "gzip", "gunzip", "zip", "unzip",
    # Other common commands
    "source", "exec", "bash", "sh", "zsh",
    "python", "python3", "node", "ruby", "perl",
    "sudo", "su",
}

# Keys that often contain URLs/online references
URL_KEY_HINTS = {
    "$schema", "schema", "$ref", "ref",
    "url", "uri", "href", "link",
    "homepage", "repository", "source",
}


def parse_file(file_path: Path) -> Optional[Any]:
    """
    Parse a configuration file and return its contents.
    
    Args:
        file_path: Path to the file to parse.
    
    Returns:
        Parsed data structure, or None if parsing fails.
    """
    suffix = file_path.suffix.lower()
    
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    
    try:
        if suffix in {".yaml", ".yml"}:
            if not HAS_YAML:
                return None
            return yaml.safe_load(content)
        
        elif suffix == ".json":
            return json.loads(content)
        
        elif suffix == ".toml":
            if not HAS_TOML:
                return None
            if hasattr(tomllib, "loads"):
                return tomllib.loads(content)
            else:
                return tomllib.load(file_path)  # type: ignore
        
        else:
            # Try to parse as JSON first, then YAML
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                if HAS_YAML:
                    return yaml.safe_load(content)
                return None
    
    except Exception:
        return None


def extract_candidate_paths(
    data: Any,
    current_key: Optional[str] = None,
    aggressive: bool = False,
) -> Set[str]:
    """
    Extract strings that might be file paths from parsed data.
    
    Args:
        data: Parsed data structure (dict, list, or scalar).
        current_key: The key under which this data was found (for heuristics).
        aggressive: If True, include all string values; if False, only those
                   under path-like keys or matching path patterns.
    
    Returns:
        Set of candidate path strings.
    """
    candidates: Set[str] = set()
    
    if isinstance(data, dict):
        for key, value in data.items():
            key_lower = str(key).lower()
            # Check if key hints at a path
            is_path_key = any(hint in key_lower for hint in PATH_KEY_HINTS)
            candidates.update(
                extract_candidate_paths(value, key_lower, aggressive or is_path_key)
            )
    
    elif isinstance(data, list):
        for item in data:
            candidates.update(extract_candidate_paths(item, current_key, aggressive))
    
    elif isinstance(data, str):
        if _is_likely_path(data, aggressive):
            cleaned = _clean_path(data)
            if cleaned:
                candidates.add(cleaned)
    
    return candidates


def _is_command_with_path_target(value: str) -> bool:
    """
    Check if a string looks like a shell command with a path as the target.
    
    Detects patterns like:
    - "chmod 600 /path/to/file"
    - "sudo rm -rf /some/path"
    - "cat /etc/config.yaml"
    
    Args:
        value: String value to check.
    
    Returns:
        True if the value appears to be a command with a path target.
    """
    # Split on whitespace to get tokens
    tokens = value.split()
    if not tokens:
        return False
    
    # Get the first token (potential command)
    first_token = tokens[0].lower()
    
    # Handle sudo/su prefix - check second token as the actual command
    if first_token in {"sudo", "su"} and len(tokens) > 1:
        first_token = tokens[1].lower()
    
    # Check if the first token (or second after sudo) is a known command
    if first_token in PATH_COMMANDS:
        # Must have additional arguments (flags or path) to be considered a command
        return len(tokens) > 1
    
    # Also check for commands with full paths like /usr/bin/chmod
    if "/" in first_token:
        # Extract just the command name from the path
        cmd_name = first_token.rstrip("/").split("/")[-1]
        if cmd_name in PATH_COMMANDS and len(tokens) > 1:
            return True
    
    return False


def _is_likely_path(value: str, aggressive: bool = False) -> bool:
    """
    Determine if a string value looks like a file path.
    
    Args:
        value: String value to check.
        aggressive: If True, be more permissive in what's considered a path.
    
    Returns:
        True if the value looks like a file path.
    """
    if not value or len(value) > 500:
        return False
    
    # Skip URLs
    if re.match(r"^https?://", value, re.IGNORECASE):
        return False
    
    # Skip values that are clearly not paths
    if value.startswith(("$", "{", "[", "(", "#", "@")):
        return False
    
    # Skip values with newlines or tabs
    if "\n" in value or "\t" in value:
        return False
    
    # Skip commands that have a path as the target
    # e.g., "chmod 600 /test/file.yaml" or "sudo rm -rf /some/path"
    if _is_command_with_path_target(value):
        return False
    
    if aggressive:
        # In aggressive mode, accept any string that could be a path
        return (
            "/" in value or 
            "\\" in value or 
            value.endswith((".yaml", ".yml", ".json", ".toml", ".xml", ".ini", ".cfg"))
        )
    
    # In non-aggressive mode, require path-like patterns
    # Must have a file extension or directory separator
    has_extension = bool(re.search(r"\.\w{1,10}$", value))
    has_separator = "/" in value or "\\" in value
    
    # Common config file patterns
    config_pattern = re.match(
        r"^[\w./\-_]+\.(ya?ml|json|toml|xml|ini|cfg|conf|config)$",
        value,
        re.IGNORECASE,
    )
    
    return has_extension and (has_separator or config_pattern is not None)


def _clean_path(value: str) -> Optional[str]:
    """
    Clean and normalize a candidate path string.
    
    Args:
        value: Raw path string.
    
    Returns:
        Cleaned path string, or None if invalid.
    """
    if not value:
        return None
    
    # Strip whitespace and quotes
    cleaned = value.strip().strip("'\"")
    
    # Handle JSON reference format ($ref: "#/...")
    if cleaned.startswith("#/"):
        return None
    
    # Remove leading ./ for consistency
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    
    # Normalize path separators
    cleaned = cleaned.replace("\\", "/")
    
    # Skip absolute paths that look like system paths
    if cleaned.startswith("/etc/") or cleaned.startswith("/usr/") or cleaned.startswith("/var/"):
        return None
    
    # Skip if empty after cleaning
    if not cleaned:
        return None
    
    return cleaned


def extract_urls(
    data: Any,
    current_key: Optional[str] = None,
) -> Set[str]:
    """
    Extract URLs (online references) from parsed data.
    
    Args:
        data: Parsed data structure (dict, list, or scalar).
        current_key: The key under which this data was found (for heuristics).
    
    Returns:
        Set of URL strings.
    """
    urls: Set[str] = set()
    
    if isinstance(data, dict):
        for key, value in data.items():
            key_lower = str(key).lower()
            urls.update(extract_urls(value, key_lower))
    
    elif isinstance(data, list):
        for item in data:
            urls.update(extract_urls(item, current_key))
    
    elif isinstance(data, str):
        if _is_url(data, current_key):
            urls.add(data)
    
    return urls


def _is_url(value: str, current_key: Optional[str] = None) -> bool:
    """
    Determine if a string value is a URL worth tracking.
    
    Args:
        value: String value to check.
        current_key: The key under which this value was found.
    
    Returns:
        True if the value is a trackable URL.
    """
    if not value or len(value) > 500:
        return False
    
    # Must be an HTTP(S) URL
    if not re.match(r"^https?://", value, re.IGNORECASE):
        return False
    
    # Check if the key hints at a reference
    if current_key:
        is_url_key = any(hint in current_key for hint in URL_KEY_HINTS)
        if is_url_key:
            return True
    
    # Accept URLs that look like schema or reference URLs
    schema_patterns = [
        r"json-schema\.org",
        r"schema\.",
        r"/schema",
        r"\.xsd$",
        r"\.dtd$",
    ]
    for pattern in schema_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    
    return False
