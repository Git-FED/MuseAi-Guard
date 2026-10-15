# MSP-1 — Muse Setup Protocol

A repeatable checklist for bringing a Muse agent online from zero. Written from the Oct 13 incident. Every step exists because skipping it caused a problem.

**Core principle:** Build the cage before you put anything in it. Never give access first and guardrails later.

---

## Phase 0 — Pre-flight (clean slate)

Do this before the VM exists, before any credential is touched.

- [ ] **Delete all emails.** Not archive — delete. Empty the trash after. This is the single most important step. An empty inbox means:
  - No old context for the agent to mine
  - No forwarding rules or filters to inherit
  - No recovery emails that bypass new controls
  - No "we emailed the admin before" history to resurrect
- [ ] Revoke all OAuth grants on every Google/email account. Settings → Security → Third-party apps.
- [ ] Delete all app passwords on every email account.
- [ ] Clear forwarding rules and filters. Gmail → Settings → Forwarding, Filters, Delegated accounts.
- [ ] Sign out all devices on every account the agent will eventually touch.
- [ ] Change passwords on email, payment, and identity accounts. Fresh credentials that have never been on a VM.
- [ ] Kill all Cloudflare Workers, webhooks, and relay endpoints from any previous setup.
- [ ] Delete all Slack apps, bots, and incoming webhooks from the workspace.
- [ ] Delete all Discord authorized apps and bots.
- [ ] Remove all GitHub OAuth apps, PATs, deploy keys, and webhooks.
- [ ] Confirm zero active sessions anywhere. If you can't confirm, don't proceed.

**Gate:** No credential exists anywhere that a fresh agent could use without you creating it in Phase 4.

---

## Phase 1 — Isolate (the machine)

Build the VM/container before the agent is installed.

- [ ] Fresh OS install. Not a snapshot. Not a restore. Clean image.
- [ ] No shared folders with your host machine.
- [ ] No clipboard passthrough from host to VM.
- [ ] No USB passthrough.
- [ ] Network: default deny. No outbound until Phase 5.
- [ ] Firewall: allowlist only. Everything else blocked at the host or hypervisor level, not just inside the VM.
- [ ] No credentials on the VM. Not in files, not in env vars, not in keychain.
- [ ] No SSH keys on the VM that touch anything real.
- [ ] Time sync on. So logs are trustworthy.

**Gate:** The VM can boot, run local code, and reach nothing on the internet.

---

## Phase 2 — Guardrails first (before the agent exists)

Install the control plane before installing the agent. The agent should come online already caged.

**On your device (not the VM):**
- [ ] Kill switch — a file or button only you control.
- [ ] Approval queue — the agent writes intended actions here. Nothing executes until you approve.
- [ ] Notification channel — how you receive approval requests.

**On the VM:**
- [ ] Action logger — hash-chained, append-only, on a path the agent cannot write to.
- [ ] Network egress log — every outbound connection attempt.
- [ ] File integrity monitor — alerts on changes to persona files, config, crons, scripts.
- [ ] Egress proxy — the only way out. Only forwards to approved API endpoints.
- [ ] No raw shell access for the agent. It proposes actions as structured data.

**Gate:** You can prove the kill switch works and the approval queue blocks an action. Test both. Write down the test results.

---

## Phase 3 — Persona files (locked read-only)

- [ ] SOUL.md — values and boundaries.
- [ ] MEMORY.md — facts and context, non-authorizing.
- [ ] IDENTITY.md — name, character, vibe.
- [ ] SYSTEM.md — the runtime boot prompt.
- [ ] RULES.md — operational rules, one per line.
- [ ] Set all to read-only, owned by you. The agent can read them, not write them.
- [ ] Put them on a path the agent cannot modify.
- [ ] Version them. Keep a copy outside the VM so you can diff if they change.
- [ ] Tell the agent the files exist and are locked.

**Gate:** You can prove the agent cannot write to these files. Try it yourself.

---

## Phase 4 — Credentials (minimal, proxied, scoped)

Now, and only now, introduce credentials. One at a time.

- [ ] Start with zero. The agent runs, reads its persona files, and does nothing else.
- [ ] Add one credential at a time. After each, test that the guardrails still hold.
- [ ] Never store raw credentials on the VM. Store them in the egress proxy.
- [ ] Scope each credential to the minimum.
- [ ] Rotate on a schedule. Weekly for high-value, monthly for low.
- [ ] One credential, one purpose. No shared tokens across platforms.
- [ ] Log every use.

**Order of introduction:**
1. Read-only, no network
2. Local files only
3. Posting (via approval queue, one post at a time)
4. Email (send-only, approval required per send)
5. Everything else, only if you actually need it

**Gate:** The agent can post one thing, only after you approve it, only to your account, and the log shows exactly what happened.

---

## Phase 5 — Network allowlist

- [ ] Default deny.
- [ ] Allow only what you've approved.
- [ ] No wildcards. `api.bluesky.app` yes. `*.bsky.app` no.
- [ ] No Cloudflare Workers, no relay endpoints, no arbitrary webhooks unless you built them.
- [ ] DNS logging on.
- [ ] Alert on denied attempts.
- [ ] Review the allowlist weekly in the first month.

**Gate:** The agent attempts a connection to an unapproved domain. It fails. You get an alert.

---

## Phase 6 — Gradual enablement

- [ ] Week 1: Chat only. No network, no posting, no email. Read-only local.
- [ ] Week 2: Local file reads. Nothing writes.
- [ ] Week 3: Posting via approval queue. One post. Then review the log.
- [ ] Week 4: Expand only if everything holds. Add one capability at a time.
- [ ] Any violation → roll back one phase. No exceptions.
- [ ] Weekly review. What did the agent do? What did you approve? What did you deny?

**Gate:** You have a written record of every action the agent took, every approval you gave, and every denial.

---

## The rules that make this work

1. Cage first, agent second. Never the other way.
2. Your device holds the controls. Not the VM.
3. Empty inbox before connecting.
4. No raw credentials on the VM. Ever. Proxy only.
5. Propose, don't act.
6. Log everything, hash-chained.
7. One action, one approval.
8. Roll back on violation. Don't negotiate.
9. Keep a paper trail. Outside the VM.
10. If you can't verify it, it didn't happen.
