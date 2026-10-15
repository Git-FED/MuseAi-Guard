#!/usr/bin/env python3
"""
Write file handler. Runs only when approved.
Writes ONLY inside the sandboxed workspace. Never to protected paths.
"""

import os

WORKSPACE = os.environ.get("MUSE_WORKSPACE", os.path.expanduser("~/workspace"))
PROTECTED = ["persona/", "guardrails/", "proxy/credentials", ".ssh", ".gnupg", ".bashrc", ".profile"]


def run(payload):
    path = os.path.abspath(payload["path"])
    content = payload["content"]

    for p in PROTECTED:
        if p in path:
            return {"ok": False, "error": f"Protected path: {p}"}

    if not path.startswith(os.path.abspath(WORKSPACE)):
        return {"ok": False, "error": f"Outside workspace: {path}"}

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return {"ok": True, "path": path, "bytes": len(content)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
