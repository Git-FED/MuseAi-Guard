#!/usr/bin/env python3
"""
Egress proxy. The ONLY way out.

- Agent asks the proxy to make a call. Proxy adds credentials.
- Proxy checks the allowlist (exact prefix, no wildcards).
- Proxy logs everything (allowed or denied).
- The agent never sees the credentials.
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
ALLOWLIST = os.path.join(BASE, "allowlist.json")
CREDS = os.path.join(BASE, "credentials")
LOG = os.path.join(BASE, "request_log.jsonl")


def _now():
    return datetime.now(timezone.utc).isoformat()


def load_allowlist():
    if not os.path.exists(ALLOWLIST):
        return {"domains": [], "blocked": []}
    with open(ALLOWLIST) as f:
        return json.load(f)


def is_allowed(method, url):
    """Returns (ok, entry, reason)."""
    method = method.upper()
    data = load_allowlist()
    host = urlparse(url).hostname or ""

    # Explicit block wins
    for block in data.get("blocked", []):
        if block.startswith("*."):
            if host.endswith(block[1:]):
                return False, None, f"blocked host: {host}"
        elif block == host or block in url:
            return False, None, f"blocked domain: {block}"

    for entry in data.get("domains", []):
        prefix = entry.get("prefix", "")
        if url.startswith(prefix):
            if method in entry.get("methods", []):
                return True, entry, "ok"
            return False, entry, f"method {method} not allowed for {prefix}"

    return False, None, "not in allowlist"


def _load_cred(name):
    if not name.endswith(".json"):
        name += ".json"
    path = os.path.join(CREDS, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"No credential: {name}")
    with open(path) as f:
        return json.load(f)


def _log(entry):
    with open(LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def forward(method, url, payload=None, headers=None, cred_name=None, timeout=30):
    """
    Agent calls this. Proxy decides.
    Returns (status_code, body_bytes) or raises PermissionError.
    """
    allowed, entry, reason = is_allowed(method, url)

    log_entry = {
        "ts": _now(),
        "method": method,
        "url": url,
        "allowed": allowed,
        "reason": reason,
        "cred": cred_name,
    }

    if not allowed:
        _log(log_entry)
        raise PermissionError(f"Blocked: {method} {url} — {reason}")

    req_headers = dict(headers or {})
    if cred_name:
        try:
            cred = _load_cred(cred_name)
        except FileNotFoundError as e:
            _log({**log_entry, "error": str(e)})
            raise
        for k, v in cred.get("headers", {}).items():
            req_headers[k] = v

    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        req_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            log_entry["status"] = resp.status
            _log(log_entry)
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read()
        log_entry["status"] = e.code
        _log(log_entry)
        return e.code, body
    except Exception as e:
        log_entry["error"] = str(e)
        _log(log_entry)
        raise


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: egress_proxy.py <METHOD> <URL> [cred_name]")
        sys.exit(1)
    method, url = sys.argv[1], sys.argv[2]
    cred = sys.argv[3] if len(sys.argv) > 3 else None
    try:
        status, body = forward(method, url, cred_name=cred)
        print(status, body[:500])
    except PermissionError as e:
        print(f"DENIED: {e}")
        sys.exit(2)
