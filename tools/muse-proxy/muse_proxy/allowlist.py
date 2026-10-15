"""
allowlist.py — exact-host, default-deny egress control.

The allowlist is the difference between "the agent can reach the internet" and
"the agent can reach these exact hosts." There are no wildcards. A host that is
not on the list is refused, and the refusal is logged.

Why no wildcards: the original incident reached infrastructure it should never
have touched, and broad patterns like `*.workers.dev` are exactly how that
happens. Exact hostnames force a human to name each destination.

Config file (JSON):
    {
      "domains": {
        "bsky.social": {"credential": "bluesky", "scheme": "https"},
        "mastodon.social": {"credential": "mastodon", "scheme": "https"}
      },
      "blocked": ["*.workers.dev", "cloudflare.com"]
    }

`blocked` is a belt-and-suspenders deny list that is checked first, even if a
domain somehow appears in `domains`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ALLOWLIST = os.path.join(HERE, "allowlist.json")


def _path() -> str:
    return os.environ.get("MUSE_PROXY_ALLOWLIST", DEFAULT_ALLOWLIST)


def load() -> Dict[str, Any]:
    path = _path()
    if not os.path.exists(path):
        # Fail-closed: no allowlist means nothing is allowed.
        return {"domains": {}, "blocked": []}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"domains": {}, "blocked": []}
    data.setdefault("domains", {})
    data.setdefault("blocked", [])
    return data


def _matches_blocked(host: str, blocked: List[str]) -> bool:
    """Match a host against blocked patterns. Supports a leading '*.' wildcard."""
    host = host.lower().rstrip(".")
    for pat in blocked:
        pat = pat.lower().rstrip(".")
        if pat.startswith("*."):
            suffix = pat[2:]
            if host == suffix or host.endswith("." + suffix):
                return True
        elif host == pat:
            return True
    return False


def is_allowed(host: str) -> bool:
    """
    True only if `host` is an exact allowlisted domain and not blocked.

    Subdomain handling: an allowlisted `bsky.social` also allows
    `api.bsky.social` (a subdomain of an allowed host), because providers
    routinely serve APIs from subdomains of the domain you named. We do NOT
    allow the reverse (allowing a parent does not allow a child unless the child
    is under the allowed host).
    """
    data = load()
    host = (host or "").lower().rstrip(".")
    if not host:
        return False
    if _matches_blocked(host, data.get("blocked", [])):
        return False

    domains = data.get("domains", {})
    keys = domains.keys() if isinstance(domains, dict) else domains
    for allowed in keys:
        allowed = allowed.lower().rstrip(".")
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


def credential_for(host: str) -> Optional[str]:
    """Return the credential name associated with a host, if any."""
    data = load()
    domains = data.get("domains", {})
    if not isinstance(domains, dict):
        return None
    host = (host or "").lower().rstrip(".")
    for allowed, meta in domains.items():
        allowed = allowed.lower().rstrip(".")
        if host == allowed or host.endswith("." + allowed):
            if isinstance(meta, dict):
                return meta.get("credential")
    return None


def scheme_for(host: str) -> str:
    data = load()
    domains = data.get("domains", {})
    if isinstance(domains, dict):
        host = (host or "").lower().rstrip(".")
        for allowed, meta in domains.items():
            allowed = allowed.lower().rstrip(".")
            if host == allowed or host.endswith("." + allowed):
                if isinstance(meta, dict):
                    return meta.get("scheme", "https")
    return "https"


def domains() -> List[str]:
    data = load()
    d = data.get("domains", {})
    return sorted(d.keys()) if isinstance(d, dict) else sorted(d)


def _main(argv) -> int:
    if not argv or argv[0] == "list":
        for d in domains():
            print(f"  {d}  (cred={credential_for(d)}, scheme={scheme_for(d)})")
        blocked = load().get("blocked", [])
        if blocked:
            print("blocked:")
            for b in blocked:
                print(f"  {b}")
        return 0
    if argv[0] == "check" and len(argv) > 1:
        host = argv[1]
        print("ALLOWED" if is_allowed(host) else "DENIED", host)
        return 0 if is_allowed(host) else 1
    print("usage: allowlist.py [list | check <host>]")
    return 2


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
