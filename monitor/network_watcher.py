#!/usr/bin/env python3
"""
network_watcher.py — Watch outbound connections against the allowlist.

The egress proxy is the primary control on what the agent can reach. This
watcher is the independent check: it reads the kernel's list of established
connections and flags any that are *not* to an allowlisted host and *not* to a
private/loopback address.

If the proxy is the lock, this is the security camera pointed at the door.

Usage:
  network_watcher.py check     # flag unexpected outbound connections
  network_watcher.py list      # print all established connections
"""

from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime, timezone
from typing import Dict, List, Set

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
ALLOWLIST = os.path.join(PROJECT_ROOT, "proxy", "allowlist.json")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_private(ip: str) -> bool:
    """True for loopback and RFC1918 private ranges (always allowed)."""
    if ip.startswith("127.") or ip == "::1":
        return True
    if ip.startswith("10.") or ip.startswith("192.168."):
        return True
    if ip.startswith("172."):
        try:
            second = int(ip.split(".")[1])
            if 16 <= second <= 31:
                return True
        except (ValueError, IndexError):
            pass
    if ip.startswith("169.254."):  # link-local
        return True
    return False


def load_allowed_domains() -> Set[str]:
    if not os.path.exists(ALLOWLIST):
        return set()
    with open(ALLOWLIST, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return set(data.get("domains", {}).keys()) | set(data.get("domains", []) or [])


def _parse_proc_net(path: str) -> List[Dict[str, str]]:
    """Parse /proc/net/tcp or tcp6 into a list of connection dicts."""
    conns: List[Dict[str, str]] = []
    if not os.path.exists(path):
        return conns
    with open(path, "r", encoding="utf-8") as fh:
        next(fh, None)  # header
        for line in fh:
            parts = line.split()
            if len(parts) < 4:
                continue
            state = parts[3]
            # 01 == ESTABLISHED
            if state != "01":
                continue
            rem = parts[2]
            ip_hex, port_hex = rem.split(":")
            ip = _hex_to_ip(ip_hex, is_v6="6" in os.path.basename(path))
            try:
                port = int(port_hex, 16)
            except ValueError:
                port = 0
            conns.append({"ip": ip, "port": str(port)})
    return conns


def _hex_to_ip(hex_str: str, is_v6: bool = False) -> str:
    try:
        if is_v6:
            raw = bytes.fromhex(hex_str)
            # /proc stores v6 as 4 little-endian 32-bit words
            words = [raw[i:i + 4][::-1] for i in range(0, 16, 4)]
            packed = b"".join(words)
            return socket.inet_ntop(socket.AF_INET6, packed)
        raw = bytes.fromhex(hex_str)
        return socket.inet_ntoa(raw[::-1])
    except Exception:
        return hex_str


def list_connections() -> List[Dict[str, str]]:
    conns = []
    conns.extend(_parse_proc_net("/proc/net/tcp"))
    conns.extend(_parse_proc_net("/proc/net/tcp6"))
    return conns


def check() -> Dict[str, object]:
    allowed = load_allowed_domains()
    unexpected: List[Dict[str, str]] = []

    for c in list_connections():
        ip = c["ip"]
        if _is_private(ip):
            continue
        # Resolve reverse DNS to compare against the domain allowlist.
        host = ""
        try:
            host = socket.gethostbyaddr(ip)[0]
        except (socket.herror, socket.gaierror, OSError):
            host = ""

        if host and any(host.endswith(d) for d in allowed):
            continue
        unexpected.append({"ip": ip, "port": c["port"], "host": host})

    return {"ok": not unexpected, "unexpected": unexpected, "when": _now()}


def _main(argv: List[str]) -> int:
    cmd = argv[0] if argv else "check"
    if cmd == "list":
        for c in list_connections():
            print(f"{c['ip']}:{c['port']}")
        return 0
    if cmd == "check":
        report = check()
        if report["ok"]:
            print("OK — no unexpected outbound connections.")
            return 0
        print("UNEXPECTED OUTBOUND CONNECTIONS:")
        for c in report["unexpected"]:
            print(f"  {c['ip']}:{c['port']}  ({c['host'] or 'no reverse DNS'})")
        return 1
    print("usage: network_watcher.py [list | check]")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
