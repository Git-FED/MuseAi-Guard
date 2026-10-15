# proxy/

The agent's only door to the internet. Holds credentials so the agent never sees them.

## How it works

1. Agent calls `forward(method, url, payload, cred_name)`.
2. Proxy checks the allowlist. No match = `PermissionError`, logged.
3. Proxy loads the credential, injects headers. Agent never sees it.
4. Request fires. Response returns.
5. Everything logged to `request_log.jsonl`.

## Files

| File | Purpose |
|------|---------|
| `egress_proxy.py` | The proxy |
| `allowlist.json` | Exact-prefix allowlist, no wildcards |
| `credentials/` | Raw secrets (chmod 600, gitignored) |
| `request_log.jsonl` | Every request, allowed or denied |

## Use

```python
from egress_proxy import forward

status, body = forward(
    "POST",
    "https://bsky.social/xrpc/com.atproto.repo.createRecord",
    payload={"repo": "did:plc:...", "collection": "app.bsky.feed.post", "record": {...}},
    cred_name="bluesky",
)
```

## Allowlist

Edit `allowlist.json`. Exact prefix only, no wildcards. The `blocked` list wins over the `domains` list.

## Log

`request_log.jsonl` — every request, allowed or denied. Rotate it weekly.
