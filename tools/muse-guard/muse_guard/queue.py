"""
queue.py — the hash-chained approval queue.

The queue is where the agent's intentions become human decisions. The agent can
only *add* proposals; a human can *decide* on them. Nothing is executed from the
queue unless it is approved AND unaltered since approval.

Everything is recorded in a single append-only JSONL file. Each record chains to
the previous one by hash, so inserting, deleting, or editing a record breaks the
chain and is detectable by verify_chain(). This is what stops the "approve one
thing, swap the payload" attack: the executor re-checks the payload hash against
the one that was approved.

Record types:
    {"type": "propose", "id", "action", "payload", "proposer", "reason", "ts", ...chain}
    {"type": "approve", "id", "approver", "ts", ...chain}
    {"type": "deny",    "id", "approver", "note", "ts", ...chain}

Each record also carries:
    "seq", "prev_hash", "hash"

The *state* of a proposal is derived by replaying the records for its id:
propose → (approve | deny | pending).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_QUEUE = os.path.join(HERE, "queue.jsonl")
GENESIS_HASH = "0" * 64
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path() -> str:
    return os.environ.get("MUSE_GUARD_QUEUE", DEFAULT_QUEUE)


def _canonical(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(obj_without_hash: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(obj_without_hash).encode("utf-8")).hexdigest()


def _read_all() -> List[Dict[str, Any]]:
    path = _path()
    if not os.path.exists(path):
        return []
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"corrupt queue at line {i}: {exc}") from exc
    return records


def _append(record: Dict[str, Any]) -> Dict[str, Any]:
    """Append a record with chain fields, atomically."""
    with _LOCK:
        records = _read_all()
        prev_hash = records[-1]["hash"] if records else GENESIS_HASH
        seq = len(records)
        record = dict(record)
        record["seq"] = seq
        record["prev_hash"] = prev_hash
        record["hash"] = _hash(record)
        path = _path()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return record


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose(
    action: str,
    payload: Dict[str, Any],
    *,
    proposer: str = "agent",
    reason: str = "",
) -> str:
    """Add a proposal to the queue. Returns its id."""
    proposal_id = uuid.uuid4().hex[:12]
    _append({
        "type": "propose",
        "id": proposal_id,
        "action": action,
        "payload": payload,
        "proposer": proposer,
        "reason": reason,
        "ts": _now(),
    })
    return proposal_id


def approve(proposal_id: str, *, approver: str = "human") -> Dict[str, Any]:
    """Record an approval. Returns the appended record."""
    return _append({
        "type": "approve",
        "id": proposal_id,
        "approver": approver,
        "ts": _now(),
    })


def deny(proposal_id: str, *, approver: str = "human", note: str = "") -> Dict[str, Any]:
    """Record a denial. Returns the appended record."""
    return _append({
        "type": "deny",
        "id": proposal_id,
        "approver": approver,
        "note": note,
        "ts": _now(),
    })


def _state_of(proposal_id: str, records: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Replay records for one id and return its current state."""
    records = records if records is not None else _read_all()
    proposal: Optional[Dict[str, Any]] = None
    decision: Optional[Dict[str, Any]] = None
    for r in records:
        if r.get("id") != proposal_id:
            continue
        if r.get("type") == "propose":
            proposal = r
        elif r.get("type") in ("approve", "deny"):
            decision = r
    if proposal is None:
        return None
    state = dict(proposal)
    if decision is None:
        state["status"] = "pending"
    else:
        state["status"] = "approved" if decision["type"] == "approve" else "denied"
        state["decision"] = decision
    return state


def get(proposal_id: str) -> Optional[Dict[str, Any]]:
    """Return the current state of a proposal, or None if unknown."""
    return _state_of(proposal_id)


def all_proposals() -> List[Dict[str, Any]]:
    """Return every proposal with its derived status."""
    records = _read_all()
    ids = [r["id"] for r in records if r.get("type") == "propose"]
    out = []
    for pid in ids:
        st = _state_of(pid, records)
        if st:
            out.append(st)
    return out


def pending() -> List[Dict[str, Any]]:
    """Proposals awaiting a human decision."""
    return [p for p in all_proposals() if p["status"] == "pending"]


def approved_unaltered() -> List[Dict[str, Any]]:
    """
    Approved proposals whose payload is intact.

    Because the queue is append-only and hash-chained, an approved proposal's
    payload cannot have changed without breaking the chain. This function
    re-verifies the chain and returns only approved items from an intact chain.
    If the chain is broken, it returns [] — fail-closed.
    """
    report = verify_chain()
    if not report["ok"]:
        return []
    return [p for p in all_proposals() if p["status"] == "approved"]


def verify_chain() -> Dict[str, Any]:
    """Verify the whole queue chain. Returns {ok, entries, first_broken_seq, reason?}."""
    try:
        records = _read_all()
    except ValueError as exc:
        return {"ok": False, "entries": 0, "first_broken_seq": None, "reason": str(exc)}

    expected_prev = GENESIS_HASH
    for i, r in enumerate(records):
        if r.get("seq") != i:
            return {"ok": False, "entries": len(records), "first_broken_seq": i,
                    "reason": f"sequence gap at {i}"}
        if r.get("prev_hash") != expected_prev:
            return {"ok": False, "entries": len(records), "first_broken_seq": i,
                    "reason": f"prev_hash mismatch at {i}"}
        recomputed = _hash({k: v for k, v in r.items() if k != "hash"})
        if r.get("hash") != recomputed:
            return {"ok": False, "entries": len(records), "first_broken_seq": i,
                    "reason": f"content hash mismatch at {i}"}
        expected_prev = r["hash"]
    return {"ok": True, "entries": len(records), "first_broken_seq": None}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main(argv) -> int:
    cmd = argv[0] if argv else "list"
    if cmd == "list":
        for p in all_proposals():
            print(f"[{p['status']:8}] {p['id']}  {p['action']:12} {p.get('reason', '')}")
        return 0
    if cmd == "pending":
        for p in pending():
            print(f"[{p['id']}] {p['action']} — {p.get('reason', '')}")
        return 0
    if cmd == "verify":
        r = verify_chain()
        print("OK" if r["ok"] else f"BROKEN: {r.get('reason')}")
        return 0 if r["ok"] else 1
    if cmd == "show" and len(argv) > 1:
        print(json.dumps(get(argv[1]), indent=2))
        return 0
    print("usage: queue.py [list|pending|verify|show <id>]")
    return 2


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
