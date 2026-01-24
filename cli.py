#!/usr/bin/env python3
"""
Repository Mapper CLI

A tool for scanning repositories for cross-file references and generating
dependency graphs in various formats.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Set

from graph.model import ReferenceGraph
from scanner.builder import build_graph
from scanner.discovery import DEFAULT_EXTENSIONS, DEFAULT_EXCLUDE_DIRS
from exporters import to_mermaid, to_ascii, to_json


def parse_args(args=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="repomap",
        description="Scan a repository for cross-file references and generate dependency graphs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  repomap .                          # Scan current directory, ASCII output
  repomap ./config -f mermaid        # Mermaid output for config directory
  repomap . -f ascii --ascii-style=ascii  # Pure ASCII (no Unicode)
  repomap . -f json -o graph.json    # JSON output to file
  repomap . --include-ext .yaml .yml # Only scan YAML files
  repomap . --ignore-missing         # Hide unresolved file references
  repomap . --show-all               # Include files with no connections
        """,
    )
    
    # Positional arguments
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Repository root directory (default: current directory)",
    )
    
    # Output options
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file (default: stdout)",
    )
    
    parser.add_argument(
        "-f", "--format",
        choices=["ascii", "mermaid", "json"],
        default="ascii",
        help="Output format (default: ascii)",
    )
    
    # Mermaid-specific options
    parser.add_argument(
        "--orientation",
        choices=["LR", "TD", "TB", "RL", "BT"],
        default="LR",
        help="Mermaid flowchart orientation (default: LR)",
    )
    
    parser.add_argument(
        "--group-by-dir",
        action="store_true",
        help="Group nodes by top-level directory in Mermaid output",
    )
    
    # ASCII-specific options
    parser.add_argument(
        "--ascii-style",
        choices=["tree", "ascii"],
        default="tree",
        help="ASCII output style: 'tree' (Unicode) or 'ascii' (pure ASCII)",
    )
    
    # Scanning options
    parser.add_argument(
        "--include-ext",
        nargs="+",
        default=None,
        help="File extensions to include (e.g., .yaml .json)",
    )
    
    parser.add_argument(
        "--exclude-dir",
        nargs="+",
        default=None,
        help="Directory names to exclude",
    )
    
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum directory depth to scan",
    )
    
    parser.add_argument(
        "--relative-to",
        type=str,
        default=None,
        help="Base path for relative path display",
    )
    
    parser.add_argument(
        "--ignore-missing",
        action="store_true",
        help="Hide missing (unresolved) file references from output",
    )
    
    parser.add_argument(
        "--ignore-remote",
        action="store_true",
        help="Hide remote (URL) references from output",
    )
    
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Include nodes that have no connections (by default, only connected nodes are shown)",
    )
    
    parser.add_argument(
        "--ignore-templates",
        action="store_true",
        help="Hide template paths (paths containing Jinja {{ }} placeholders)",
    )
    
    return parser.parse_args(args)


def main(args=None):
    """Main entry point."""
    parsed = parse_args(args)
    
    # Resolve paths
    root = Path(parsed.root).resolve()
    if not root.is_dir():
        print(f"Error: '{parsed.root}' is not a directory", file=sys.stderr)
        return 1
    
    base = Path(parsed.relative_to).resolve() if parsed.relative_to else root
    
    # Prepare scanning options
    include_ext: Optional[Set[str]] = None
    if parsed.include_ext:
        include_ext = set()
        for ext in parsed.include_ext:
            if not ext.startswith("."):
                ext = "." + ext
            include_ext.add(ext.lower())
    
    exclude_dirs: Optional[Set[str]] = None
    if parsed.exclude_dir:
        exclude_dirs = set(parsed.exclude_dir) | DEFAULT_EXCLUDE_DIRS
    
    # Build the graph
    try:
        graph = build_graph(
            root=root,
            include_ext=include_ext,
            exclude_dirs=exclude_dirs,
            max_depth=parsed.max_depth,
        )
    except Exception as e:
        print(f"Error scanning repository: {e}", file=sys.stderr)
        return 1
    
    # Determine whether to include missing, remote, and template references
    include_missing = not parsed.ignore_missing
    include_remote = not parsed.ignore_remote
    include_templates = not parsed.ignore_templates
    show_all = parsed.show_all
    
    # Generate output
    if parsed.format == "mermaid":
        output = to_mermaid(
            graph=graph,
            root=root,
            orientation=parsed.orientation,
            base=base,
            group_by_directory=parsed.group_by_dir,
            include_missing=include_missing,
            include_remote=include_remote,
            include_templates=include_templates,
            include_folders=True,
            show_all=show_all,
        )
    elif parsed.format == "json":
        output = to_json(
            graph=graph,
            root=root,
            base=base,
            include_missing=include_missing,
            include_remote=include_remote,
            include_templates=include_templates,
            include_folders=True,
            show_all=show_all,
        )
    else:  # ascii (default)
        output = to_ascii(
            graph=graph,
            root=root,
            base=base,
            style=parsed.ascii_style,
            include_missing=include_missing,
            include_remote=include_remote,
            include_templates=include_templates,
            include_folders=True,
            show_all=show_all,
        )
    
    # Write output
    if parsed.output:
        try:
            output_path = Path(parsed.output)
            output_path.write_text(output, encoding="utf-8")
            print(f"Output written to: {output_path}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output: {e}", file=sys.stderr)
            return 1
    else:
        print(output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
