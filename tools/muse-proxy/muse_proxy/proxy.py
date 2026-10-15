"""
proxy.py — the egress proxy. The only door to the outside world.

Everything that leaves the box goes through here. The proxy:
  1. Refuses if the kill switch is engaged (fail-closed).
  2. Checks the target host against the exact allowlist (default-deny).
  3. Loads the credential for that host from the store.
  4. Makes the request.
  5. Logs the request (host, method, result — never the credential).

The agent calls `request(...)`; it never calls `urllib` itself and never sees a
credential. Even a fully hijacked agent cannot exfiltrate a key it never had.

This module is deliberately small and boring. Boring is auditable.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from . import allowlist, creds

# Make the kill switch importable whether or not muse_guard is installed.
def _kill_locked() -> bool:
    try:
        from muse_guard import kill  # type: ignore
        return kill.is_locked()
    except Exception:
        # If the kill switch is unavailable, fail closed.
        return True


class ProxyDenied(Exception):
    """Raised when the proxy refuses a request (kill switch, allowlist)."""


def _log(event: Dict[str, Any]) -> None:
    """Best-effort structured log to stderr; never includes secrets."""
    try:
        sys.stderr.write("proxy " + json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def request(
    host: str,
    *,
    method: str = "GET",
    path: str = "/",
    json_body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    credential: Optional[str] = None,
    timeout: int = 20,
) -> Dict[str, Any]:
    """
    Make an allowlisted outbound request on the caller's behalf.

    Returns a dict: {"ok": bool, "status": int, "body": str, "error": str?}.

    Raises ProxyDenied if the kill switch is engaged or the host is not allowed.
    """
    host = (host or "").strip()
    parsed = urlparse(host if "://" in host else f"//{host}")
    hostname = parsed.hostname or host

    # 1. kill switch (fail-closed)
    if _kill_locked():
        _log({"event": "denied", "reason": "kill switch", "host": hostname})
        raise ProxyDenied("kill switch engaged")

    # 2. allowlist (default-deny)
    if not allowlist.is_allowed(hostname):
        _log({"event": "denied", "reason": "not allowlisted", "host": hostname})
        raise ProxyDenied(f"host not allowlisted: {hostname}")

    # 3. credential
    scheme = allowlist.scheme_for(hostname)
    cred_name = credential or allowlist.credential_for(hostname)
    auth_headers = dict(headers or {})
    if cred_name:
        secret = creds.get(cred_name)
        if secret is not None:
            # Providers differ in how they want the secret; a common convention
            # is a bearer token. Callers can override via `headers`.
            auth_headers.setdefault("Authorization", f"Bearer {secret}")
        # NOTE: we never log `secret`.

    url = f"{scheme}://{hostname}{path}"
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        auth_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, method=method.upper(), headers=auth_headers)

    # 4. make the request
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            status = resp.status
            _log({"event": "ok", "host": hostname, "method": method, "status": status,
                  "cred": creds.redact(cred_name) if cred_name else None})
            return {"ok": True, "status": status, "body": body}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace") if exc.fp else ""
        _log({"event": "http_error", "host": hostname, "status": exc.code})
        return {"ok": False, "status": exc.code, "body": body, "error": str(exc)}
    except Exception as exc:  # network error, timeout, etc.
        _log({"event": "error", "host": hostname, "error": str(exc)})
        return {"ok": False, "status": 0, "body": "", "error": str(exc)}


def selftest() -> int:
    """
    Verify the proxy's controls without touching the network.

    Returns 0 if the cage behaves, 1 otherwise.
    """
    problems = []
    # kill switch should be readable
    try:
        locked = _kill_locked()
        print(f"kill switch readable (locked={locked})")
    except Exception as exc:
        problems.append(f"kill switch error: {exc}")

    # allowlist should deny a random host
    if allowlist.is_allowed("definitely-not-allowed.example"):
        problems.append("allowlist allowed an unknown host (should deny)")
    else:
        print("allowlist denies unknown host (good)")

    # allowlist should deny blocked hosts
    for blocked in allowlist.load().get("blocked", []):
        probe = blocked[2:] if blocked.startswith("*.") else blocked
        if allowlist.is_allowed(probe):
            problems.append(f"blocked host allowed: {blocked}")
    print("blocked-list checked")

    # credential permissions
    perms = creds.check_permissions()
    if perms:
        problems.extend(perms)
    else:
        print("credential permissions clean")

    if problems:
        print("SELFTEST FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("SELFTEST PASSED")
    return 0


def _main(argv) -> int:
    if argv and argv[0] == "--selftest":
        return selftest()
    if argv and argv[0] == "request":
        # request <host> <path> [method]
        host = argv[1]
        path = argv[2] if len(argv) > 2 else "/"
        method = argv[3] if len(argv) > 3 else "GET"
        try:
            print(json.dumps(request(host, method=method, path=path), indent=2))
            return 0
        except ProxyDenied as exc:
            print(f"DENIED: {exc}")
            return 1
    print("usage: proxy.py --selftest | proxy.py request <host> <path> [method]")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
