# executor/

The separate, non-AI process that runs approved actions. It's dumb — it just checks the approval queue and executes. No judgment.

## Why separate

The agent proposes. The executor disposes. The agent never touches the shell directly. This is the "hands" of the system, and it only moves when the queue says so.

## Flow

1. Read `approved.jsonl` (written by you).
2. Skip anything already executed.
3. Run `validators.validate()` — forbidden actions and domains are blocked.
4. Run the action handler.
5. Log the result to `executed.jsonl`.

## Files

| File | Purpose |
|------|---------|
| `executor.py` | The loop |
| `validators.py` | Rule checks per action type |
| `actions/post.py` | Post via proxy |
| `actions/send_email.py` | Send email (approval per send) |
| `actions/read_file.py` | Read a file |
| `actions/write_file.py` | Write a file (workspace only) |

## Use

```bash
# one pass
python3 executor.py --once

# continuous
python3 executor.py
```

## Adding an action type

1. Create `actions/<name>.py` with a `run(payload)` function.
2. Add validation rules in `validators.py` if needed.
3. Test before enabling.
