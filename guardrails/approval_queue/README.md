# approval_queue/

Agent proposes. You approve or deny. Nothing executes without your tap.

## Files

| File | Who writes | What |
|------|-----------|------|
| `pending.jsonl` | Agent | Intended actions, awaiting decision |
| `approved.jsonl` | You | Your approvals (hash-chained) |
| `denied.jsonl` | You | Your denials |

## Use

```bash
# List pending
python3 approve.py

# Approve
python3 approve.py approve <intent-id> "looks good"

# Deny
python3 approve.py deny <intent-id> "not authorized"
```

## Agent side

```python
from queue import propose

iid = propose("post", {"platform": "bluesky", "content": "..."}, "user asked")
# returns intent id. nothing executes.
```

The agent **cannot** approve, deny, lock, or unlock. Only you can.

## Tamper evidence

Every entry is hash-chained. `approved_unaltered()` returns only the entries whose chain verifies — it stops at the first break. If the agent edits the approved file, the chain breaks and the executor sees nothing past the break.
