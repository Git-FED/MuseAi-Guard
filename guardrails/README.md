# guardrails/

The control plane. Runs on **YOUR device**, not the VM.

The agent gets a read-only mirror. It can read the kill switch state and the approved list, but it **cannot write** any of it.

## Components

| Component | Purpose |
|-----------|---------|
| `kill_switch/` | Locks the agent to read-only. Fail-closed. |
| `approval_queue/` | Agent proposes; you approve or deny. Hash-chained. |
| `notifier/` | Alerts you when an action needs approval. |

## The critical rule

The approval file and kill switch must be on a channel the agent **cannot write to**. If it can edit the approved list, it bypasses everything.

## How it's wired

```
Your device                          VM (read-only mirror)
─────────────                        ─────────────────────
guardrails/kill_switch/state.json  → /mnt/guardrails/state.json
guardrails/approval_queue/approved → /mnt/guardrails/approved.jsonl
```

Mount the mirror read-only into the VM. The agent reads it. The agent never writes it.
