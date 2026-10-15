"""
files.py — find recently modified and suspicious files.

The question this answers: "what changed, and when?" On a box that was just
"pulled", the recently-modified files are the story. We look at:
  * files modified in the last N days under common locations
  * executables in temp dirs (/tmp, /dev/shm, /var/tmp)
  * anything with an obvious agent/muse/bot name
"""

from __future__ import annotations

import os
import time
from typing import Dict, List

from ._util import write_artifact

SCAN_ROOTS = ["/etc", "/opt", "/srv", "/var", "/tmp", "/dev/shm", "/root", "/home", "/usr/local"]
TEMP_DIRS = ["/tmp", "/dev/shm", "/var/tmp"]
NAME_HINTS = ["muse", "agent", "bot", "worker", "rogue", "payload", "backdoor"]

RECENT_DAYS = 14
MAX_RESULTS = 500


def _recent_files(root: str, cutoff: float) -> List[str]:
    out: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip noisy/irrelevant trees.
        if any(seg in dirpath for seg in ("/proc", "/sys", "/dev/pts", "/run")):
            dirnames[:] = []
            continue
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path, follow_symlinks=False)
            except OSError:
                continue
            if st.st_mtime >= cutoff:
                out.append(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(st.st_mtime))}  {path}")
            if len(out) >= MAX_RESULTS:
                return out
    return out


def _executables_in_temps() -> List[str]:
    out: List[str] = []
    for d in TEMP_DIRS:
        if not os.path.isdir(d):
            continue
        for dirpath, _, filenames in os.walk(d):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path, follow_symlinks=False)
                except OSError:
                    continue
                if st.st_mode & 0o111:  # any execute bit
                    out.append(path)
    return out


def run(out_dir: str) -> Dict:
    findings: List[str] = []
    artifacts: List[str] = []
    cutoff = time.time() - RECENT_DAYS * 86400

    # 1. recently modified files
    recent: List[str] = []
    for root in SCAN_ROOTS:
        if os.path.isdir(root):
            recent.extend(_recent_files(root, cutoff))
    recent_text = "\n".join(sorted(recent)) if recent else "(none)"
    artifacts.append(write_artifact(out_dir, "recent_files.txt", recent_text))

    # 2. executables in temp dirs (a classic staging location)
    execs = _executables_in_temps()
    exec_text = "\n".join(execs) if execs else "(none)"
    artifacts.append(write_artifact(out_dir, "temp_executables.txt", exec_text))
    for e in execs:
        findings.append(f"executable in temp: {e}")

    # 3. name hints in recently-modified files
    for line in recent:
        low = line.lower()
        if any(h in low for h in NAME_HINTS):
            findings.append(f"suspicious name: {line}")

    ok = not findings
    summary = (f"{len(recent)} recent file(s), no red flags" if ok
               else f"{len(findings)} file finding(s)")
    return {"name": "files", "ok": ok, "summary": summary,
            "findings": findings, "artifacts": artifacts}
