"""File discovery utilities for scanning repositories."""

from pathlib import Path
from typing import Iterator, Set, Optional, List


DEFAULT_EXTENSIONS = {".yaml", ".yml", ".json", ".toml"}
DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".tox", ".nox",
    "venv", ".venv", "env", ".env",
    ".idea", ".vscode",
    "build", "dist", ".eggs", "*.egg-info",
}


def iter_files(
    root: Path,
    include_ext: Optional[Set[str]] = None,
    exclude_dirs: Optional[Set[str]] = None,
    max_depth: Optional[int] = None,
) -> Iterator[Path]:
    """
    Iterate over files in a directory tree.
    
    Args:
        root: Root directory to scan.
        include_ext: Set of file extensions to include (e.g., {'.yaml', '.json'}).
                    If None, uses DEFAULT_EXTENSIONS.
        exclude_dirs: Set of directory names to skip.
                     If None, uses DEFAULT_EXCLUDE_DIRS.
        max_depth: Maximum depth to descend. None means unlimited.
    
    Yields:
        Path objects for matching files.
    """
    if include_ext is None:
        include_ext = DEFAULT_EXTENSIONS
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS
    
    root = root.resolve()
    
    def _walk(current: Path, depth: int) -> Iterator[Path]:
        if max_depth is not None and depth > max_depth:
            return
        
        try:
            entries = sorted(current.iterdir())
        except PermissionError:
            return
        
        for entry in entries:
            if entry.is_dir():
                # Check if directory should be excluded
                if entry.name in exclude_dirs:
                    continue
                # Check for glob patterns in exclude_dirs
                if any(entry.name.endswith(pat.lstrip("*")) for pat in exclude_dirs if pat.startswith("*")):
                    continue
                yield from _walk(entry, depth + 1)
            elif entry.is_file():
                if entry.suffix.lower() in include_ext:
                    yield entry
    
    yield from _walk(root, 0)


def get_relative_path(file_path: Path, root: Path) -> Path:
    """Get the path relative to root, handling edge cases."""
    try:
        return file_path.resolve().relative_to(root.resolve())
    except ValueError:
        return file_path
