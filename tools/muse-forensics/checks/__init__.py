"""
checks — individual forensic probes for a (possibly dead) box.

Each module exposes `run(out_dir) -> dict` where the dict is a finding report:

    {
      "name": "cron",
      "ok": True,                 # True = nothing alarming found
      "summary": "one-line summary",
      "findings": [ ... ],        # list of strings or dicts
      "artifacts": [ ... ]        # files written under out_dir
    }

The probes are read-only. They never modify the box. They are written to be
safe to run on a machine you are investigating, including one that is only
mounted read-only.
"""

from . import (  # noqa: F401
    cloud,
    credentials,
    cron,
    files,
    history,
    logs,
    ssh,
    systemd,
)

ALL_CHECKS = [
    cron,
    systemd,
    history,
    ssh,
    files,
    credentials,
    logs,
    cloud,
]

__all__ = ["ALL_CHECKS", "cron", "systemd", "history", "ssh", "files",
           "credentials", "logs", "cloud"]
