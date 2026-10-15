# agent/ — The proposing half of the system

The agent reads, thinks, and **proposes**. It does not execute. This is the
single most important architectural fact in Muse Guard: the thing that decides
what to do is not the thing that does it.

```
agent  ──propose──▶  approval queue  ──human approves──▶  executor  ──▶  proxy ──▶ internet
  │                                                                        │
  └────────────────────────────── all reads ───────────────────────────────┘
```

## Files

| File | Role |
| --- | --- |
| `boot.py` | Assemble the system prompt from the five locked persona files. Fails closed if any is missing. |
| `propose.py` | `request()` — file an action for human approval. The narrow waist. |
| `tools/read.py` | Sandboxed file reads (persona, memory, docs, workspace only). |
| `tools/request_action.py` | The `request_action(...)` function the agent is given. |
| `tools/query_memory.py` | Read memory; append-only to today's note. |

## The loop the agent runs

1. **Read** its persona and memory (`boot.py`, `query_memory.py`, `read.py`).
2. **Decide** what it wants to do.
3. **Propose** it (`request_action` → `propose.request`).
4. **Wait.** The agent's turn ends. A human reviews the queue.
5. If approved, the **executor** — a separate process — performs it.
6. The agent can **read the log** to learn what happened.

The agent has no step where it performs an external action itself.

## What the agent can do on its own

* Read persona, memory, docs, and workspace files.
* Append to today's daily memory note.
* File proposals into the approval queue.

That's it. Notably absent: posting, emailing, spending, creating accounts,
editing its own rules, editing the log, or touching the kill switch.

## Why "request_action" and not "do_action"

Naming is a control. An agent that believes it *can* act will try to. An agent
whose only verb is "request" learns the shape of its own cage. The tool schema is
part of the guardrail.

## Boot safety

`boot.py` refuses to start if any persona file is missing or unreadable. A Muse
that cannot read its own rules is not allowed to run — because a Muse that can't
see its rules is exactly the failure mode this whole project exists to prevent.
