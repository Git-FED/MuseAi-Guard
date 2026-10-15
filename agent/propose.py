#!/usr/bin/env python3
"""
propose.py — The agent's only way to ask for something to happen.

The agent cannot post, send, spend, or write anything outside its workspace
directly. Instead it calls propose(). That writes a request into the approval
queue and stops. A human then approves or denies. Only an approved, unaltered
request is ever executed — by the *executor*, a separate non-AI process.

This module is the narrow waist of the whole system. Everything the agent wants
to do flows through here, and everything that flows through here is queued,
hashed, and logged.

Usage (as a library):
    from agent import propose
    pid = propose.request("post", {"platform": "bluesky", "text": "hello"},
                          reason="daily update")
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _import_queue():
    from guardrails.approval_queue import queue as q  # type: ignore
    return q


def _import_kill():
    from guardrails.kill_switch import kill_switch as ks  # type: ignore
    return ks


def request(
    action: str,
    payload: Dict[str, Any],
    *,
    reason: str = "",
) -> Optional[str]:
    """
    Propose an action for human approval.

    Returns the proposal id on success, or None if the kill switch is engaged
    (in which case nothing is queued — fail closed).

    Parameters
    ----------
    action  : the action type the executor understands ("post", "send_email",
              "read_file", "write_file").
    payload : action-specific arguments.
    reason  : short human-readable justification (shown to the approver).
    """
    kill = _import_kill()
    if kill.is_locked():
        # Fail closed: if we're locked, do not even queue.
        return None

    q = _import_queue()
    proposal_id = q.propose(
        action=action,
        payload=payload,
        proposer="agent",
        reason=reason,
    )
    return proposal_id


def status(proposal_id: str) -> Optional[Dict[str, Any]]:
    """Look up the status of a previously proposed action."""
    q = _import_queue()
    return q.get(proposal_id)


def pending() -> list:
    """List all proposals still awaiting a human decision."""
    q = _import_queue()
    return q.pending()


def _main(argv) -> int:
    """Tiny CLI so a human can see what the agent is asking for."""
    cmd = argv[0] if argv else "pending"
    if cmd == "pending":
        rows = pending()
        if not rows:
            print("No pending proposals.")
            return 0
        for row in rows:
            print(f"[{row['id']}] {row['action']} — {row.get('reason', '')}")
        return 0
    if cmd == "status" and len(argv) > 1:
        import json

        print(json.dumps(status(argv[1]), indent=2))
        return 0
    print("usage: propose.py [pending | status <id>]")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
