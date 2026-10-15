"""
creds.py — the credential store.

Credentials live here and nowhere else. One secret per file, mode 0600, never
printed, never logged, never returned to the agent. The proxy reads them; the
agent cannot reach this directory (it is not in the agent's readable roots).

File layout:
    credentials/<name>     e.g. credentials/bluesky, credentials/smtp

The value is the raw secret (token, app password, etc.). For multi-field
credentials (host/user/pass), store a small JSON object instead — the proxy
knows how to read both.

Safety rules enforced here:
  * Writes are atomic and 0600.
  * Reads never log the value.
  * A `redact()` helper exists so callers can safely include a credential name
    in a message without ever including its value.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STORE = os.path.join(HERE, "credentials")


def _store() -> str:
    return os.environ.get("MUSE_PROXY_CREDS", DEFAULT_STORE)


def _safe_name(name: str) -> str:
    """Reject names that try to escape the store."""
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        raise ValueError(f"invalid credential name: {name!r}")
    return name


def put(name: str, value: str) -> None:
    """Store a credential value atomically with 0600 perms."""
    name = _safe_name(name)
    store = _store()
    os.makedirs(store, exist_ok=True)
    path = os.path.join(store, name)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(value)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def put_fields(name: str, fields: Dict[str, Any]) -> None:
    """Store a multi-field credential as JSON."""
    put(name, json.dumps(fields))


def get(name: str) -> Optional[str]:
    """
    Read a credential value. Returns None if absent.

    IMPORTANT: callers must never log or return this value to the agent.
    """
    name = _safe_name(name)
    path = os.path.join(_store(), name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def get_fields(name: str) -> Optional[Dict[str, Any]]:
    """Read a credential and parse it as JSON, if it is JSON."""
    raw = get(name)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"value": raw}


def exists(name: str) -> bool:
    try:
        return os.path.exists(os.path.join(_store(), _safe_name(name)))
    except ValueError:
        return False


def list_names() -> List[str]:
    store = _store()
    if not os.path.isdir(store):
        return []
    out = []
    for f in sorted(os.listdir(store)):
        if f.endswith(".tmp") or f in ("README.md", ".gitkeep"):
            continue
        out.append(f)
    return out


def redact(name: str) -> str:
    """A safe string for logs/messages: the name, never the value."""
    return f"<credential:{name}>"


def check_permissions() -> List[str]:
    """Return a list of problems (e.g. world-readable files). Empty = clean."""
    problems: List[str] = []
    store = _store()
    if not os.path.isdir(store):
        return problems
    for f in os.listdir(store):
        path = os.path.join(store, f)
        if not os.path.isfile(path) or f.endswith(".tmp"):
            continue
        mode = os.stat(path).st_mode & 0o777
        if mode & 0o077:  # any group/world bits
            problems.append(f"{f} has mode {oct(mode)} (should be 600)")
    return problems


def _main(argv) -> int:
    if not argv or argv[0] == "list":
        for n in list_names():
            print(f"  {redact(n)}")
        probs = check_permissions()
        for p in probs:
            print(f"  INSECURE: {p}")
        return 0 if not probs else 1
    if argv[0] == "check":
        probs = check_permissions()
        if not probs:
            print("OK — all credentials are 0600.")
            return 0
        for p in probs:
            print(f"INSECURE: {p}")
        return 1
    print("usage: creds.py [list | check]")
    return 2


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
