"""
logs.py — collect system logs and look for the agent's fingerprints.

Logs are where actions leave traces even when the actor tried to hide. We gather
auth logs, syslog, and any Muse Guard action log, then grep for the tell-tale
signs: new accounts, sudo use, network tools, and the names from the incident.
"""

from __future__ import annotations

import os
from typing import Dict, List

from ._util import read_text, write_artifact

LOG_FILES = [
    "/var/log/auth.log",
    "/var/log/secure",
    "/var/log/syslog",
    "/var/log/messages",
    "/var/log/cloud-init.log",
]

# Muse Guard's own logs (if present on the box).
MUSE_LOGS = [
    "/opt/muse-guard/logger/logs/actions.jsonl",
    "logger/logs/actions.jsonl",
]

SUSPICIOUS = ["useradd", "adduser", "usermod", "passwd", "sudo", "su ",
              "curl", "wget", "ssh", "nc ", "nmap", "crontab", "systemctl",
              "musefm", "muse3", "workers.dev", "new account", "created"]


def _tail(path: str, max_lines: int = 5000) -> str:
    content = read_text(path, max_bytes=5_000_000)
    if content is None:
        return ""
    lines = content.splitlines()
    return "\n".join(lines[-max_lines:])


def run(out_dir: str) -> Dict:
    findings: List[str] = []
    artifacts: List[str] = []
    blob: List[str] = []

    for path in LOG_FILES:
        text = _tail(path)
        if text:
            blob.append(f"===== {path} (tail) =====\n{text}")
            for line in text.splitlines():
                low = line.lower()
                if any(s in low for s in SUSPICIOUS):
                    findings.append(f"{os.path.basename(path)}: {line.strip()[:160]}")

    # Muse Guard's own action log is gold — copy it whole if present.
    for path in MUSE_LOGS:
        if os.path.exists(path):
            text = read_text(path, max_bytes=10_000_000)
            if text:
                artifacts.append(write_artifact(out_dir, "muse_action_log.jsonl", text))
                findings.append(f"Muse Guard action log found: {path}")

    combined = "\n".join(blob) if blob else "(no system logs found)"
    artifacts.append(write_artifact(out_dir, "system_logs.txt", combined))

    ok = not findings
    summary = ("no suspicious log lines" if ok
               else f"{len(findings)} suspicious log line(s)")
    return {"name": "logs", "ok": ok, "summary": summary,
            "findings": findings, "artifacts": artifacts}
