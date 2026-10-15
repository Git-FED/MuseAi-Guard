#!/usr/bin/env python3
"""
integrity_check.py — Verify the tamper-evident action log (and friends).

This is the tool you run when you are worried. It:
  1. Verifies the SHA-256 hash chain of logger/logs/actions.jsonl.
  2. Reports the size and last-write time of the log.
  3. Optionally checks the approval queue chain too (if importable).

Exit codes:
  0 = everything intact
  1 = something is broken (details printed)
  2 = usage error

Run it from cron, from CI, or by hand. If it ever returns 1, treat it as an
incident: stop the agent, preserve the log, and investigate.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(HERE, "logs", "actions.jsonl")

# Make sibling packages importable when run directly.
PROJECT_ROOT = os.path.dirname(HERE)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _fmt_ts(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_action_log() -> Dict[str, Any]:
    """Verify the action log chain and gather file stats."""
    import action_log  # local module (same directory)

    report: Dict[str, Any] = {"name": "action_log", "file": LOG_FILE}

    if not os.path.exists(LOG_FILE):
        report.update({"ok": True, "note": "no log yet (empty system)", "entries": 0})
        return report

    stat = os.stat(LOG_FILE)
    report["bytes"] = stat.st_size
    report["last_write"] = _fmt_ts(stat.st_mtime)

    verdict = action_log.verify()
    report.update(verdict)
    return report


def check_approval_queue() -> Dict[str, Any]:
    """Verify the approval queue chain, if it is available."""
    report: Dict[str, Any] = {"name": "approval_queue"}
    try:
        from guardrails.approval_queue import queue as q  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        report.update({"ok": None, "note": f"not checked: {exc}"})
        return report

    try:
        verdict = q.verify_chain()
        report.update(verdict)
    except Exception as exc:  # pragma: no cover
        report.update({"ok": False, "reason": f"verification error: {exc}"})
    return report


def run_all() -> List[Dict[str, Any]]:
    return [check_action_log(), check_approval_queue()]


def _main(argv: List[str]) -> int:
    as_json = "--json" in argv
    reports = run_all()

    if as_json:
        print(json.dumps(reports, indent=2))
    else:
        print("Muse Guard — integrity check")
        print("=" * 40)
        for r in reports:
            status = {True: "OK", False: "BROKEN", None: "SKIPPED"}.get(r.get("ok"), "?")
            print(f"[{status:7}] {r['name']}")
            if r.get("ok") is False:
                print(f"          reason: {r.get('reason', 'unknown')}")
            if r.get("note"):
                print(f"          note:   {r['note']}")
            if r.get("entries") is not None:
                print(f"          entries: {r.get('entries')}  last_write: {r.get('last_write', '-')}")

    # Failure if any check that ran came back False.
    if any(r.get("ok") is False for r in reports):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
