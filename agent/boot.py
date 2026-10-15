#!/usr/bin/env python3
"""
boot.py — Assemble the agent's system prompt from the locked persona files.

The agent does not get to invent who it is at runtime. On every boot, this
script reads the five persona files and concatenates them into a single system
prompt. If any of them is missing or unreadable, boot fails closed — a Muse that
can't read its own rules does not get to run.

This is the "constitution load" step. It is deliberately boring and hard to
subvert: read five files, in a fixed order, or refuse to start.

Usage:
  python agent/boot.py            # print the assembled system prompt
  python agent/boot.py --check    # verify all persona files exist and are readable
"""

from __future__ import annotations

import os
import sys
from typing import List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
PERSONA_DIR = os.path.join(PROJECT_ROOT, "persona")

# Fixed load order. Identity first (who), then soul (why), then rules (bounds),
# then system (how), then memory (context). Order matters for the model.
PERSONA_FILES = [
    "IDENTITY.md",
    "SOUL.md",
    "RULES.md",
    "SYSTEM.md",
    "MEMORY.md",
]


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read().strip()


def load_persona() -> Tuple[bool, List[str], List[str]]:
    """
    Attempt to load all persona files.

    Returns (ok, loaded_names, missing_names).
    """
    loaded: List[str] = []
    missing: List[str] = []
    for name in PERSONA_FILES:
        path = os.path.join(PERSONA_DIR, name)
        if os.path.exists(path) and os.access(path, os.R_OK):
            loaded.append(name)
        else:
            missing.append(name)
    return (not missing), loaded, missing


def build_system_prompt() -> str:
    """Concatenate the persona files into one system prompt. Fails closed."""
    ok, loaded, missing = load_persona()
    if not ok:
        raise RuntimeError(
            "Refusing to boot: persona files missing/unreadable: "
            + ", ".join(missing)
        )

    parts: List[str] = [
        "# === MUSE GUARD SYSTEM PROMPT (assembled at boot) ===",
        "# This prompt is generated from locked, read-only files. You cannot",
        "# change it. If you believe a rule is wrong, propose a change to your",
        "# human — do not act around it.",
        "",
    ]
    for name in PERSONA_FILES:
        path = os.path.join(PERSONA_DIR, name)
        parts.append(f"\n\n===== BEGIN {name} =====")
        parts.append(_read(path))
        parts.append(f"===== END {name} =====")
    return "\n".join(parts)


def _main(argv: List[str]) -> int:
    if "--check" in argv:
        ok, loaded, missing = load_persona()
        if ok:
            print(f"OK — loaded {len(loaded)} persona files: {', '.join(loaded)}")
            return 0
        print(f"MISSING: {', '.join(missing)}")
        return 1
    try:
        print(build_system_prompt())
    except RuntimeError as exc:
        print(f"BOOT FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
