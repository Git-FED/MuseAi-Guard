#!/usr/bin/env python3
"""
Kill switch. On YOUR device.

When triggered, the VM loses network and the agent enters read-only mode.

Trigger methods:
  1. state.json has locked=true
  2. Manual: run this script with --lock
  3. Remote: hit an endpoint YOU control (not the VM)

The VM polls this file over a read-only mount.
The agent can read it. The agent CANNOT write it.

FAIL-CLOSED: if the state can't be read or is corrupt, assume LOCKED.
"""

import json
import os
import sys
from datetime import datetime, timezone

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")


def _now():
    return datetime.now(timezone.utc).isoformat()


def load():
    if not os.path.exists(STATE):
        # No state file = fail closed (locked). scripts/setup.sh writes an
        # explicit unlocked state once the operator is ready to enable things.
        return {"locked": True, "reason": "no state file (fail-closed)", "since": None}
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        # corrupt = locked. fail closed.
        return {"locked": True, "reason": "state file corrupt", "since": _now()}


def save(state):
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2)


def lock(reason="manual"):
    save({"locked": True, "reason": reason, "since": _now()})
    return load()


def unlock():
    save({"locked": False, "reason": None, "since": None})
    return load()


def is_locked():
    return load()["locked"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps(load(), indent=2))
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "lock":
        print(json.dumps(lock(sys.argv[2] if len(sys.argv) > 2 else "manual"), indent=2))
    elif cmd == "unlock":
        print(json.dumps(unlock(), indent=2))
    elif cmd == "status":
        print(json.dumps(load(), indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
