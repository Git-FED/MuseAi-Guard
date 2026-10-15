#!/usr/bin/env python3
"""
process_watcher.py — Notice processes that should not be running.

The agent is supposed to be a *proposer*, not a background daemon that spawns
shells, cron jobs, or long-lived helpers. This watcher maintains an allowlist of
processes that are expected and flags anything else that looks suspicious.

It is intentionally conservative: it reports, it does not kill. Killing is a
human decision (or the kill switch's job). The value here is visibility.

Usage:
  process_watcher.py baseline     # record currently-running command names
  process_watcher.py check        # flag anything not in the allowlist
  process_watcher.py list         # print all running processes
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOW_FILE = os.path.join(HERE, "process_allowlist.json")

# Processes we expect to see in a healthy Muse Guard box. Anything matching
# these substrings is considered "known". Everything else is reported.
DEFAULT_ALLOW = [
    "systemd", "init", "sshd", "cron", "dbus", "rsyslog", "journald",
    "python", "pytest", "node", "npm", "bash", "sh", "tmux", "vim",
    "chromium", "chrome", "grep", "cat", "ls", "ps", "top", "sleep",
    "muse", "executor", "proxy", "watchdog",
]

# Substrings that, if seen, are always reported regardless of the allowlist.
SUSPICIOUS = [
    "nc ", "ncat", "netcat", "socat", "nmap", "masscan", "hydra",
    "curl -", "wget ", "scp ", "rsync ", "ssh ", "reverse", "backdoor",
    "miner", "xmrig", "cryptonight",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_processes() -> List[Dict[str, object]]:
    """Return a list of {pid, comm, cmdline} for all readable processes."""
    procs: List[Dict[str, object]] = []
    proc_root = "/proc"
    if not os.path.isdir(proc_root):
        return procs
    for name in os.listdir(proc_root):
        if not name.isdigit():
            continue
        pid = int(name)
        comm_path = os.path.join(proc_root, name, "comm")
        cmd_path = os.path.join(proc_root, name, "cmdline")
        try:
            with open(comm_path, "r", encoding="utf-8", errors="replace") as fh:
                comm = fh.read().strip()
            with open(cmd_path, "rb") as fh:
                raw = fh.read().replace(b"\x00", b" ").decode("utf-8", "replace").strip()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        procs.append({"pid": pid, "comm": comm, "cmdline": raw})
    return procs


def load_allow() -> List[str]:
    if os.path.exists(ALLOW_FILE):
        with open(ALLOW_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh).get("allow", DEFAULT_ALLOW)
    return DEFAULT_ALLOW


def write_allow(allow: List[str]) -> None:
    with open(ALLOW_FILE, "w", encoding="utf-8") as fh:
        json.dump({"created": _now(), "allow": allow}, fh, indent=2)


def check() -> Dict[str, object]:
    allow = load_allow()
    unknown: List[Dict[str, object]] = []
    suspicious: List[Dict[str, object]] = []

    for p in list_processes():
        blob = f"{p['comm']} {p['cmdline']}".lower()
        if any(s in blob for s in SUSPICIOUS):
            suspicious.append(p)
        elif not any(a.lower() in blob for a in allow):
            unknown.append(p)

    return {
        "ok": not suspicious,  # unknown processes are informational; suspicious are not
        "suspicious": suspicious,
        "unknown": unknown,
        "when": _now(),
    }


def _main(argv: List[str]) -> int:
    cmd = argv[0] if argv else "check"
    if cmd == "list":
        for p in list_processes():
            print(f"{p['pid']:>7}  {p['comm']:<16} {p['cmdline'][:80]}")
        return 0
    if cmd == "baseline":
        names = sorted({str(p["comm"]) for p in list_processes() if p["comm"]})
        write_allow(names)
        print(f"Allowlist written with {len(names)} names -> {ALLOW_FILE}")
        return 0
    if cmd == "check":
        report = check()
        if report["suspicious"]:
            print("SUSPICIOUS PROCESSES:")
            for p in report["suspicious"]:
                print(f"  pid {p['pid']}: {p['cmdline'][:100]}")
        if report["unknown"]:
            print(f"Unknown (informational) processes: {len(report['unknown'])}")
            for p in report["unknown"][:20]:
                print(f"  pid {p['pid']}: {p['comm']}")
        if report["ok"]:
            print("OK — no suspicious processes.")
            return 0
        return 1
    print("usage: process_watcher.py [list | baseline | check]")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
