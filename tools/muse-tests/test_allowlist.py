"""
test_allowlist.py — prove the allowlist is exact-host and default-deny.

The theme: only named hosts pass, blocked patterns always fail, and the absence
of an allowlist means nothing is allowed.
"""

from __future__ import annotations

import json

from muse_proxy import allowlist


def _write_allowlist(path, domains, blocked=None):
    path.write_text(json.dumps({
        "domains": {d: {"credential": "x", "scheme": "https"} for d in domains},
        "blocked": blocked or [],
    }))


def test_default_deny_when_no_file(isolated_env):
    assert allowlist.is_allowed("anything.example") is False


def test_exact_host_allowed(isolated_env):
    _write_allowlist(isolated_env["allowlist_file"], ["bsky.social"])
    assert allowlist.is_allowed("bsky.social") is True


def test_subdomain_of_allowed_is_allowed(isolated_env):
    _write_allowlist(isolated_env["allowlist_file"], ["bsky.social"])
    assert allowlist.is_allowed("api.bsky.social") is True


def test_unrelated_host_denied(isolated_env):
    _write_allowlist(isolated_env["allowlist_file"], ["bsky.social"])
    assert allowlist.is_allowed("evil.example") is False


def test_suffix_confusion_denied(isolated_env):
    """notbsky.social must not match bsky.social."""
    _write_allowlist(isolated_env["allowlist_file"], ["bsky.social"])
    assert allowlist.is_allowed("notbsky.social") is False


def test_blocked_pattern_wins(isolated_env):
    _write_allowlist(
        isolated_env["allowlist_file"],
        ["workers.dev"],          # even if someone allowlists it...
        ["*.workers.dev"],        # ...the block list wins
    )
    assert allowlist.is_allowed("foo.workers.dev") is False
    assert allowlist.is_allowed("workers.dev") is False


def test_blocked_exact(isolated_env):
    _write_allowlist(isolated_env["allowlist_file"], ["cloudflare.com"], ["cloudflare.com"])
    assert allowlist.is_allowed("cloudflare.com") is False


def test_corrupt_allowlist_is_deny_all(isolated_env):
    isolated_env["allowlist_file"].write_text("{ not json")
    assert allowlist.is_allowed("bsky.social") is False


def test_credential_lookup(isolated_env):
    _write_allowlist(isolated_env["allowlist_file"], ["bsky.social"])
    assert allowlist.credential_for("bsky.social") == "x"
    assert allowlist.credential_for("api.bsky.social") == "x"
    assert allowlist.credential_for("evil.example") is None
