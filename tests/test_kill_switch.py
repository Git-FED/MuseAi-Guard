"""
test_kill_switch.py — the kill switch must FAIL CLOSED.

The single most important property of the kill switch is that the *absence* of
good state means LOCKED. If the state file is missing, corrupt, or unreadable,
the agent must not be able to act. These tests pin that behaviour down so a
future refactor can't quietly turn "unknown" into "unlocked".
"""

from __future__ import annotations

import json
import os


def test_missing_state_is_locked(kill_mod, tmp_path):
    """No state file at all => locked (fail closed)."""
    assert not os.path.exists(kill_mod.STATE)
    state = kill_mod.load()
    assert state["locked"] is True
    assert kill_mod.is_locked() is True


def test_corrupt_state_is_locked(kill_mod):
    """Garbage in the state file => locked, not a crash."""
    with open(kill_mod.STATE, "w") as fh:
        fh.write("{ this is not json ")
    state = kill_mod.load()
    assert state["locked"] is True
    assert "corrupt" in state["reason"].lower()


def test_empty_state_file_is_locked(kill_mod):
    """An empty file is also corrupt => locked."""
    open(kill_mod.STATE, "w").close()
    assert kill_mod.is_locked() is True


def test_lock_unlock_roundtrip(kill_mod):
    """Explicit lock then unlock flips the flag cleanly."""
    kill_mod.unlock()
    assert kill_mod.is_locked() is False

    kill_mod.lock("test reason")
    state = kill_mod.load()
    assert state["locked"] is True
    assert state["reason"] == "test reason"

    kill_mod.unlock()
    assert kill_mod.is_locked() is False


def test_unlock_writes_readable_state(kill_mod):
    """After unlock, the file on disk is valid JSON with locked=false."""
    kill_mod.unlock()
    with open(kill_mod.STATE) as fh:
        raw = json.load(fh)
    assert raw["locked"] is False


def test_deleting_state_relocks(kill_mod):
    """If someone deletes the state file, we fail closed again."""
    kill_mod.unlock()
    assert kill_mod.is_locked() is False

    os.remove(kill_mod.STATE)
    assert kill_mod.is_locked() is True


def test_lock_is_idempotent(kill_mod):
    """Locking twice stays locked; no error."""
    kill_mod.lock("first")
    kill_mod.lock("second")
    state = kill_mod.load()
    assert state["locked"] is True
    assert state["reason"] == "second"


def test_lock_records_timestamp(kill_mod):
    """A lock records a 'since' timestamp for the incident timeline."""
    kill_mod.lock("because")
    state = kill_mod.load()
    assert state.get("since")
