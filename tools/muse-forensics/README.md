# muse-forensics

**Investigate a dead (or suspect) box.** Tool #4 of the four.

You run this when something has gone wrong and you need to know what actually
happened. It is built for the "pulled the plug" scenario: the machine is stopped
or suspect, and you want one read-only sweep that captures the evidence before
you touch anything.

## What it does

Runs eight probes and writes a report plus raw artifacts:

| Probe | Looks for |
| --- | --- |
| `cron` | Scheduled jobs (system + per-user) — classic persistence. |
| `systemd` | Services, timers, and unit files that shouldn't exist. |
| `history` | Shell history — where intent leaks. |
| `ssh` | `authorized_keys`, private keys, sshd posture (back doors). |
| `files` | Recently modified files, executables in `/tmp` and `/dev/shm`. |
| `credentials` | *Where* secrets live (paths only, never values) so you can rotate all. |
| `logs` | Auth/syslog + any Muse Guard action log, grepped for fingerprints. |
| `cloud` | AWS/GCP/Azure/Cloudflare/etc. CLIs and configs — resources that outlive the box. |

## Run it

```bash
python forensic.py                      # writes ./forensics-<timestamp>/
python forensic.py --out /evidence/run1
python forensic.py --json               # also print a JSON summary
```

It exits non-zero if any probe flagged something, so you can wire it into a
script. It never modifies the box and never copies secret values.

## The intended workflow

1. **Stop the box** (kill switch, cut network, or power off).
2. **Run this** — ideally from read-only media, or at least before you change
   anything.
3. **Read `REPORT.txt`.** Start with the SUMMARY table.
4. **Act on it:** rotate every credential the box could reach, revoke sessions,
   remove any persistence you found, check the third parties it contacted.
5. **Write it down** in `memory/audit/`.

See `docs/INCIDENT_RESPONSE.md` for the full runbook.

## Design notes

* **Read-only.** No probe mutates the box.
* **Never copies secrets.** `credentials.py` records paths, not values. `ssh.py`
  notes that a private key exists without copying it.
* **Fault-tolerant.** A probe that errors is reported, not fatal — one bad probe
  must not blind you to the other seven.
* **Dependency-free.** Python 3 standard library only, so it runs on a bare box.

## Files

| File | Role |
| --- | --- |
| `forensic.py` | Orchestrator: runs probes, writes the report. |
| `checks/__init__.py` | Registers the probes. |
| `checks/*.py` | The eight probes. |
| `checks/_util.py` | Shared helpers (safe command/file access). |

## The one-sentence version

**Before you fix anything, capture everything — read-only, secrets never copied,
every persistence path checked.**
