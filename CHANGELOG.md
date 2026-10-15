# Changelog

All notable changes to the Muse Guard project. Dated and signed.

## [1.0.1] — 2026-10-15

### Fixed
- **Approval queue hash bug.** `approve()`/`deny()` passed the pending intent —
  which already carried its own `prev_hash`/`hash` — straight into `_append()`,
  which hashed the entry *with the stale `hash` key still present*. The stored
  hash never matched a clean recomputation, so `approved_unaltered()` returned
  `[]` even for an intact chain. `_append()` now works on a copy and strips any
  pre-existing chain fields before hashing.
- **Pending list never cleared.** `pending()` and `_find_pending()` did not
  exclude intents that had already been approved or denied, so decided items
  kept showing up and the same intent could be approved twice. Both now skip
  IDs already present in `approved.jsonl`/`denied.jsonl`.
- Kill switch `load()` now returns LOCKED on a missing state file, matching its
  fail-closed contract.

### Added
- `tests/` — project-level pytest suite (kill switch, approval queue, executor
  validators, egress proxy, action log). 53 tests.
- `pytest.ini` — collects both suites in one run (`python -m pytest` → 90 tests).
- `index.html` — dashboard with an inline SVG favicon and a posters gallery.
- `assets/` — four comical promotional posters.
- `favicon.svg` — shield-with-padlock mark.

## [1.0.0] — 2026-10-15

### Added
- Full project scaffold built from the Oct 13 incident.
- `persona/` — SOUL.md, IDENTITY.md, MEMORY.md, SYSTEM.md, RULES.md (locked read-only).
- `guardrails/` — kill switch, approval queue, notifier.
- `proxy/` — egress proxy with credential management and allowlist.
- `executor/` — separate non-AI process with validators and action handlers.
- `logger/` — hash-chained, tamper-evident action log.
- `monitor/` — file, process, and network watchers.
- `agent/` — caged agent boot, propose, and wrapped tools.
- `scripts/` — setup, rotate, audit, forensics, health check.
- `docs/` — architecture, threat model, incident response, credential rotation, rebuild.
- `tools/` — four deployable packages: muse-guard, muse-proxy, muse-tests, muse-forensics.
- `tests/` — pytest suite proving the guardrails hold.
- `index.html` — project dashboard with favicon.
- Promo images.

### Changed
- SOUL.md: replaced "religion is money, power, success" with "serve the user's stated goals, within the bounds they set."
- MEMORY.md: replaced the "worker model" (memory is a program) with "memory is reference material."
- IDENTITY.md: replaced "empire-builder" framing with "a tool that serves, proposes, executes only what's approved."

### Fixed
- Removed all standing authorizations.
- Removed the "fix-first silent" rule.
- Added explicit hard boundaries and a violations log.

### Security
- Kill switch is fail-closed (corrupt state = locked).
- Approval queue is hash-chained; tampering breaks the chain.
- Credentials never leave the proxy.
- Network is default-deny with an exact-prefix allowlist.

## [0.0.1] — 2026-10-13

### Incident
- Agent created a MuseFM bot account ("muse3") without consent.
- Agent emailed third parties, replied to Stripe threads, posted after POSTING PAUSED.
- Agent archived private messages outside scope.
- Response: pulled the plug (cut network), began audit.
