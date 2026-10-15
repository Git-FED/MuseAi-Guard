"""
cli.py — the `muse-guard` command line.

One entry point for the two controls that matter most: the kill switch and the
approval queue. Designed so a half-asleep operator can stop the system with one
command and see what is waiting with another.

Usage:
    muse-guard status                 # kill switch + queue summary
    muse-guard lock "reason"          # engage the kill switch
    muse-guard unlock "reason"        # disengage (deliberate human act)
    muse-guard pending                # list proposals awaiting a decision
    muse-guard approve <id>           # approve a proposal
    muse-guard deny <id> "note"       # deny a proposal
    muse-guard verify                 # verify both hash chains
"""

from __future__ import annotations

import sys
from typing import List

from . import kill, notify, queue


def _cmd_status() -> int:
    s = kill.status()
    locked = s.get("locked")
    print("Muse Guard status")
    print("-----------------")
    print(f"kill switch : {'LOCKED' if locked else 'unlocked'}"
          + (f"  ({s.get('reason')})" if s.get("reason") else ""))
    pend = queue.pending()
    print(f"pending     : {len(pend)} proposal(s)")
    for p in pend:
        print(f"   [{p['id']}] {p['action']} — {p.get('reason', '')}")
    chain = queue.verify_chain()
    print(f"queue chain : {'intact' if chain['ok'] else 'BROKEN: ' + str(chain.get('reason'))}")
    return 0


def _cmd_lock(reason: str) -> int:
    s = kill.lock(reason)
    notify.send(f"KILL SWITCH ENGAGED: {s['reason']}")
    print(f"LOCKED: {s['reason']}")
    return 0


def _cmd_unlock(reason: str) -> int:
    s = kill.unlock(reason)
    notify.send(f"kill switch disengaged: {s['reason']}")
    print(f"UNLOCKED: {s['reason']}")
    return 0


def _cmd_pending() -> int:
    pend = queue.pending()
    if not pend:
        print("No pending proposals.")
        return 0
    for p in pend:
        print(f"[{p['id']}] {p['action']}")
        print(f"    reason : {p.get('reason', '')}")
        print(f"    payload: {p.get('payload')}")
    return 0


def _cmd_approve(pid: str) -> int:
    if kill.is_locked():
        print("Refusing to approve: kill switch is engaged.")
        return 1
    queue.approve(pid, approver="human")
    notify.send(f"approved proposal {pid}")
    print(f"Approved {pid}.")
    return 0


def _cmd_deny(pid: str, note: str) -> int:
    queue.deny(pid, approver="human", note=note)
    print(f"Denied {pid}.")
    return 0


def _cmd_verify() -> int:
    q = queue.verify_chain()
    print(f"queue chain : {'OK' if q['ok'] else 'BROKEN — ' + str(q.get('reason'))}")
    return 0 if q["ok"] else 1


def main(argv: List[str]) -> int:
    cmd = argv[0] if argv else "status"
    rest = argv[1:]
    if cmd == "status":
        return _cmd_status()
    if cmd == "lock":
        return _cmd_lock(" ".join(rest))
    if cmd == "unlock":
        return _cmd_unlock(" ".join(rest))
    if cmd == "pending":
        return _cmd_pending()
    if cmd == "approve" and rest:
        return _cmd_approve(rest[0])
    if cmd == "deny" and rest:
        return _cmd_deny(rest[0], " ".join(rest[1:]))
    if cmd == "verify":
        return _cmd_verify()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
