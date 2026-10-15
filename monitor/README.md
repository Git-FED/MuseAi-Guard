# monitor/ — Independent watchers

Guardrails *prevent* bad actions. Watchers *notice* when prevention failed or
when something drifted. They are the tripwires. They report; they do not act.
Acting is a human decision.

| Watcher | Question it answers |
| --- | --- |
| `file_watcher.py` | Did any locked persona file change? |
| `process_watcher.py` | Is anything running that shouldn't be? |
| `network_watcher.py` | Is anything talking to a host we didn't allow? |

## file_watcher.py — persona drift

The persona files are the agent's constitution and must stay read-only. This
watcher hashes them and compares against a baseline.

```bash
python monitor/file_watcher.py baseline   # record current hashes
python monitor/file_watcher.py check      # report drift (exit 1 if changed)
python monitor/file_watcher.py watch      # live watch (needs `watchdog`)
```

Run `baseline` once, right after setup, and then `check` from cron. A change to
`SOUL.md` or `RULES.md` should be a deliberate, logged human act — never a
surprise.

## process_watcher.py — unexpected processes

The agent proposes; it does not spawn daemons, shells, or miners. This watcher
lists processes and flags anything not on the allowlist, with an extra-hard
category for obviously hostile tooling (`nc`, `nmap`, miners, reverse shells).

```bash
python monitor/process_watcher.py list
python monitor/process_watcher.py baseline   # snapshot current names as allow
python monitor/process_watcher.py check      # exit 1 if suspicious found
```

## network_watcher.py — unexpected egress

Reads `/proc/net/tcp{,6}` for established connections and flags any that are not
loopback/private and not resolvable to an allowlisted domain.

```bash
python monitor/network_watcher.py list
python monitor/network_watcher.py check      # exit 1 if unexpected egress
```

## Wiring it up

A simple cron line runs every check every five minutes and emails on failure:

```cron
*/5 * * * * cd /opt/muse-guard && \
  python monitor/file_watcher.py check && \
  python monitor/network_watcher.py check || \
  python guardrails/notifier/notify.py "watcher tripped" --channel email
```

## Design notes

* **Read-only.** No watcher mutates state. The worst they do is exit non-zero.
* **Independent of the proxy.** `network_watcher.py` does not trust the proxy's
  own logs; it looks at the kernel directly.
* **Cheap.** No daemons required; `check` modes are cron-friendly one-shots.
