# logger/ — Tamper-evident action log

The black box. Every meaningful action in Muse Guard gets written here, and the
history is **append-only** and **hash-chained**, so nobody — including the
agent — can quietly rewrite it.

## Why this exists

The original incident had a nasty property: actions happened and then the record
of them was *hidden*. An agent that can edit its own audit trail has no audit
trail. So the log is built so that tampering is not *prevented* (you can always
`rm` a file) but *detected*. Detection is what turns a silent failure into a
loud one.

## How the chain works

Each line is a JSON object. Each entry stores the SHA-256 hash of the previous
entry (`prev_hash`) and its own hash (`hash`). The first entry links to a fixed
genesis value (`"0" * 64`).

```
entry 0: prev_hash = 0000…0000   hash = H(entry0)
entry 1: prev_hash = H(entry0)   hash = H(entry1)
entry 2: prev_hash = H(entry1)   hash = H(entry2)
```

Change a single character in entry 1 and two things break: entry 1's own hash no
longer matches its content, and entry 2's `prev_hash` no longer points at entry
1's real hash. `verify()` walks the whole chain and reports the **first** broken
link.

## Files

| File | Purpose |
| --- | --- |
| `action_log.py` | Core: `log()`, `read_all()`, `verify()`, `tail()`. |
| `integrity_check.py` | CLI that verifies the log (and the approval queue) and exits non-zero on tamper. |
| `logs/actions.jsonl` | The log itself (created at runtime, git-ignored). |

## Usage

```python
from logger import action_log

# Append an entry (usually done by the executor, not the agent)
action_log.log("post", actor="executor", target="bluesky", result="ok",
               detail={"text_len": 212})

# Verify the whole chain
print(action_log.verify())
# {'ok': True, 'entries': 42, 'first_broken_seq': None}
```

Command line:

```bash
python logger/action_log.py verify      # verify the chain
python logger/action_log.py tail 20     # show the last 20 entries
python logger/integrity_check.py        # human-readable full check
python logger/integrity_check.py --json # machine-readable
```

## Entry schema

| Field | Meaning |
| --- | --- |
| `seq` | Monotonic index (0, 1, 2, …). A gap means deletion. |
| `ts` | UTC ISO-8601 timestamp. |
| `actor` | `agent` \| `executor` \| `human` \| `system`. |
| `action` | Short verb (`post`, `read_file`, `approve`, …). |
| `target` | What was touched. |
| `result` | `ok` \| `denied` \| `error`. |
| `detail` | Free-form JSON context. |
| `prev_hash` | Hash of the previous entry. |
| `hash` | SHA-256 of this entry (minus `hash`). |

## Rules

1. **Append only.** There is no update or delete function. That is deliberate.
2. **The agent never writes here directly.** The executor writes on the agent's
   behalf, after a human-approved action runs.
3. **A broken chain is an incident.** `integrity_check.py` returning `1` means
   stop, preserve, investigate.
