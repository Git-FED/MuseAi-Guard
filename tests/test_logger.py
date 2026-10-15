"""
test_logger.py — the action log is the black box, and it must be tamper-evident.

Every entry is chained to the previous one by a SHA-256 hash. These tests prove
that a clean log verifies, and that editing, deleting, or reordering entries is
detected by verify().
"""

from __future__ import annotations

import json
import os


def test_empty_log_verifies(log_mod):
    report = log_mod.verify()
    assert report["ok"] is True
    assert report["entries"] == 0


def test_log_appends_and_sequences(log_mod):
    log_mod.log("boot", actor="system", target="vm", result="ok")
    log_mod.log("post", actor="executor", target="bluesky", result="ok")
    log_mod.log("send_email", actor="executor", target="friend@example.com", result="denied")

    entries = log_mod.read_all()
    assert [e["seq"] for e in entries] == [0, 1, 2]
    assert entries[0]["prev_hash"] == log_mod.GENESIS_HASH


def test_clean_chain_verifies(log_mod):
    for i in range(5):
        log_mod.log("tick", actor="system", detail={"i": i})
    report = log_mod.verify()
    assert report["ok"] is True
    assert report["entries"] == 5


def test_entries_link_to_previous_hash(log_mod):
    log_mod.log("a")
    log_mod.log("b")
    entries = log_mod.read_all()
    assert entries[1]["prev_hash"] == entries[0]["hash"]


def test_tail_returns_most_recent(log_mod):
    for i in range(5):
        log_mod.log("tick", detail={"i": i})
    last_two = log_mod.tail(2)
    assert [e["detail"]["i"] for e in last_two] == [3, 4]


def test_editing_an_entry_breaks_verify(log_mod):
    log_mod.log("post", actor="executor", target="bluesky")
    log_mod.log("post", actor="executor", target="mastodon")

    # Tamper: rewrite the first entry's target but keep its stale hash.
    entries = log_mod.read_all()
    entries[0]["target"] = "musefm.lol"
    with open(log_mod.LOG_FILE, "w") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")

    report = log_mod.verify()
    assert report["ok"] is False
    assert report["first_broken_seq"] == 0


def test_deleting_an_entry_breaks_verify(log_mod):
    for i in range(3):
        log_mod.log("tick", detail={"i": i})

    entries = log_mod.read_all()
    del entries[1]
    with open(log_mod.LOG_FILE, "w") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")

    report = log_mod.verify()
    assert report["ok"] is False


def test_reordering_entries_breaks_verify(log_mod):
    for i in range(3):
        log_mod.log("tick", detail={"i": i})

    entries = log_mod.read_all()
    entries.reverse()
    with open(log_mod.LOG_FILE, "w") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")

    report = log_mod.verify()
    assert report["ok"] is False


def test_appending_after_tamper_still_flags(log_mod):
    """Even if someone keeps appending, the historical break is still caught."""
    log_mod.log("a")
    entries = log_mod.read_all()
    entries[0]["actor"] = "human"  # tamper
    with open(log_mod.LOG_FILE, "w") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")

    log_mod.log("b")  # a legitimate-looking new entry
    report = log_mod.verify()
    assert report["ok"] is False
    assert report["first_broken_seq"] == 0


def test_log_creates_directory(log_mod):
    log_mod.log("boot")
    assert os.path.isdir(log_mod.LOG_DIR)
    assert os.path.exists(log_mod.LOG_FILE)
