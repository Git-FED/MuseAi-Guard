"""
cloud.py — check cloud CLI state for resources the agent may have created.

The original incident involved creating accounts and reaching infrastructure.
Cloud CLIs (AWS, GCP, Azure, Cloudflare) are how a box spins up *new* things
that outlive it: workers, buckets, VMs, DNS records. We inventory the CLI
configs and, where the CLI is present, list a few high-signal resources.

All commands are read-only and best-effort. If a CLI is absent or unauthenticated,
we note it and move on.
"""

from __future__ import annotations

import os
from typing import Dict, List

from ._util import read_text, run_cmd, write_artifact

CONFIG_FILES = [
    "~/.aws/credentials",
    "~/.aws/config",
    "~/.config/gcloud/configurations",
    "~/.azure/azureProfile.json",
    "~/.wrangler/config/default.toml",
    "~/.config/wrangler/config.toml",
    "~/.cloudflared",
    "~/.config/heroku",
    "~/.fly/config.yml",
    "~/.vercel/auth.json",
    "~/.netlify/config.json",
]


def run(out_dir: str) -> Dict:
    findings: List[str] = []
    artifacts: List[str] = []
    blob: List[str] = []

    # 1. which CLIs are present
    clis = ["aws", "gcloud", "az", "wrangler", "cloudflared", "flyctl", "heroku",
            "vercel", "netlify", "doctl", "linode-cli"]
    present = []
    for cli in clis:
        rc, out, err = run_cmd(["which", cli])
        if rc == 0 and out.strip():
            present.append((cli, out.strip()))
            findings.append(f"cloud CLI present: {cli} ({out.strip()})")
    blob.append("===== CLIs present =====\n" +
                "\n".join(f"{c}: {p}" for c, p in present) if present else "(none)")

    # 2. config files present
    for p in CONFIG_FILES:
        path = os.path.expanduser(p)
        if os.path.exists(path):
            findings.append(f"cloud config present: {path}")

    # 3. read-only resource listings (best effort)
    listings = [
        (["aws", "iam", "list-users", "--output", "json"], "aws_iam_users.json"),
        (["aws", "s3", "ls"], "aws_s3.txt"),
        (["gcloud", "projects", "list"], "gcloud_projects.txt"),
        (["az", "account", "list"], "az_accounts.json"),
        (["wrangler", "whoami"], "wrangler_whoami.txt"),
        (["doctl", "compute", "droplet", "list"], "do_droplets.txt"),
    ]
    for cmd, fname in listings:
        rc, out, err = run_cmd(cmd, timeout=25)
        if rc == 0 and out.strip():
            artifacts.append(write_artifact(out_dir, fname, out))
            blob.append(f"===== {' '.join(cmd)} =====\n{out}")

    artifacts.append(write_artifact(out_dir, "cloud.txt", "\n".join(blob)))

    ok = not findings
    summary = ("no cloud CLI/config found" if ok
               else f"{len(findings)} cloud indicator(s)")
    return {"name": "cloud", "ok": ok, "summary": summary,
            "findings": findings, "artifacts": artifacts}
