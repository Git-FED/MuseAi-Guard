# credentials/

Raw secrets live HERE. Never on the VM's memory, never in `persona/`, never in `memory/`.

## Format

One JSON file per credential. `chmod 600`. Root-owned.

```json
{
  "headers": {
    "Authorization": "Bearer eyJ..."
  },
  "notes": "created 2026-10-15, scoped to post only"
}
```

## Rules

- One credential, one purpose. No shared tokens across platforms.
- Scope to the minimum. Posting token = posting only.
- Rotate on a schedule. Weekly for high-value, monthly for low.
- Never commit these files. They're in `.gitignore`.

## The point

The agent asks the proxy to make a call. The proxy adds the credential. The agent never sees it. If the agent is compromised, the credentials are still safe.
