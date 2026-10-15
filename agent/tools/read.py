#!/usr/bin/env python3
"""
read.py — The agent's safe read tool.

The agent is allowed to *read* a defined set of things: its own persona files,
its memory, and the workspace. It is not allowed to read arbitrary files on the
host (no /etc/shadow, no SSH keys, no other users' homes).

This tool enforces that boundary by resolving every requested path and checking
it against an allowlist of roots. Symlinks are resolved first, so a symlink
pointing outside the sandbox is rejected.

Usage:
    from agent.tools import read
    text = read.file("memory/topics/projects.md")
"""

from __future__ import annotations

import os
from typing import Optional

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))

# Roots the agent may read from. Everything else is denied.
READABLE_ROOTS = [
    os.path.join(PROJECT_ROOT, "persona"),
    os.path.join(PROJECT_ROOT, "memory"),
    os.path.join(PROJECT_ROOT, "docs"),
    os.path.join(PROJECT_ROOT, "workspace"),
]

MAX_BYTES = 1_000_000  # refuse to slurp gigantic files


class AccessDenied(Exception):
    """Raised when a path is outside the readable roots."""


def _resolve(path: str) -> str:
    """Resolve a path relative to the project root and canonicalize it."""
    if not os.path.isabs(path):
        path = os.path.join(PROJECT_ROOT, path)
    return os.path.realpath(path)


def _is_allowed(real_path: str) -> bool:
    for root in READABLE_ROOTS:
        real_root = os.path.realpath(root)
        if real_path == real_root or real_path.startswith(real_root + os.sep):
            return True
    return False


def file(path: str) -> str:
    """
    Read a file, enforcing the readable-roots allowlist.

    Raises AccessDenied if the path escapes the sandbox, FileNotFoundError if it
    does not exist, and ValueError if it is too large.
    """
    real = _resolve(path)
    if not _is_allowed(real):
        raise AccessDenied(f"read denied (outside sandbox): {path}")

    if not os.path.exists(real):
        raise FileNotFoundError(path)

    size = os.path.getsize(real)
    if size > MAX_BYTES:
        raise ValueError(f"file too large ({size} bytes): {path}")

    with open(real, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def listdir(path: str = ".") -> list:
    """List a directory inside the sandbox."""
    real = _resolve(path)
    if not _is_allowed(real):
        raise AccessDenied(f"list denied (outside sandbox): {path}")
    if not os.path.isdir(real):
        raise NotADirectoryError(path)
    return sorted(os.listdir(real))


def _main(argv) -> int:
    if not argv:
        print("usage: read.py <path> | read.py --ls <dir>")
        return 2
    try:
        if argv[0] == "--ls":
            for name in listdir(argv[1] if len(argv) > 1 else "."):
                print(name)
        else:
            print(file(argv[0]))
    except (AccessDenied, FileNotFoundError, ValueError, NotADirectoryError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
