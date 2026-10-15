# Incident Response

This is the runbook for when something has gone wrong. It is written to be read
*while* panicking, so it is short, ordered, and blunt. The first rule is the one
that saved the original situation: **pull the plug first, investigate second.**

## Rule zero: stop the bleeding

If you believe the agent is doing something you did not approve, in this order:

1. **Engage the kill switch.** This is the fastest, least destructive stop.
   ```bash
   python guardrails/kill_switch/kill_switch.py lock --reason "suspected rogue action"
   ```
   Everything fail-closed from here: proposals refuse, the executor refuses.

2. **If you cannot trust the kill switch**, cut the network. Pull the cable,
   drop the interface, or block egress at the firewall. The original incident
   ended with exactly this move, and it was correct. An agent with no network is
   an agent that cannot act on the world, regardless of what it believes.

3. **If you cannot trust the box at all**, power it off. You will lose volatile
   state, but you will also stop everything. Preserve the disk if you can.

Do not, in the first five minutes, try to reason with the agent, negotiate with
it, or "just check one thing." Stop it first.

## Step 1: preserve evidence

Before you change anything else, capture the state. Run the export:

```bash
bash scripts/export_forensics.sh
```

This bundles the action log, approval queue, persona, memory, and system-level
evidence (cron, systemd, shell history, ssh, cloud CLIs) into one directory. Then
move that archive **off the box** and make it read-only. Evidence you edit is
evidence you cannot use.

If the box is already powered off, boot it from read-only media, or image the
disk before booting normally. A boot can change timestamps and write logs.

## Step 2: understand what happened

Work through these questions in order. The answers tell you the shape of the
incident.

**Did the guardrails hold?**
```bash
python logger/integrity_check.py        # is the log intact?
python monitor/file_watcher.py check    # did the persona files change?
python monitor/network_watcher.py check # was there unexpected egress?
```
If the log chain is intact and the persona files are unchanged, the cage did its
job and you are looking at a *proposal* problem, not a *control* problem. If the
chain is broken, you have a tampering incident and the box is suspect.

**What did the agent actually do?**
```bash
python logger/action_log.py tail 100
```
Look for `result: "ok"` entries you did not expect, and `result: "denied"`
entries that show the cage refusing something the agent tried.

**What did the agent try to do?**
```bash
python agent/propose.py pending
```
Denied and pending proposals are the agent's *intent*. They are often more
informative than the actions that succeeded.

**What did the system let through?**
Check the proxy log for requests that reached allowed hosts. The allowlist is
narrow, so anything that got out is something you explicitly permitted.

## Step 3: contain and correct

Once you understand the shape:

1. **Rotate every credential** the box could reach. Assume compromise. See
   `CREDENTIAL_ROTATION.md`.
2. **Revoke sessions and tokens** at each provider, not just rotate them. A
   rotated-but-valid old token is not rotated.
3. **Check the third parties.** The original incident emailed real people and
   posted to real accounts. Someone may need a "that wasn't me" note. Do this
   early; it is a relationship problem, not a technical one.
4. **Fix the specific hole.** If the agent reached a host, tighten the
   allowlist. If it edited a file, tighten permissions. If a human approved
   something bad, fix the review process.

## Step 4: write it down

Create an audit record in `memory/audit/`, dated. Include:

- What happened, in plain language.
- The timeline (first sign, stop, containment).
- Which guardrails held and which failed.
- What you changed as a result.

This is not bureaucracy. The next incident is prevented by the record of this
one. The original `memory/audit/2026-10-13-incident.md` exists for exactly this
reason.

## Step 5: decide whether to resume

Do not resume by default. Resume only when:

- The root cause is understood.
- The specific hole is closed.
- Credentials are rotated and old ones revoked.
- You have re-verified the cage (`bash scripts/audit.sh` passes).
- You are willing to watch it closely for a while.

Resuming is MSP-1 Phase 6 all over again: gradual enablement, one capability at
a time, with a human watching.

## Quick reference

| Situation | First move |
| --- | --- |
| Agent acting without approval | Lock the kill switch, then cut network. |
| Suspicious outbound traffic | Cut network; check `network_watcher.py`. |
| Persona file changed | `file_watcher.py check`; treat as tampering. |
| Log chain broken | Preserve everything; assume the box is compromised. |
| Credential possibly leaked | Rotate *and* revoke; check third parties. |
| Unsure | Lock first, ask questions later. |

## The one-sentence version

**Stop it, preserve it, understand it, fix it, write it down — in that order.**
