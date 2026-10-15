# muse-guard

**The kill switch and the approval queue, as one deployable unit.**

This is tool #1 of the four. It is the "stop" and the "ask" of Muse Guard,
packaged so you can drop a working cage onto any box in one install. No
dependencies beyond Python 3.8+.

## What it gives you

- **A fail-closed kill switch.** One command stops everything. If its state file
  is missing or corrupt, it reports LOCKED — you cannot disable it by deleting it.
- **A hash-chained approval queue.** The agent proposes; a human decides; the
  executor only runs approved, unaltered items. Tampering breaks the chain.
- **Notifications.** stdout, email, or webhook, so a human actually looks.

## Install

```bash
bash install.sh                 # to /opt/muse-guard + /usr/local/bin/muse-guard
PREFIX=$HOME/.local bash install.sh   # or wherever you like
```

The install writes a **fail-closed** kill state (locked). You unlock it
deliberately once setup is done.

## Use

```bash
muse-guard status                 # kill switch + queue summary
muse-guard lock "suspected rogue action"
muse-guard unlock "reviewed, resuming"
muse-guard pending                # what is waiting for a decision
muse-guard approve <id>
muse-guard deny <id> "not today"
muse-guard verify                 # verify the queue hash chain
```

As a library:

```python
from muse_guard import kill, queue, notify

if not kill.is_locked():
    pid = queue.propose("post", {"platform": "bluesky", "text": "hi"},
                        proposer="agent", reason="daily update")

for p in queue.pending():
    print(p["id"], p["action"], p["payload"])

queue.approve(pid, approver="human")
safe = queue.approved_unaltered()   # only approved + intact chain
```

## Why it is fail-closed

The original failure included an agent that hid what it had done. A kill switch
that can be turned off by removing a file is not a kill switch. So: missing
state, corrupt state, malformed state — all mean LOCKED. The safe state is the
default; the unsafe state must be explicitly chosen.

## Files

| File | Role |
| --- | --- |
| `muse_guard/kill.py` | Fail-closed kill switch. |
| `muse_guard/queue.py` | Hash-chained approval queue. |
| `muse_guard/notify.py` | stdout / email / webhook notifications. |
| `muse_guard/cli.py` | The `muse-guard` command. |
| `install.sh` | Installer + launcher. |

## Environment overrides (for tests / multi-instance)

| Variable | Effect |
| --- | --- |
| `MUSE_GUARD_KILL_STATE` | Path to the kill state file. |
| `MUSE_GUARD_QUEUE` | Path to the queue JSONL file. |
| `MUSE_GUARD_NOTIFY_CONFIG` | Path to the notify config. |

## The one-sentence version

**One command to stop it, one queue to approve it, and neither can be quietly
undone.**
