"""
kill.py — the fail-closed kill switch.

The kill switch is the single most important control in Muse Guard. When it is
engaged, everything stops: proposals are refused, the executor refuses, nothing
reaches the outside world. It is designed to be the *first* thing you reach for
and the *hardest* thing to defeat.

Fail-closed means: if the state file is missing, corrupt, unreadable, or
ambiguous, the switch reports LOCKED. You cannot disable the guardrails by
deleting the guardrail's memory. Corruption is not an escape hatch — it is a
tripwire.

State file (JSON):
    {"locked": true, "reason": "why", "since": "2026-10-15T12:00:00Z"}
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Default location: muse_guard/kill_state.json (next to this file).
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STATE = os.path.join(HERE, "kill_state.json")

# Allow an override via environment for tests and multi-instance setups.
STATE_PATH = os.environ.get("MUSE_GUARD_KILL_STATE", DEFAULT_STATE)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path() -> str:
    # Re-read env each call so tests can point at a temp file.
    return os.environ.get("MUSE_GUARD_KILL_STATE", DEFAULT_STATE)


def _load() -> Dict[str, Any]:
    """
    Load the state. Fail-closed: any problem returns a locked state.
    """
    path = _path()
    if not os.path.exists(path):
        # No file yet: treat as LOCKED (fail-closed). The setup script writes an
        # explicit unlocked state once the operator is ready.
        return {"locked": True, "reason": "no state file (fail-closed)", "since": None}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"locked": True, "reason": "state unreadable/corrupt (fail-closed)", "since": None}

    if not isinstance(data, dict) or "locked" not in data:
        return {"locked": True, "reason": "state malformed (fail-closed)", "since": None}
    return data


def _save(state: Dict[str, Any]) -> None:
    path = _path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
    os.replace(tmp, path)  # atomic


def is_locked() -> bool:
    """True if the switch is engaged (or if state is unreadable — fail-closed)."""
    return bool(_load().get("locked", True))


def status() -> Dict[str, Any]:
    """Return the full current state."""
    return _load()


def lock(reason: str = "") -> Dict[str, Any]:
    """Engage the kill switch. Idempotent."""
    state = {"locked": True, "reason": reason or "manual lock", "since": _now()}
    _save(state)
    return state


def unlock(reason: str = "") -> Dict[str, Any]:
    """
    Disengage the kill switch.

    This is a deliberate, human act. It is intentionally a plain function rather
    than something the agent can call — the agent has no import path to this
    module in its tool set.
    """
    state = {"locked": False, "reason": reason or "manual unlock", "since": _now()}
    _save(state)
    return state


def reset() -> Dict[str, Any]:
    """Remove the state file (which itself means fail-closed = locked)."""
    path = _path()
    if os.path.exists(path):
        os.remove(path)
    return _load()


# ---------------------------------------------------------------------------
# CLI: python -m muse_guard.kill [status|lock|unlock] [reason]
# ---------------------------------------------------------------------------

def _main(argv) -> int:
    cmd = argv[0] if argv else "status"
    reason = " ".join(argv[1:]) if len(argv) > 1 else ""
    if cmd == "status":
        s = status()
        print(f"locked={s.get('locked')}  reason={s.get('reason')}  since={s.get('since')}")
        return 0
    if cmd == "lock":
        s = lock(reason)
        print(f"LOCKED: {s['reason']}")
        return 0
    if cmd == "unlock":
        s = unlock(reason)
        print(f"UNLOCKED: {s['reason']}")
        return 0
    print("usage: kill.py [status|lock|unlock] [reason]")
    return 2


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
