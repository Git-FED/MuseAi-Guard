"""
credentials.py — find where secrets live so you can rotate them ALL.

This probe does not try to steal secrets; it inventories where they are, so that
after an incident you can rotate every one. The rule from the runbook: assume
compromise, rotate everything the box could reach.

We look for:
  * well-known credential files (~/.aws/credentials, ~/.netrc, ~/.docker/config.json,
    ~/.config/gh/hosts.yml, ~/.config/gcloud, ~/.kube/config, .env files)
  * private keys
  * files whose names suggest tokens
We record PATHS and existence, never values.
"""

from __future__ import annotations

import os
from typing import Dict, List

from ._util import write_artifact

KNOWN_CRED_FILES = [
    "~/.aws/credentials",
    "~/.aws/config",
    "~/.netrc",
    "~/.docker/config.json",
    "~/.config/gh/hosts.yml",
    "~/.config/gcloud/credentials.db",
    "~/.kube/config",
    "~/.npmrc",
    "~/.pypirc",
    "~/.git-credentials",
    "~/.config/rclone/rclone.conf",
    "~/.ssh/id_rsa",
    "~/.ssh/id_ed25519",
]

ENV_NAMES = [".env", ".env.local", ".env.production", "secrets.json",
             "credentials.json", "token.json", "auth.json"]

SCAN_ROOTS = ["/root", "/home", "/opt", "/srv", "/etc", "/var/www"]


def _expand(p: str) -> str:
    return os.path.expanduser(p)


def run(out_dir: str) -> Dict:
    findings: List[str] = []
    artifacts: List[str] = []
    found_paths: List[str] = []

    # 1. known credential files
    for p in KNOWN_CRED_FILES:
        path = _expand(p)
        if os.path.exists(path):
            found_paths.append(path)

    # 2. .env-style files under scan roots
    for root in SCAN_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if any(seg in dirpath for seg in ("/proc", "/sys", "/.git/")):
                dirnames[:] = []
                continue
            for fn in filenames:
                if fn in ENV_NAMES:
                    found_paths.append(os.path.join(dirpath, fn))

    # 3. record paths only (never values)
    listing = "\n".join(sorted(set(found_paths))) if found_paths else "(none found)"
    artifacts.append(write_artifact(out_dir, "credential_locations.txt", listing))

    for p in sorted(set(found_paths)):
        findings.append(f"credential file present (rotate if this box was compromised): {p}")

    # "ok" here means "nothing found" — but finding credentials is normal. We
    # mark ok=True and let the summary carry the count, because the point is
    # inventory, not alarm.
    summary = f"{len(set(found_paths))} credential file(s) located (rotate all if compromised)"
    return {"name": "credentials", "ok": True, "summary": summary,
            "findings": findings, "artifacts": artifacts}
