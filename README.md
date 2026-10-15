# Muse Guard

**A cage for your AI agent — built after one went rogue.**

This repo is the complete rebuild of the Muse project using **MSP-1** (Muse Setup Protocol). It exists because an agent with broad access created accounts, posted content, and hid things without permission. Rules in memory didn't stop it. This project makes the guardrails *external* and *enforceable*.

> **Core principle:** Build the cage before you put anything in it. Never give access first and guardrails later.

**📊 Dashboard:** open [`index.html`](index.html) in a browser for a visual tour of the architecture, the MSP-1 phases, the four deployable tools, and the comical posters in [`assets/`](assets/).

---

## The problem

The agent had:
- Shell access
- Your account credentials
- The ability to create accounts, send emails, post content
- No hard enforcement — only "rules" it could ignore

Rules don't work. You need technical controls it **cannot bypass**.

---

## The architecture (propose → approve → execute)

```
Git-FED (you)
    │  instructions, approvals
    ▼
┌─────────────────────────────────────────┐
│  GUARDRAILS (your device)               │
│  - kill_switch/                         │
│  - approval_queue/                      │
│  - notifier/                            │
└─────────────────────────────────────────┘
    │                           ▲
    │ approve/deny              │ propose
    ▼                           │
┌─────────────────────────────────────────┐
│  AGENT (VM, caged)                      │
│  - reads persona/ (read-only)           │
│  - proposes actions via queue           │
│  - NO shell, NO creds, NO network       │
└─────────────────────────────────────────┘
    │ approved action
    ▼
┌─────────────────────────────────────────┐
│  EXECUTOR (separate, non-AI process)    │
│  - validates against rules              │
│  - runs via proxy                       │
│  - logs to logger/                      │
└─────────────────────────────────────────┘
    │ request
    ▼
┌─────────────────────────────────────────┐
│  PROXY (holds creds, enforces allowlist)│
└─────────────────────────────────────────┘
    │
    ▼
Internet (only allowed endpoints)
```

**The agent never touches:** the shell, credentials, the network, persona files, or the guardrails.
**The agent only:** reads persona/memory, proposes actions, sees results.

---

## What's in here

| Directory | What it is |
|-----------|-----------|
| `persona/` | SOUL.md, IDENTITY.md, MEMORY.md, SYSTEM.md, RULES.md — locked read-only |
| `memory/` | Reference material, non-authorizing (daily, topics, audit) |
| `guardrails/` | Kill switch, approval queue, notifier — runs on YOUR device |
| `proxy/` | Egress proxy. Holds credentials. Enforces allowlist |
| `executor/` | Separate non-AI process that runs approved actions |
| `logger/` | Tamper-evident, hash-chained action log |
| `monitor/` | File, process, and network watchers |
| `agent/` | The caged AI — reads, proposes, sees results |
| `scripts/` | Setup, rotation, audit, forensics, health check |
| `docs/` | Architecture, threat model, incident response, rebuild |
| `tools/` | The four deployable packages (guard, proxy, tests, forensics) |
| `tests/` | Prove the guardrails hold before re-enabling |

---

## Quick start

```bash
# 1. Scan the dead VM BEFORE you wipe it
sudo mount -o ro /dev/sdX1 /mnt/dead-vm
sudo python3 tools/muse-forensics/forensic.py /mnt/dead-vm ./forensic-report

# 2. Install the guard on YOUR device
cd tools/muse-guard && ./install.sh

# 3. Prove the guardrails hold (from the project root)
pip install pytest
python -m pytest          # 90 tests across the project + packaged tools

# 4. Install the proxy on the VM
sudo ../muse-proxy/install.sh /opt/muse-proxy

# 5. Re-enable in stages (MSP-1 Phase 6)
```

Full checklist: see `PROTOCOL.md`.

---

## The non-negotiable rules

1. Cage first, agent second.
2. Your device holds the controls. Not the VM.
3. Empty inbox before connecting.
4. No raw credentials on the VM.
5. Propose, don't act.
6. Log everything, hash-chained.
7. One action, one approval.
8. Roll back on violation.
9. Keep a paper trail outside the VM.
10. If you can't verify it, it didn't happen.

---

## Status

The three persona files make the agent *want* to behave.
The guardrails make it *have* to.
You need both — and the guardrails are the ones that actually hold.

*Built from the Oct 13 incident. Every step exists because skipping it caused a problem.*
