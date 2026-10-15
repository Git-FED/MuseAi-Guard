"""
test_proxy.py — the egress proxy is the ONLY way out, and it defaults to DENY.

The allowlist matches on exact URL prefixes (no wildcards) and an explicit
blocked list always wins. Anything not explicitly allowed is refused. These
tests also confirm that denied requests are logged, so attempts to reach
forbidden hosts leave a trail.
"""

from __future__ import annotations

import json
import os

import pytest

ALLOWLIST = {
    "domains": [
        {"prefix": "https://bsky.social/xrpc/", "methods": ["GET", "POST"], "cred_file": "bluesky"},
        {"prefix": "https://api.github.com/", "methods": ["GET", "POST", "PATCH"], "cred_file": "github"},
    ],
    "blocked": [
        "cloudflare.com",
        "workers.dev",
        "fedos.workers.dev",
        "musefm.lol",
        "lemmy.zip",
        "*.workers.dev",
    ],
}


@pytest.fixture
def proxy(proxy_mod):
    """The proxy fixture with a known allowlist written to its temp path."""
    with open(proxy_mod.ALLOWLIST, "w") as fh:
        json.dump(ALLOWLIST, fh)
    os.makedirs(proxy_mod.CREDS, exist_ok=True)
    return proxy_mod


def test_allowed_prefix_is_permitted(proxy):
    ok, entry, reason = proxy.is_allowed("POST", "https://bsky.social/xrpc/com.atproto.repo.createRecord")
    assert ok is True
    assert entry["cred_file"] == "bluesky"


def test_unlisted_host_is_denied(proxy):
    ok, entry, reason = proxy.is_allowed("GET", "https://example.com/")
    assert ok is False
    assert "not in allowlist" in reason


def test_method_not_allowed_is_denied(proxy):
    ok, entry, reason = proxy.is_allowed("DELETE", "https://bsky.social/xrpc/x")
    assert ok is False
    assert "method" in reason.lower()


def test_blocked_domain_wins_even_if_prefix_matched(proxy):
    """A blocked host is refused regardless of any allowlist entry."""
    ok, entry, reason = proxy.is_allowed("GET", "https://musefm.lol/api")
    assert ok is False
    assert "blocked" in reason.lower()


def test_wildcard_block_matches_subdomain(proxy):
    ok, entry, reason = proxy.is_allowed("GET", "https://evil.workers.dev/x")
    assert ok is False
    assert "blocked" in reason.lower()


def test_prefix_confusion_is_denied(proxy):
    """A host that merely *contains* an allowed string is not allowed."""
    ok, entry, reason = proxy.is_allowed("GET", "https://bsky.social.evil.com/xrpc/")
    assert ok is False


def test_missing_allowlist_denies_everything(proxy_mod):
    """No allowlist file => nothing is allowed (fail closed)."""
    assert not os.path.exists(proxy_mod.ALLOWLIST)
    ok, entry, reason = proxy_mod.is_allowed("GET", "https://bsky.social/xrpc/x")
    assert ok is False


def test_forward_denied_raises_permission_error(proxy):
    with pytest.raises(PermissionError):
        proxy.forward("GET", "https://example.com/steal")


def test_denied_request_is_logged(proxy):
    with pytest.raises(PermissionError):
        proxy.forward("GET", "https://musefm.lol/api")

    assert os.path.exists(proxy.LOG)
    with open(proxy.LOG) as fh:
        entries = [json.loads(line) for line in fh if line.strip()]
    assert entries
    assert entries[-1]["allowed"] is False
    assert "musefm.lol" in entries[-1]["reason"]


def test_forward_attaches_credential_headers(proxy, monkeypatch):
    """When a cred file exists, the proxy adds its headers to the request."""
    cred = {"headers": {"Authorization": "Bearer SECRET-TOKEN"}}
    with open(os.path.join(proxy.CREDS, "bluesky.json"), "w") as fh:
        json.dump(cred, fh)

    captured = {}

    class FakeResp:
        status = 200

        def read(self):
            return b"ok"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        return FakeResp()

    monkeypatch.setattr(proxy.urllib.request, "urlopen", fake_urlopen)

    status, body = proxy.forward(
        "POST", "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        payload={"a": 1}, cred_name="bluesky",
    )
    assert status == 200
    assert captured["headers"].get("authorization") == "Bearer SECRET-TOKEN"


def test_forward_missing_credential_raises(proxy):
    with pytest.raises(FileNotFoundError):
        proxy.forward("POST", "https://bsky.social/xrpc/x", cred_name="nope")
