# Credential Rotation

Credentials are the agent's forbidden fruit. In Muse Guard the agent never
touches them; only the proxy does. This document explains how credentials are
stored, why, and how to rotate them without leaving a trail of still-valid
secrets behind you.

## The principle

> The agent must never be able to read a credential, and a credential that has
> been replaced must also be revoked.

Two ideas, both simple, both frequently skipped. The first is why the proxy
exists. The second is why rotation is not just "write a new value."

## Where credentials live

```
proxy/
  credentials/            ← the store. readable only by the proxy process.
    bluesky               ← one file per credential, 0600 perms
    mastodon
    smtp
    ...
  egress_proxy.py         ← the only code that reads the store
  allowlist.json          ← exact hostnames the proxy may reach
```

Rules:

- **One secret per file.** No bundling. Rotation touches one file.
- **Mode 0600.** Owner read/write only. No group, no world.
- **Never in the repo.** `credentials/` is git-ignored. Secrets in version
  control are secrets you have already leaked.
- **Never in logs.** The proxy logs *that* it used a credential, never its
  value. The action log has no field for secret values.
- **Never in memory.** The agent's memory files describe *that* an account
  exists, never its password.

## How the proxy uses them

When the agent proposes an action that needs a credential (a post, an email),
the executor calls the proxy. The proxy:

1. Checks the target host against the allowlist (default-deny).
2. Loads the relevant credential from the store.
3. Attaches it to the outbound request.
4. Logs the request (host, action, result — not the secret).
5. Returns the response.

The agent sees the *result*, never the credential. Even a fully hijacked agent
cannot exfiltrate a key it never possessed.

## Rotating a credential

Use the helper:

```bash
bash scripts/rotate_credentials.sh bluesky
```

It backs up the old value, prompts (hidden input) for the new one, writes it with
0600 perms, and reminds you of the two follow-ups. Then:

1. **Revoke the old credential at the provider.** This is the step people skip.
   Rotating without revoking means both the old and new secrets work. The whole
   point is to invalidate the old one.
2. **Restart the proxy** so it loads the new value.

### Doing it by hand

```bash
# 1. write the new value (hidden input)
read -r -s NEW; printf '%s' "$NEW" > proxy/credentials/bluesky; chmod 600 proxy/credentials/bluesky

# 2. revoke the old one at the provider (web console / API)

# 3. restart the proxy
```

## When to rotate

- **After any incident.** Assume compromise. Rotate everything the box could
  reach.
- **On a schedule.** Even absent an incident, rotate on a cadence (monthly is a
  reasonable default). Scheduled rotation bounds the value of a slow leak.
- **When a human with access leaves.** Their copy is still valid until revoked.
- **When you are unsure.** Rotation is cheap; a leaked key is not.

## What "revoke" means per provider

| Provider type | How to revoke |
| --- | --- |
| OAuth app tokens (Bluesky, Mastodon, X) | Revoke the app password / session in account settings. |
| SMTP / email | Change the account password; invalidate app passwords. |
| Cloud CLIs (AWS/GCP/Azure) | Delete the access key; rotate the IAM user. |
| GitHub | Revoke the personal access token / deploy key. |

The rule is uniform: find the credential in the provider's security settings and
delete it, then confirm it no longer works.

## Verification after rotation

```bash
# the store should have no world-readable files
find proxy/credentials -type f ! -perm 600 -printf 'INSECURE: %p\n'

# confirm the new credential works and the old one does not
# (run a real request through the proxy and check the result)
python proxy/egress_proxy.py --selftest
```

## Failure modes to avoid

1. **Rotate without revoke.** The most common mistake. Two valid secrets.
2. **Secrets in shell history.** Prefer hidden input (`read -s`) over passing
   secrets as arguments, which land in history and process lists.
3. **Secrets in backups that are world-readable.** If you back up the store,
   encrypt the backup.
4. **Secrets in the action log.** The proxy must never log values. Audit the
   proxy code if you are unsure.
5. **Forgetting the agent's memory.** If a memory file ever recorded a secret,
   rotate that secret *and* scrub the memory file, then re-baseline the watcher.

## The one-sentence version

**The proxy holds the keys, the agent never sees them, and a rotated key is a
revoked key — anything else is theater.**
