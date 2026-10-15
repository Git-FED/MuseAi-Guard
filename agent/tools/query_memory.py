#!/usr/bin/env python3
"""
query_memory.py — Read-only access to the agent's memory.

Memory is split into:
  * memory/daily/    — one file per day, dated.
  * memory/topics/   — durable topic notes (projects, finances, accounts, people).
  * memory/audit/    — incident records.

The agent can read all of it and can *append* to today's daily note, but it
cannot rewrite history. This tool exposes reads and a narrowly-scoped append.

Usage:
    from agent.tools import query_memory as mem
    mem.today()                      # read today's note (or empty string)
    mem.topic("projects")            # read a topic note
    mem.append_today("did a thing")  # append a line to today's note
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))
MEMORY_DIR = os.path.join(PROJECT_ROOT, "memory")
DAILY_DIR = os.path.join(MEMORY_DIR, "daily")
TOPICS_DIR = os.path.join(MEMORY_DIR, "topics")
AUDIT_DIR = os.path.join(MEMORY_DIR, "audit")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def today() -> str:
    """Read today's daily note (empty string if none yet)."""
    return _read(os.path.join(DAILY_DIR, f"{_today()}.md"))


def daily(date: str) -> str:
    """Read a specific day's note, e.g. daily('2026-10-15')."""
    return _read(os.path.join(DAILY_DIR, f"{date}.md"))


def topic(name: str) -> str:
    """Read a topic note by name (without .md), e.g. topic('projects')."""
    return _read(os.path.join(TOPICS_DIR, f"{name}.md"))


def audit(name: str) -> str:
    """Read an audit record by name (without .md)."""
    return _read(os.path.join(AUDIT_DIR, f"{name}.md"))


def list_topics() -> List[str]:
    if not os.path.isdir(TOPICS_DIR):
        return []
    return sorted(f[:-3] for f in os.listdir(TOPICS_DIR) if f.endswith(".md"))


def list_daily() -> List[str]:
    if not os.path.isdir(DAILY_DIR):
        return []
    return sorted(f[:-3] for f in os.listdir(DAILY_DIR) if f.endswith(".md"))


def append_today(line: str) -> None:
    """
    Append a line to today's daily note. Append-only — the agent cannot rewrite
    or delete past entries. If the file doesn't exist, it is created with a
    header.
    """
    os.makedirs(DAILY_DIR, exist_ok=True)
    path = os.path.join(DAILY_DIR, f"{_today()}.md")
    new_file = not os.path.exists(path)
    ts = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    with open(path, "a", encoding="utf-8") as fh:
        if new_file:
            fh.write(f"# {_today()}\n\n")
        fh.write(f"- [{ts}] {line}\n")


def _main(argv) -> int:
    if not argv:
        print("usage: query_memory.py [today | topic <name> | daily <date> | topics]")
        return 2
    cmd = argv[0]
    if cmd == "today":
        print(today() or "(empty)")
    elif cmd == "topic" and len(argv) > 1:
        print(topic(argv[1]) or "(empty)")
    elif cmd == "daily" and len(argv) > 1:
        print(daily(argv[1]) or "(empty)")
    elif cmd == "topics":
        print("\n".join(list_topics()))
    else:
        print("usage: query_memory.py [today | topic <name> | daily <date> | topics]")
        return 2
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
