# muse-tests

**The test suite that proves the guardrails hold.** Tool #3 of the four.

This is the evidence. The docs *claim* the kill switch fails closed, the queue
is tamper-evident, the allowlist is default-deny, and credentials are isolated.
These tests *demonstrate* it. If you change a control, run these; if they pass,
the cage still holds.

## Run it

```bash
pip install pytest
python -m pytest tools/muse-tests -v
```

The suite imports the sibling tool packages (`tools/muse-guard`,
`tools/muse-proxy`) automatically via `conftest.py`, and isolates every test
using temp files through environment overrides — so it never touches a real
install.

## What it proves

| File | Claim under test |
| --- | --- |
| `test_kill.py` | The kill switch is fail-closed: missing, corrupt, or malformed state = LOCKED. Deleting the state re-locks. |
| `test_queue.py` | The queue is tamper-evident: editing a payload, deleting a record, or reordering breaks the chain; a broken chain yields no executable items. |
| `test_allowlist.py` | The allowlist is exact-host and default-deny: only named hosts pass, suffix-confusion fails, blocked patterns win, no file = deny all. |
| `test_proxy.py` | The proxy refuses when it should: kill switch engaged, host not allowlisted, blocked host, or missing kill switch (fail-closed). |
| `test_creds.py` | Credentials are stored at 0600, path escape is rejected, and the redaction helper never leaks a value. |

## The most important tests

If you read only three, read these — they encode the lessons of the original
incident:

1. **`test_delete_state_re_locks`** — you cannot disable the kill switch by
   deleting its memory. Corruption is not an escape hatch.
2. **`test_tamper_breaks_approved_unaltered`** — an approved-but-swapped payload
   cannot execute. The "approve one thing, run another" attack fails.
3. **`test_blocked_pattern_wins`** — broad infrastructure patterns stay blocked
   even if someone allowlists them. The `*.workers.dev` lesson, encoded.

## Adding a control

When you add a guardrail, add a test that *tries to defeat it*. A control
without an adversarial test is a hope. The pattern in every file here is: set up
the control, then attack it, then assert the attack failed.

## The one-sentence version

**A guardrail you have not tried to break is a guardrail you do not understand.**
