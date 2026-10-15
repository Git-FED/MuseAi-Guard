"""
test_proxy.py — prove the proxy refuses when it should.

The theme: the proxy is the door, and the door is locked by default. We test the
refusal paths (which never touch the network) rather than real requests.
"""

from __future__ import annotations

import json

import pytest

from muse_proxy import allowlist, proxy


def _write_allowlist(path, domains, blocked=None):
    path.write_text(json.dumps({
        "domains": {d: {"credential": "x", "scheme": "https"} for d in domains},
        "blocked": blocked or [],
    }))


def test_kill_switch_blocks_request(isolated_env):
    """If the kill switch is engaged, the proxy refuses — fail-closed."""
    from muse_guard import kill

    kill.lock("test")
    with pytest.raises(proxy.ProxyDenied):
        proxy.request("bsky.social", path="/")


def test_unallowlisted_host_denied(isolated_env):
    from muse_guard import kill

    kill.unlock("test")
    _write_allowlist(isolated_env["allowlist_file"], ["bsky.social"])
    with pytest.raises(proxy.ProxyDenied):
        proxy.request("evil.example", path="/")


def test_blocked_host_denied(isolated_env):
    from muse_guard import kill

    kill.unlock("test")
    _write_allowlist(isolated_env["allowlist_file"], ["foo.workers.dev"], ["*.workers.dev"])
    with pytest.raises(proxy.ProxyDenied):
        proxy.request("foo.workers.dev", path="/")


def test_missing_kill_switch_fails_closed(isolated_env, monkeypatch):
    """
    If muse_guard is unimportable, the proxy must fail closed.

    We simulate by making the import raise, then confirm a request is denied.
    """
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "muse_guard" or name.startswith("muse_guard."):
            raise ImportError("simulated missing kill switch")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(proxy.ProxyDenied):
        proxy.request("bsky.social", path="/")


def test_selftest_passes_on_clean_config(isolated_env, monkeypatch):
    from muse_guard import kill

    kill.unlock("test")
    _write_allowlist(isolated_env["allowlist_file"], ["bsky.social"], ["*.workers.dev"])
    # selftest reads the real allowlist path via env; ensure it is set (it is,
    # via the fixture). It should pass.
    assert proxy.selftest() == 0
