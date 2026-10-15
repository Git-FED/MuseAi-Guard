#!/usr/bin/env python3
"""
Approval queue. Agent writes intended actions here.
Nothing executes until YOU approve.

- Agent side: writes to pending.jsonl
- You side: reads pending, writes to approved.jsonl or denied.jsonl
- Executor: reads approved.jsonl, runs the action, logs result.

Each entry is hash-chained for tamper evidence.
"""

import json
import os
import uuid
import hashlib
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
PENDING = os.path.join(BASE, "pending.jsonl")
APPROVED = os.path.join(BASE, "approved.jsonl")
DENIED = os.path.join(BASE, "denied.jsonl")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _last_hash(path):
    if not os.path.exists(path):
        return "genesis"
    last = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    if not last:
        return "genesis"
    return json.loads(last).get("hash", "genesis")


def _append(path, entry):
    # Work on a copy and drop any pre-existing chain fields. An intent that was
    # first written to pending.jsonl already carries its own prev_hash/hash; if
    # we hashed it with those still present the stored hash would never match a
    # clean recomputation and the chain would look broken.
    entry = dict(entry)
    entry.pop("hash", None)
    entry["prev_hash"] = _last_hash(path)
    entry["hash"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True).encode()
    ).hexdigest()
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def _decided_ids():
    """IDs that already have a decision recorded in approved/denied."""
    decided = set()
    for path in (APPROVED, DENIED):
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    decided.add(json.loads(line).get("id"))
                except json.JSONDecodeError:
                    continue
    return decided


def propose(action_type, payload, reason):
    """Agent calls this. Returns intent ID. Does NOT execute."""
    intent = {
        "id": str(uuid.uuid4()),
        "ts": _now(),
        "action_type": action_type,
        "payload": payload,
        "reason": reason,
        "status": "pending",
    }
    _append(PENDING, intent)
    return intent["id"]


def _find_pending(intent_id):
    if not os.path.exists(PENDING):
        return None
    decided = _decided_ids()
    with open(PENDING) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("id") == intent_id and entry.get("status") == "pending":
                # Already approved or denied => not pending anymore. This also
                # makes a double-approve a hard error rather than a silent no-op.
                if intent_id in decided:
                    return None
                return entry
    return None


def approve(intent_id, note=""):
    """You call this. Moves intent to approved."""
    intent = _find_pending(intent_id)
    if not intent:
        raise ValueError(f"No pending intent: {intent_id}")
    intent["status"] = "approved"
    intent["approved_at"] = _now()
    intent["note"] = note
    _append(APPROVED, intent)
    return intent


def deny(intent_id, note=""):
    """You call this. Moves intent to denied."""
    intent = _find_pending(intent_id)
    if not intent:
        raise ValueError(f"No pending intent: {intent_id}")
    intent["status"] = "denied"
    intent["denied_at"] = _now()
    intent["note"] = note
    _append(DENIED, intent)
    return intent


def pending():
    if not os.path.exists(PENDING):
        return []
    decided = _decided_ids()
    items = []
    with open(PENDING) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("status") == "pending" and entry.get("id") not in decided:
                items.append(entry)
    return items


def approved_unaltered():
    """Return approved items whose chain verifies. Stops at first break."""
    if not os.path.exists(APPROVED):
        return []
    items = []
    prev = "genesis"
    with open(APPROVED) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("prev_hash") != prev:
                break
            check = {k: v for k, v in entry.items() if k != "hash"}
            expected = hashlib.sha256(
                json.dumps(check, sort_keys=True).encode()
            ).hexdigest()
            if entry.get("hash") != expected:
                break
            prev = entry["hash"]
            items.append(entry)
    return items
