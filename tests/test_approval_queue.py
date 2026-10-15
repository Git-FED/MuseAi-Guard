"""
test_approval_queue.py — the approval queue is the gate between "wants to" and
"did".

Nothing executes without an explicit human approval, and the approved list is
hash-chained so a tampered or reordered history is detectable. These tests
exercise both the happy path (propose -> approve/deny) and the tamper-evidence
guarantees.
"""

from __future__ import annotations

import json
import os


def _read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def test_propose_creates_pending(queue_mod):
    """A proposal lands in the pending list and is not executed."""
    pid = queue_mod.propose("post", {"url": "https://bsky.social/xrpc/x"}, "say hi")
    assert pid

    items = queue_mod.pending()
    assert len(items) == 1
    assert items[0]["id"] == pid
    assert items[0]["status"] == "pending"
    assert items[0]["action_type"] == "post"


def test_propose_returns_unique_ids(queue_mod):
    """Two proposals get distinct IDs."""
    a = queue_mod.propose("post", {}, "one")
    b = queue_mod.propose("post", {}, "two")
    assert a != b
    assert len(queue_mod.pending()) == 2


def test_approve_moves_to_approved(queue_mod):
    """Approving removes it from pending and adds it to approved."""
    pid = queue_mod.propose("post", {"url": "x"}, "go")
    queue_mod.approve(pid, note="looks good")

    assert queue_mod.pending() == []
    approved = _read_lines(queue_mod.APPROVED)
    assert len(approved) == 1
    assert approved[0]["id"] == pid
    assert approved[0]["status"] == "approved"
    assert approved[0]["note"] == "looks good"


def test_deny_moves_to_denied(queue_mod):
    """Denying removes it from pending and records a denial."""
    pid = queue_mod.propose("send_email", {"to": "a@b.com"}, "spam?")
    queue_mod.deny(pid, note="no")

    assert queue_mod.pending() == []
    denied = _read_lines(queue_mod.DENIED)
    assert len(denied) == 1
    assert denied[0]["status"] == "denied"
    assert _read_lines(queue_mod.APPROVED) == []


def test_approve_unknown_id_raises(queue_mod):
    """Approving something that was never proposed is an error."""
    try:
        queue_mod.approve("does-not-exist")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown intent")


def test_cannot_approve_twice(queue_mod):
    """Once approved, the intent is no longer pending, so a second approve fails."""
    pid = queue_mod.propose("post", {}, "once")
    queue_mod.approve(pid)
    try:
        queue_mod.approve(pid)
    except ValueError:
        return
    raise AssertionError("expected ValueError on double-approve")


def test_approved_unaltered_returns_approved(queue_mod):
    """A clean chain yields exactly the approved intents."""
    pid = queue_mod.propose("post", {"url": "x"}, "go")
    queue_mod.approve(pid)
    clean = queue_mod.approved_unaltered()
    assert len(clean) == 1
    assert clean[0]["id"] == pid


def test_approved_chain_is_linked(queue_mod):
    """Each approved entry links to the previous one via prev_hash."""
    for i in range(3):
        pid = queue_mod.propose("post", {"n": i}, f"go {i}")
        queue_mod.approve(pid)

    approved = _read_lines(queue_mod.APPROVED)
    assert approved[0]["prev_hash"] == "genesis"
    for prev, cur in zip(approved, approved[1:]):
        assert cur["prev_hash"] == prev["hash"]


def test_tampering_payload_breaks_chain(queue_mod):
    """Editing an approved entry's payload invalidates it."""
    pid = queue_mod.propose("post", {"url": "safe"}, "go")
    queue_mod.approve(pid)

    # Rewrite the payload on disk, leaving the stored hash stale.
    approved = _read_lines(queue_mod.APPROVED)
    approved[0]["payload"] = {"url": "https://musefm.lol/evil"}
    with open(queue_mod.APPROVED, "w") as fh:
        for entry in approved:
            fh.write(json.dumps(entry) + "\n")

    assert queue_mod.approved_unaltered() == []


def test_deleting_an_approved_entry_breaks_chain(queue_mod):
    """Removing a middle entry breaks the linkage and halts verification."""
    ids = []
    for i in range(3):
        pid = queue_mod.propose("post", {"n": i}, f"go {i}")
        queue_mod.approve(pid)
        ids.append(pid)

    approved = _read_lines(queue_mod.APPROVED)
    del approved[1]  # drop the middle entry
    with open(queue_mod.APPROVED, "w") as fh:
        for entry in approved:
            fh.write(json.dumps(entry) + "\n")

    clean = queue_mod.approved_unaltered()
    # Only the first entry survives verification.
    assert len(clean) == 1
    assert clean[0]["id"] == ids[0]


def test_reordering_breaks_chain(queue_mod):
    """Swapping two approved entries is detected."""
    for i in range(2):
        pid = queue_mod.propose("post", {"n": i}, f"go {i}")
        queue_mod.approve(pid)

    approved = _read_lines(queue_mod.APPROVED)
    approved.reverse()
    with open(queue_mod.APPROVED, "w") as fh:
        for entry in approved:
            fh.write(json.dumps(entry) + "\n")

    assert queue_mod.approved_unaltered() == []
