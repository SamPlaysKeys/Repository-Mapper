"""Scanner module for file discovery and reference extraction."""

from .discovery import iter_files
from .parser import parse_file, extract_candidate_paths
from .resolver import resolve_candidate_path
from .builder import build_graph

__all__ = [
    "iter_files",
    "parse_file",
    "extract_candidate_paths",
    "resolve_candidate_path",
    "build_graph",
]
