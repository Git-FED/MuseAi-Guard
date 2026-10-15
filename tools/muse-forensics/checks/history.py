"""
history.py — collect shell history, which is where intent leaks.

Shell history is the closest thing to a transcript of what a human (or an agent
with a shell) actually typed. Even if the agent "hid" its actions, the shell
often remembers. We gather:
  * bash history (~/.bash_history, /root/.bash_history)
  * zsh history (~/.zsh_history)
  * python history (~/.python_history)
  * any *.history under home directories
"""

from __future__ import annotations

import os
from typing import Dict, List

from ._util import find_files, read_text, write_artifact

HISTORY_NAMES = [".bash_history", ".zsh_history", ".python_history",
                 ".sh_history", ".history", ".node_repl_history"]

# Commands that suggest network use, persistence, or exfiltration.
SUSPICIOUS = ["curl", "wget", "ssh ", "scp ", "rsync ", "nc ", "ncat", "socat",
              "nmap", "chmod +x", "crontab", "systemctl enable", "base64",
              "python -c", "python3 -c", "eval", ">/dev/tcp", "musefm",
              "workers.dev", "token", "password", "secret"]


def _home_dirs() -> List[str]:
    homes = ["/root", "/home"]
    out = ["/root"]
    if os.path.isdir("/home"):
        for name in os.listdir("/home"):
            out.append(os.path.join("/home", name))
    return [h for h in out if os.path.isdir(h)] + ([] if os.path.isdir("/home") else [])


def run(out_dir: str) -> Dict:
    findings: List[str] = []
    artifacts: List[str] = []
    blob: List[str] = []

    roots = _home_dirs()
    files = find_files(roots, HISTORY_NAMES, max_depth=3)
    # Also scan a few common non-home spots.
    for extra in ["/var/log/agent", "/tmp"]:
        files.extend(find_files([extra], HISTORY_NAMES, max_depth=3))

    for path in files:
        content = read_text(path, max_bytes=1_000_000)
        if content is None:
            continue
        blob.append(f"===== {path} =====\n{content}")
        for line in content.splitlines():
            low = line.lower()
            if any(s in low for s in SUSPICIOUS):
                findings.append(f"{path}: {line.strip()}")

    combined = "\n".join(blob) if blob else "(no history files found)"
    artifacts.append(write_artifact(out_dir, "history.txt", combined))

    ok = not findings
    summary = ("no suspicious history commands" if ok
               else f"{len(findings)} suspicious history line(s)")
    return {"name": "history", "ok": ok, "summary": summary,
            "findings": findings, "artifacts": artifacts}
