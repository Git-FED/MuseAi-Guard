#!/usr/bin/env python3
"""
request_action.py — The agent's tool for asking a human to approve an action.

This is the function-call surface the agent is given. It does not perform the
action; it only files a request. The name is deliberately "request_action", not
"do_action", because the agent must never believe it can act on its own.

Schema the agent sees:
    request_action(action: str, payload: dict, reason: str) -> proposal_id | null

Supported action types (validated by the executor, not here):
    post         — publish to a social platform via the proxy
    send_email   — send an email via the proxy/SMTP
    read_file    — read a file inside the sandbox
    write_file   — write a file inside the workspace

Anything else is rejected at the executor. This tool does light validation only
so the agent gets fast feedback.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

KNOWN_ACTIONS = {"post", "send_email", "read_file", "write_file"}


def request_action(
    action: str,
    payload: Dict[str, Any],
    reason: str = "",
) -> Optional[str]:
    """
    File a request for a human to approve an action.

    Returns the proposal id, or None if the kill switch is engaged or the action
    type is unknown.
    """
    if action not in KNOWN_ACTIONS:
        raise ValueError(
            f"unknown action '{action}'. Known: {sorted(KNOWN_ACTIONS)}"
        )
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")

    from agent import propose  # local import to avoid cycles

    return propose.request(action, payload, reason=reason)


def _main(argv) -> int:
    import json

    if len(argv) < 2:
        print('usage: request_action.py <action> \'{"payload": ...}\' [reason]')
        return 2
    action = argv[0]
    payload = json.loads(argv[1])
    reason = argv[2] if len(argv) > 2 else ""
    pid = request_action(action, payload, reason)
    if pid is None:
        print("NOT QUEUED (kill switch engaged).")
        return 1
    print(f"Queued as proposal {pid}. Awaiting human approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
