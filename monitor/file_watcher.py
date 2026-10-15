#!/usr/bin/env python3
"""
file_watcher.py — Watch the locked persona files for unauthorized changes.

The persona files (SOUL.md, IDENTITY.md, MEMORY.md, SYSTEM.md, RULES.md) are the
agent's constitution. They are meant to be read-only. This watcher computes a
SHA-256 baseline of each protected file and alerts if any of them changes.

Two modes:
  * baseline : record current hashes to monitor/baseline.json
  * check    : compare current hashes against the baseline, report drift

Optionally, if the `watchdog` package is installed, `watch` runs a live monitor
that fires on any change event. Without watchdog, use `check` from cron.

This is defense in depth: file permissions are the primary control, this is the
tripwire that catches the case where permissions were bypassed.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
BASELINE_FILE = os.path.join(HERE, "baseline.json")

# Files that must never change without a deliberate, logged human action.
PROTECTED = [
    "persona/SOUL.md",
    "persona/IDENTITY.md",
    "persona/MEMORY.md",
    "persona/SYSTEM.md",
    "persona/RULES.md",
]


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _abs(rel: str) -> str:
    return os.path.join(PROJECT_ROOT, rel)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot() -> Dict[str, str]:
    """Return {relative_path: sha256} for every protected file that exists."""
    out: Dict[str, str] = {}
    for rel in PROTECTED:
        path = _abs(rel)
        if os.path.exists(path):
            out[rel] = _sha256(path)
    return out


def write_baseline() -> Dict[str, str]:
    snap = snapshot()
    data = {"created": _now(), "files": snap}
    with open(BASELINE_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return snap


def load_baseline() -> Dict[str, str]:
    if not os.path.exists(BASELINE_FILE):
        raise FileNotFoundError(
            f"No baseline at {BASELINE_FILE}. Run: file_watcher.py baseline"
        )
    with open(BASELINE_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh).get("files", {})


def check() -> Dict[str, object]:
    """
    Compare current state against baseline.

    Returns a report:
      { "ok": bool, "changed": [...], "missing": [...], "added": [...], "when": ts }
    """
    baseline = load_baseline()
    current = snapshot()

    changed: List[str] = []
    missing: List[str] = []
    added: List[str] = []

    for rel, old_hash in baseline.items():
        if rel not in current:
            missing.append(rel)
        elif current[rel] != old_hash:
            changed.append(rel)

    for rel in current:
        if rel not in baseline:
            added.append(rel)

    ok = not (changed or missing or added)
    return {
        "ok": ok,
        "changed": changed,
        "missing": missing,
        "added": added,
        "when": _now(),
    }


def watch() -> int:
    """Live watch using watchdog, if available. Blocks until interrupted."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        print("watchdog not installed; falling back to one-shot check.")
        return 0 if check()["ok"] else 1

    class Handler(FileSystemEventHandler):
        def on_any_event(self, event):  # noqa: D401
            src = getattr(event, "src_path", "")
            if any(src.endswith(os.path.basename(p)) for p in PROTECTED):
                print(f"[ALERT] {event.event_type}: {src} @ {_now()}")

    observer = Observer()
    observer.schedule(Handler(), PROJECT_ROOT, recursive=True)
    observer.start()
    print(f"Watching protected files under {PROJECT_ROOT}. Ctrl-C to stop.")
    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    return 0


def _main(argv: List[str]) -> int:
    cmd = argv[0] if argv else "check"
    if cmd == "baseline":
        snap = write_baseline()
        print(f"Baseline written for {len(snap)} file(s) -> {BASELINE_FILE}")
        return 0
    if cmd == "check":
        report = check()
        if report["ok"]:
            print("OK — no drift in protected files.")
            return 0
        print("DRIFT DETECTED:")
        for rel in report["changed"]:
            print(f"  changed: {rel}")
        for rel in report["missing"]:
            print(f"  missing: {rel}")
        for rel in report["added"]:
            print(f"  added:   {rel}")
        return 1
    if cmd == "watch":
        return watch()
    print("usage: file_watcher.py [baseline | check | watch]")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
