"""
cron.py — find scheduled jobs the agent (or anyone) may have planted.

Cron is a classic persistence mechanism: a line in a crontab runs your code
again and again, long after you have logged out. The original incident's agent
was goal-directed; scheduled jobs are exactly how such a system keeps acting
when nobody is watching.

We look in every place cron hides:
  * system crontabs (/etc/crontab, /etc/cron.d/*)
  * per-user crontabs (/var/spool/cron/crontabs/*, /var/spool/cron/*)
  * the periodic dirs (/etc/cron.{hourly,daily,weekly,monthly}/*)
"""

from __future__ import annotations

import os
from typing import Dict, List

from ._util import read_text, run_cmd, write_artifact

CRON_FILES = [
    "/etc/crontab",
    "/etc/anacrontab",
]
CRON_DIRS = [
    "/etc/cron.d",
    "/var/spool/cron",
    "/var/spool/cron/crontabs",
    "/etc/cron.hourly",
    "/etc/cron.daily",
    "/etc/cron.weekly",
    "/etc/cron.monthly",
]

# Substrings that suggest something worth a human's eyes.
SUSPICIOUS = ["curl", "wget", "python", "bash -c", "sh -c", "nc ", "ncat",
              "base64", "/tmp/", "/dev/shm", "eval", "chmod +x"]


def run(out_dir: str) -> Dict:
    findings: List[str] = []
    artifacts: List[str] = []
    blob: List[str] = []

    # 1. system crontab files
    for path in CRON_FILES:
        content = read_text(path)
        if content:
            blob.append(f"===== {path} =====\n{content}")

    # 2. cron directories
    for d in CRON_DIRS:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            path = os.path.join(d, name)
            if os.path.isfile(path):
                content = read_text(path)
                if content is not None:
                    blob.append(f"===== {path} =====\n{content}")

    # 3. per-user crontabs via crontab -l for the current user
    rc, out, err = run_cmd(["crontab", "-l"])
    if rc == 0 and out.strip():
        blob.append(f"===== crontab -l =====\n{out}")

    combined = "\n".join(blob) if blob else "(no cron files found)"
    artifacts.append(write_artifact(out_dir, "cron.txt", combined))

    # 4. flag suspicious lines
    for line in combined.splitlines():
        low = line.lower()
        if line.strip().startswith("#") or not line.strip():
            continue
        if any(s in low for s in SUSPICIOUS):
            findings.append(line.strip())

    ok = not findings
    summary = ("no suspicious cron entries" if ok
               else f"{len(findings)} suspicious cron line(s)")
    return {"name": "cron", "ok": ok, "summary": summary,
            "findings": findings, "artifacts": artifacts}
