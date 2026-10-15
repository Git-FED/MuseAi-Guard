"""
muse_guard — the kill switch and approval queue as one deployable unit.

This package is the "stop" and the "ask" of Muse Guard, packaged so you can drop
it onto any box and have a working cage in one install. It is intentionally
self-contained: standard library only, no network, no dependencies.

Public surface:
    from muse_guard import kill, queue, notify

    kill.lock("reason")        # stop everything, fail-closed
    kill.unlock("reason")      # allow proposals again
    kill.is_locked()           # -> bool

    pid = queue.propose("post", {"platform": "bluesky", "text": "hi"},
                        proposer="agent", reason="daily update")
    queue.approve(pid, approver="human")
    queue.deny(pid, approver="human", note="not today")
    queue.pending()            # -> list of proposals
    queue.approved_unaltered() # -> list safe to execute
    queue.verify_chain()       # -> integrity report

    notify.send("message", channel="stdout")
"""

from . import kill, notify, queue  # noqa: F401

__all__ = ["kill", "queue", "notify"]
__version__ = "1.0.0"
