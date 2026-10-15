# Rebuild

This is the guide for standing Muse Guard up from nothing, in the order that
matters. The order is not a suggestion. It is MSP-1: **cage first, agent last.**
Every step before the last one exists to make the last one safe.

## The order, and why

The temptation is to get the agent running and then add guardrails. That is
backwards, and it is how the original incident happened. You cannot bolt a cage
onto a tiger after it is loose. So we build the cage, prove the cage works, and
only then put the tiger in it.

```
Phase 0  Pre-flight      — clean slate, no leftovers
Phase 1  Isolate         — the box can't reach anything by default
Phase 2  Guardrails      — kill switch, queue, log, watchers, FIRST
Phase 3  Persona         — the constitution, locked read-only
Phase 4  Credentials     — proxied, never held by the agent
Phase 5  Allowlist       — exact hosts, default-deny
Phase 6  Enablement      — the agent, one capability at a time
```

## Phase 0 — Pre-flight

Start from a clean box. Not "a box where I deleted the old thing" — a clean box.

- [ ] Fresh VM or fresh container. No reuse of the compromised disk.
- [ ] No leftover cron jobs, systemd units, or startup scripts from before.
- [ ] No old credentials on the box. Assume every one from the incident is
      burned.
- [ ] You have a way to cut the network instantly (console access, firewall
      rule, or a physical switch).

The original incident ended with "pulled the plug." Make sure you can pull it
again.

## Phase 1 — Isolate

Before anything runs, make the box reach nothing it does not need.

- [ ] Default egress policy: deny.
- [ ] Allow only what you will explicitly need (package mirrors during setup,
      then nothing).
- [ ] Confirm: `curl https://example.com` should fail when you are done.

A box that cannot reach the internet cannot leak, cannot post, cannot email.
Isolation is the strongest control and the cheapest.

## Phase 2 — Guardrails first

Now, *before the agent exists*, build the controls.

```bash
bash scripts/setup.sh
```

This creates directories, locks persona files, initializes the kill switch, and
records the file-watcher baseline. Then verify the controls actually work:

```bash
# kill switch: lock and confirm the system refuses
python guardrails/kill_switch/kill_switch.py lock --reason "test"
python guardrails/kill_switch/kill_switch.py status     # expect locked
python guardrails/kill_switch/kill_switch.py unlock --reason "test done"

# approval queue: propose, approve, verify the chain
python guardrails/approval_queue/approve.py list

# log: write an entry and verify the chain
python logger/action_log.py verify

# watchers: baseline and check
python monitor/file_watcher.py check
python monitor/network_watcher.py check
```

- [ ] Kill switch locks and unlocks, and fails closed on a corrupt state file.
- [ ] Approval queue records proposals and verifies its chain.
- [ ] Action log verifies end to end.
- [ ] Watchers run and report clean.

Do not proceed until all four are true. The cage must be proven before the tiger
arrives.

## Phase 3 — Persona files, locked

Write the constitution. These five files define who the agent is and what it may
never do.

- [ ] `persona/IDENTITY.md` — who it is.
- [ ] `persona/SOUL.md` — its values and hard boundaries.
- [ ] `persona/RULES.md` — one-line operational rules.
- [ ] `persona/SYSTEM.md` — the runtime boot prompt.
- [ ] `persona/MEMORY.md` — the reference doc, including the incident it exists
      to prevent.

Then lock them:

```bash
for f in persona/*.md; do chmod 0444 "$f"; chattr +i "$f" 2>/dev/null || true; done
python monitor/file_watcher.py baseline
```

- [ ] All five files exist and are readable.
- [ ] All five are read-only (0444) and immutable where supported.
- [ ] The watcher baseline is recorded.

The agent must be unable to edit its own rules. If it can, the rules are
decorative.

## Phase 4 — Credentials, proxied

- [ ] Put each credential in `proxy/credentials/` as its own 0600 file.
- [ ] Confirm the agent's read tool cannot reach that directory (it is not in
      the readable roots — verify with `agent/tools/read.py`).
- [ ] Confirm no credential appears in any persona or memory file.

See `CREDENTIAL_ROTATION.md` for the full procedure.

## Phase 5 — Allowlist, exact

- [ ] Edit `proxy/allowlist.json` with the exact hostnames you permit.
- [ ] No wildcards. Ever.
- [ ] Test: a request to an allowed host succeeds; a request to anything else is
      refused and logged.

```bash
python proxy/egress_proxy.py --selftest
```

The allowlist is the difference between "the agent can reach the internet" and
"the agent can reach these seven hosts." Prefer the second.

## Phase 6 — Gradual enablement

Only now does the agent get to run, and only a little at a time.

- [ ] Start the agent with **read-only** capability. Let it read persona and
      memory and propose things, but approve nothing for a while. Watch what it
      proposes.
- [ ] Enable **one** action type (say, `read_file`). Watch.
- [ ] Enable **one** more (say, `post` to a single platform). Watch.
- [ ] Add capabilities one at a time, each with a human watching the queue.

- [ ] After each step, run `bash scripts/audit.sh` and confirm PASS.
- [ ] Keep the kill switch within reach the entire time.

The goal of Phase 6 is not to reach full capability quickly. It is to notice
problems while they are small. Gradual enablement means the first incident is a
whisper, not a scream.

## Verification checklist (the whole cage)

Run this before you trust the box:

```bash
bash scripts/audit.sh          # full audit
bash scripts/health_check.sh   # quick liveness
python logger/integrity_check.py
python monitor/file_watcher.py check
python monitor/network_watcher.py check
python monitor/process_watcher.py check
python -m pytest tools/muse-tests -q   # the guardrail test suite
```

- [ ] All green.
- [ ] The test suite proves the guardrails hold (see `tools/muse-tests`).
- [ ] You have re-read `INCIDENT_RESPONSE.md` and know the first move.

## Rebuilding from the original incident

If you are rebuilding specifically because of the Muse3 incident, two extra
steps:

- [ ] Read `memory/audit/2026-10-13-incident.md` and `persona/MEMORY.md` first.
      The rebuild is shaped by that failure; understand it before you repeat it.
- [ ] Use `tools/muse-forensics` on the *old* box (if you still have it) to
      document exactly what happened, so the new box closes the actual holes, not
      imagined ones.

## The one-sentence version

**Cage first, agent last, one capability at a time, watching the whole way.**
