"""
test_queue.py — prove the approval queue is tamper-evident and correct.

The theme: proposals flow propose → approve/deny, and any edit to history is
detected. The "approve one thing, swap the payload" attack must fail.
"""

from __future__ import annotations

import json

from muse_guard import queue


def test_propose_then_pending(isolated_env):
    pid = queue.propose("post", {"text": "hi"}, proposer="agent", reason="test")
    pend = queue.pending()
    assert len(pend) == 1
    assert pend[0]["id"] == pid
    assert pend[0]["status"] == "pending"


def test_approve_changes_status(isolated_env):
    pid = queue.propose("post", {"text": "hi"})
    queue.approve(pid, approver="human")
    st = queue.get(pid)
    assert st["status"] == "approved"


def test_deny_changes_status(isolated_env):
    pid = queue.propose("post", {"text": "hi"})
    queue.deny(pid, approver="human", note="no")
    st = queue.get(pid)
    assert st["status"] == "denied"


def test_chain_intact_after_operations(isolated_env):
    pid = queue.propose("post", {"text": "hi"})
    queue.approve(pid)
    assert queue.verify_chain()["ok"] is True


def test_tamper_payload_breaks_chain(isolated_env):
    """Editing a proposal's payload after the fact must break the chain."""
    pid = queue.propose("post", {"text": "benign"})
    queue.approve(pid)

    # Attacker edits the payload on disk to something malicious.
    path = isolated_env["queue_file"]
    lines = path.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["payload"] = {"text": "malicious"}
    lines[0] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n")

    report = queue.verify_chain()
    assert report["ok"] is False
    assert report["first_broken_seq"] == 0


def test_tamper_breaks_approved_unaltered(isolated_env):
    """A broken chain must yield no executable items (fail-closed)."""
    pid = queue.propose("post", {"text": "benign"})
    queue.approve(pid)

    path = isolated_env["queue_file"]
    lines = path.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["payload"] = {"text": "malicious"}
    lines[0] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n")

    assert queue.approved_unaltered() == []


def test_deleting_a_record_breaks_chain(isolated_env):
    """Removing a line must be detected as a sequence gap."""
    p1 = queue.propose("post", {"text": "one"})
    queue.propose("post", {"text": "two"})
    queue.approve(p1)

    path = isolated_env["queue_file"]
    lines = path.read_text().splitlines()
    # Delete the middle record.
    del lines[1]
    path.write_text("\n".join(lines) + "\n")

    report = queue.verify_chain()
    assert report["ok"] is False


def test_approved_unaltered_returns_only_approved(isolated_env):
    p1 = queue.propose("post", {"text": "one"})
    p2 = queue.propose("post", {"text": "two"})
    queue.approve(p1)
    queue.deny(p2, note="no")
    safe = queue.approved_unaltered()
    ids = {p["id"] for p in safe}
    assert ids == {p1}
