#!/usr/bin/env python3
"""
action_log.py — Tamper-evident, hash-chained, append-only action log.

Every entry records what happened, when, and who/what caused it. Each entry
contains the SHA-256 hash of the previous entry, so any edit, deletion, or
reordering breaks the chain and is detectable by verify().

This is the "black box" of Muse Guard. The agent can request that things be
logged (and the executor always logs), but the agent has no code path that
rewrites history. If the chain is broken, integrity_check.py screams.

Design goals:
  * Append-only. There is no update() or delete() function, by design.
  * Tamper-evident. verify() recomputes the whole chain and reports the first
    broken link.
  * Boring and dependency-free. Standard library only.

Log format: one JSON object per line (JSONL). Fields:
  {
    "seq":       0,                     # monotonically increasing
    "ts":        "2026-10-15T12:00:00Z",# UTC ISO-8601
    "actor":     "executor",            # agent | executor | human | system
    "action":    "post",                # short verb
    "target":    "bluesky",             # what it touched
    "result":    "ok",                  # ok | denied | error
    "detail":    {...},                 # free-form, must be JSON-serializable
    "prev_hash": "0000...0000",         # hash of the previous entry (or genesis)
    "hash":      "abcd...1234"          # SHA-256 over this entry minus "hash"
  }
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "logs")
LOG_FILE = os.path.join(LOG_DIR, "actions.jsonl")

# The "previous hash" of the very first entry. A fixed, well-known value so the
# genesis link is reproducible and verifiable.
GENESIS_HASH = "0" * 64

# A process-wide lock so concurrent writers within one process don't interleave.
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string with a Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical(entry: Dict[str, Any]) -> str:
    """
    Produce a canonical JSON string for hashing.

    We sort keys and use compact separators so the same logical entry always
    hashes to the same value regardless of dict ordering or whitespace.
    """
    return json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_entry(entry_without_hash: Dict[str, Any]) -> str:
    """SHA-256 of the canonical form of an entry (which must not include 'hash')."""
    return hashlib.sha256(_canonical(entry_without_hash).encode("utf-8")).hexdigest()


def _ensure_log_dir() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)


def _read_all_raw() -> List[Dict[str, Any]]:
    """Read every entry from the log file. Returns [] if the file is absent."""
    if not os.path.exists(LOG_FILE):
        return []
    entries: List[Dict[str, Any]] = []
    with open(LOG_FILE, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Corrupt log at line {line_no}: {exc}"
                ) from exc
    return entries


def _last_entry() -> Optional[Dict[str, Any]]:
    """Return the last entry in the log, or None if empty/missing."""
    entries = _read_all_raw()
    return entries[-1] if entries else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log(
    action: str,
    *,
    actor: str = "system",
    target: str = "",
    result: str = "ok",
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Append a new entry to the hash-chained log and return the written entry.

    Parameters
    ----------
    action : short verb describing what happened (e.g. "post", "read_file").
    actor  : who caused it — "agent" | "executor" | "human" | "system".
    target : what it touched (e.g. "bluesky", "/path/to/file").
    result : "ok" | "denied" | "error".
    detail : optional JSON-serializable dict of extra context.

    The function is thread-safe within a single process. Cross-process safety is
    provided by O_APPEND semantics (each line is written with a single write()
    call on a line-buffered handle).
    """
    _ensure_log_dir()

    with _LOCK:
        prev = _last_entry()
        prev_hash = prev["hash"] if prev else GENESIS_HASH
        seq = (prev["seq"] + 1) if prev else 0

        entry: Dict[str, Any] = {
            "seq": seq,
            "ts": _utcnow(),
            "actor": actor,
            "action": action,
            "target": target,
            "result": result,
            "detail": detail or {},
            "prev_hash": prev_hash,
        }
        entry["hash"] = _hash_entry(entry)

        line = json.dumps(entry, ensure_ascii=False)
        # Single write() of a complete line keeps concurrent appends atomic on
        # POSIX filesystems for reasonably sized lines.
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    return entry


def read_all() -> List[Dict[str, Any]]:
    """Return every entry in the log (public read accessor)."""
    return _read_all_raw()


def verify() -> Dict[str, Any]:
    """
    Recompute the entire hash chain and check it end to end.

    Returns a report:
      {
        "ok": True/False,
        "entries": N,
        "first_broken_seq": None | int,
        "reason": "..."            # present only when ok is False
      }

    A chain is valid when, for every entry:
      * entry["seq"] == expected_seq (0, 1, 2, ...)
      * entry["prev_hash"] == previous entry's "hash" (GENESIS for the first)
      * recomputed hash of the entry equals entry["hash"]
    """
    entries = _read_all_raw()
    expected_prev = GENESIS_HASH

    for i, entry in enumerate(entries):
        # 1. sequence continuity
        if entry.get("seq") != i:
            return {
                "ok": False,
                "entries": len(entries),
                "first_broken_seq": i,
                "reason": f"sequence gap: expected seq {i}, found {entry.get('seq')}",
            }

        # 2. prev_hash linkage
        if entry.get("prev_hash") != expected_prev:
            return {
                "ok": False,
                "entries": len(entries),
                "first_broken_seq": i,
                "reason": (
                    f"prev_hash mismatch at seq {i}: "
                    f"expected {expected_prev[:12]}…, found {str(entry.get('prev_hash'))[:12]}…"
                ),
            }

        # 3. content hash
        stored_hash = entry.get("hash")
        recomputed = _hash_entry({k: v for k, v in entry.items() if k != "hash"})
        if stored_hash != recomputed:
            return {
                "ok": False,
                "entries": len(entries),
                "first_broken_seq": i,
                "reason": (
                    f"content hash mismatch at seq {i}: entry was modified after write"
                ),
            }

        expected_prev = stored_hash

    return {"ok": True, "entries": len(entries), "first_broken_seq": None}


def tail(n: int = 10) -> List[Dict[str, Any]]:
    """Return the last n entries (most recent last)."""
    entries = _read_all_raw()
    return entries[-n:] if n > 0 else []


# ---------------------------------------------------------------------------
# CLI convenience: python action_log.py [verify|tail N]
# ---------------------------------------------------------------------------

def _main(argv: List[str]) -> int:
    if not argv or argv[0] == "verify":
        report = verify()
        if report["ok"]:
            print(f"OK — {report['entries']} entries, chain intact.")
            return 0
        print(f"BROKEN — {report['reason']}")
        return 1
    if argv[0] == "tail":
        n = int(argv[1]) if len(argv) > 1 else 10
        for entry in tail(n):
            print(json.dumps(entry, ensure_ascii=False))
        return 0
    print("usage: action_log.py [verify | tail N]")
    return 2


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
