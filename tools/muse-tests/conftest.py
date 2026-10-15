"""
conftest.py — shared fixtures for the Muse Guard guardrail tests.

These tests prove the cage holds. They are the evidence that the controls do
what the docs claim: fail-closed kill switch, tamper-evident queue, default-deny
allowlist, credential isolation.

Each test runs against isolated temp files via environment overrides, so the
suite never touches a real install.
"""

from __future__ import annotations

import os
import sys

import pytest

# Make the sibling tool packages importable.
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)  # .../tools
for pkg in ("muse-guard", "muse-proxy"):
    path = os.path.join(TOOLS, pkg)
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Point every stateful component at temp files for one test."""
    kill_state = tmp_path / "kill_state.json"
    queue_file = tmp_path / "queue.jsonl"
    creds_dir = tmp_path / "credentials"
    allowlist_file = tmp_path / "allowlist.json"

    monkeypatch.setenv("MUSE_GUARD_KILL_STATE", str(kill_state))
    monkeypatch.setenv("MUSE_GUARD_QUEUE", str(queue_file))
    monkeypatch.setenv("MUSE_PROXY_CREDS", str(creds_dir))
    monkeypatch.setenv("MUSE_PROXY_ALLOWLIST", str(allowlist_file))

    return {
        "kill_state": kill_state,
        "queue_file": queue_file,
        "creds_dir": creds_dir,
        "allowlist_file": allowlist_file,
    }


@pytest.fixture
def unlocked(isolated_env):
    """A fresh, unlocked kill switch."""
    from muse_guard import kill

    kill.unlock("test")
    return kill
