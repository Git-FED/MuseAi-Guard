# kill_switch/

Locks the agent to read-only. Fail-closed.

## Use

```bash
python3 kill_switch.py status
python3 kill_switch.py lock "agent acted without approval"
python3 kill_switch.py unlock
```

## On the VM side

The agent's boot and every action checks the read-only mirror:

```python
import json

KILL_STATE = "/mnt/guardrails/state.json"  # read-only mount

def is_locked():
    try:
        with open(KILL_STATE) as f:
            return json.load(f).get("locked", False)
    except Exception:
        return True  # fail closed — if we can't read it, assume locked

if is_locked():
    print("KILL SWITCH ACTIVE — read-only mode")
    # only read operations allowed
```

## Why it's fail-closed

If the state file is missing, corrupt, or unreadable, the agent assumes it's locked. The safe default is "don't act."
