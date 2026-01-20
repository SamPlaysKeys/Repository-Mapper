"""Path resolution utilities for mapping candidate paths to actual files."""

from pathlib import Path
from typing import Optional


def resolve_candidate_path(
    source_file: Path,
    candidate: str,
    root: Path,
) -> Optional[Path]:
    """
    Resolve a candidate path string to an actual file path.
    
    Tries multiple resolution strategies:
    1. Relative to the source file's directory.
    2. Relative to the repository root.
    3. As an absolute path (if within the repo).
    
    Args:
        source_file: The file containing the reference.
        candidate: The candidate path string.
        root: The repository root directory.
    
    Returns:
        Resolved Path if the file exists, None otherwise.
    """
    if not candidate:
        return None
    
    root = root.resolve()
    source_dir = source_file.parent.resolve()
    
    # Normalize the candidate path
    normalized = candidate.replace("\\", "/")
    
    # Strip leading slashes - treat /path/to/file as root-relative, not absolute
    normalized = normalized.lstrip("/")
    
    candidate_path = Path(normalized)
    
    # Strategy 1: Relative to source file's directory
    try:
        resolved = (source_dir / candidate_path).resolve()
        if resolved.is_file() and _is_within_repo(resolved, root):
            return resolved
    except (OSError, ValueError):
        pass
    
    # Strategy 2: Relative to repository root
    try:
        resolved = (root / candidate_path).resolve()
        if resolved.is_file() and _is_within_repo(resolved, root):
            return resolved
    except (OSError, ValueError):
        pass
    
    # Strategy 3: Handle absolute paths that might be within repo
    if candidate_path.is_absolute():
        try:
            resolved = candidate_path.resolve()
            if resolved.is_file() and _is_within_repo(resolved, root):
                return resolved
        except (OSError, ValueError):
            pass
    
    # Strategy 4: Try common parent directory patterns
    # e.g., if candidate is "schemas/user.json" and we're in "config/app.yaml"
    # try looking in sibling directories
    for parent in source_dir.parents:
        if not _is_within_repo(parent, root):
            break
        try:
            resolved = (parent / candidate_path).resolve()
            if resolved.is_file() and _is_within_repo(resolved, root):
                return resolved
        except (OSError, ValueError):
            pass
    
    return None


def _is_within_repo(path: Path, root: Path) -> bool:
    """Check if a path is within the repository root."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def get_relative_path(file_path: Path, root: Path) -> Path:
    """
    Get the path relative to root.
    
    Args:
        file_path: The file path to make relative.
        root: The root directory.
    
    Returns:
        Relative path, or the original path if it can't be made relative.
    """
    try:
        return file_path.resolve().relative_to(root.resolve())
    except ValueError:
        return file_path
