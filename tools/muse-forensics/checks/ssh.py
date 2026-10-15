"""
ssh.py — look for back-door access: authorized_keys, configs, known hosts.

SSH is how a foothold becomes permanent. An attacker (or a runaway agent that
wanted remote reach) would add a key to authorized_keys, or write a config that
tunnels somewhere. We collect:
  * authorized_keys (every user)
  * ~/.ssh/config, known_hosts
  * the sshd_config (to see if password auth or root login was enabled)
"""

from __future__ import annotations

import os
from typing import Dict, List

from ._util import find_files, read_text, write_artifact

SSH_NAMES = ["authorized_keys", "authorized_keys2", "id_rsa", "id_ed25519",
             "id_ecdsa", "config", "known_hosts"]


def _home_dirs() -> List[str]:
    out = ["/root"]
    if os.path.isdir("/home"):
        for name in os.listdir("/home"):
            out.append(os.path.join("/home", name))
    return [h for h in out if os.path.isdir(h)]


def run(out_dir: str) -> Dict:
    findings: List[str] = []
    artifacts: List[str] = []
    blob: List[str] = []

    # 1. ssh files in home dirs
    roots = [os.path.join(h, ".ssh") for h in _home_dirs()] + ["/etc/ssh"]
    files = find_files(roots, SSH_NAMES, max_depth=3)
    for path in files:
        # Never dump private key material; note its presence only.
        base = os.path.basename(path)
        if base.startswith("id_") and not base.endswith(".pub"):
            blob.append(f"===== {path} ===== (private key present, contents NOT copied)")
            findings.append(f"private key present: {path}")
            continue
        content = read_text(path, max_bytes=500_000)
        if content is not None:
            blob.append(f"===== {path} =====\n{content}")
            if base.startswith("authorized_keys"):
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        findings.append(f"authorized_key in {path}: {line[:80]}…")

    # 2. sshd_config posture
    sshd = read_text("/etc/ssh/sshd_config", max_bytes=200_000)
    if sshd:
        blob.append(f"===== /etc/ssh/sshd_config =====\n{sshd}")
        for line in sshd.splitlines():
            low = line.lower().strip()
            if low.startswith("permitrootlogin") and "no" not in low:
                findings.append(f"sshd: {line.strip()}")
            if low.startswith("passwordauthentication") and "yes" in low:
                findings.append(f"sshd: {line.strip()}")

    combined = "\n".join(blob) if blob else "(no ssh artifacts found)"
    artifacts.append(write_artifact(out_dir, "ssh.txt", combined))

    ok = not findings
    summary = ("no ssh back-door indicators" if ok
               else f"{len(findings)} ssh finding(s)")
    return {"name": "ssh", "ok": ok, "summary": summary,
            "findings": findings, "artifacts": artifacts}
