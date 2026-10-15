# muse-proxy

**The credential-holding egress proxy.** Tool #2 of the four.

This is the only component in Muse Guard that touches a credential or makes an
outbound request. The agent asks the proxy to do something; the proxy checks the
allowlist, attaches the credential, makes the request, and logs it. The agent
never sees a key.

## What it gives you

- **Credentials the agent cannot read.** One secret per file, mode 0600, in a
  directory outside the agent's readable roots.
- **Exact-host, default-deny egress.** No wildcards. A host not on the list is
  refused and logged.
- **A kill-switch check on every request.** If the switch is engaged, the proxy
  refuses — fail-closed.
- **A blocked list.** Belt-and-suspenders denies (e.g. `*.workers.dev`) checked
  before the allowlist.

## Install

```bash
bash install.sh
# creates /opt/muse-proxy with a 0700 credential store and a `muse-proxy` launcher
```

## Configure

Edit `muse_proxy/allowlist.json`:

```json
{
  "domains": {
    "bsky.social": {"credential": "bluesky", "scheme": "https"},
    "mastodon.social": {"credential": "mastodon", "scheme": "https"}
  },
  "blocked": ["*.workers.dev", "cloudflare.com"]
}
```

Put credentials in the store (one per file, 0600):

```bash
printf '%s' "$BLUESKY_APP_PASSWORD" > /opt/muse-proxy/muse_proxy/credentials/bluesky
chmod 600 /opt/muse-proxy/muse_proxy/credentials/bluesky
```

## Use

```bash
muse-proxy --selftest                 # verify controls without touching network
muse-proxy request bsky.social /xrpc/app.bsky.feed.getTimeline GET
```

As a library:

```python
from muse_proxy import proxy, allowlist, creds

# The agent calls this; it never sees the credential.
result = proxy.request("bsky.social", method="POST",
                       path="/xrpc/com.atproto.repo.createRecord",
                       json_body={...})
# -> {"ok": True, "status": 200, "body": "..."}

allowlist.is_allowed("evil.example")   # -> False (default-deny)
```

## Why default-deny with no wildcards

Broad patterns like `*.workers.dev` are how the original incident reached
infrastructure it should never have touched. Exact hostnames force a human to
name each destination, which is the point: egress should be a deliberate,
enumerated list, not a category.

## Files

| File | Role |
| --- | --- |
| `muse_proxy/proxy.py` | The proxy: kill-switch check, allowlist, credential attach, request, log. |
| `muse_proxy/allowlist.py` | Exact-host, default-deny allowlist with a blocked list. |
| `muse_proxy/creds.py` | Credential store (0600, one per file, never logged). |
| `muse_proxy/allowlist.json` | The allowlist + blocked config. |
| `install.sh` | Installer + launcher. |

## Environment overrides

| Variable | Effect |
| --- | --- |
| `MUSE_PROXY_ALLOWLIST` | Path to the allowlist JSON. |
| `MUSE_PROXY_CREDS` | Path to the credential store. |

## The one-sentence version

**The agent can reach exactly the hosts you named, using keys it never sees.**
