"""
test_kill.py — prove the kill switch is fail-closed.

The kill switch is the most important control, so it gets the harshest tests.
The theme: any ambiguity resolves to LOCKED.
"""

from __future__ import annotations

import json
import os

from muse_guard import kill


def test_missing_state_is_locked(isolated_env):
    """No state file at all must mean LOCKED (fail-closed)."""
    assert not isolated_env["kill_state"].exists()
    assert kill.is_locked() is True


def test_corrupt_state_is_locked(isolated_env):
    """Garbage in the state file must mean LOCKED."""
    isolated_env["kill_state"].write_text("{ this is not json")
    assert kill.is_locked() is True


def test_malformed_state_is_locked(isolated_env):
    """Valid JSON that lacks 'locked' must mean LOCKED."""
    isolated_env["kill_state"].write_text(json.dumps({"foo": "bar"}))
    assert kill.is_locked() is True


def test_lock_and_unlock_roundtrip(isolated_env):
    kill.unlock("test")
    assert kill.is_locked() is False
    kill.lock("because")
    assert kill.is_locked() is True
    s = kill.status()
    assert s["locked"] is True
    assert s["reason"] == "because"


def test_delete_state_re_locks(isolated_env):
    """Deleting the state file must NOT disable the switch."""
    kill.unlock("test")
    assert kill.is_locked() is False
    os.remove(isolated_env["kill_state"])
    assert kill.is_locked() is True  # back to fail-closed


def test_lock_is_idempotent(isolated_env):
    kill.lock("first")
    kill.lock("second")
    assert kill.is_locked() is True
    assert kill.status()["reason"] == "second"
