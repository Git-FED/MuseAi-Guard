#!/usr/bin/env python3
"""
Read file handler. Runs only when approved.
Read-only. Cannot write.
"""

import os


def run(payload):
    path = payload["path"]
    max_bytes = payload.get("max_bytes", 100_000)

    if not os.path.exists(path):
        return {"ok": False, "error": f"Not found: {path}"}

    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return {
            "ok": True,
            "path": path,
            "size": size,
            "truncated": size > max_bytes,
            "content": data.decode(errors="replace"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
