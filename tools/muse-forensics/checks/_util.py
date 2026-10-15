"""
_util.py — shared helpers for forensic probes.

Kept tiny and dependency-free so the probes run on a bare box (or a mounted
disk) with nothing but Python 3.
"""

from __future__ import annotations

import os
import subprocess
from typing import List, Optional, Tuple


def run_cmd(cmd: List[str], timeout: int = 15) -> Tuple[int, str, str]:
    """Run a command, returning (returncode, stdout, stderr). Never raises."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", f"not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(cmd)}"
    except Exception as exc:  # pragma: no cover
        return 1, "", str(exc)


def read_text(path: str, max_bytes: int = 2_000_000) -> Optional[str]:
    """Read a text file if it exists and is not too large. Never raises."""
    try:
        if not os.path.exists(path):
            return None
        if os.path.getsize(path) > max_bytes:
            return f"<file too large: {os.path.getsize(path)} bytes>"
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, PermissionError):
        return None


def write_artifact(out_dir: str, name: str, content: str) -> str:
    """Write a finding artifact under out_dir and return its path."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def find_files(roots: List[str], names: List[str], max_depth: int = 6) -> List[str]:
    """Find files whose basename is in `names` under any of `roots`."""
    found: List[str] = []
    wanted = set(names)
    for root in roots:
        if not os.path.isdir(root):
            continue
        base_depth = root.rstrip("/").count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root):
            depth = dirpath.rstrip("/").count(os.sep) - base_depth
            if depth > max_depth:
                dirnames[:] = []
                continue
            for fn in filenames:
                if fn in wanted:
                    found.append(os.path.join(dirpath, fn))
    return found
