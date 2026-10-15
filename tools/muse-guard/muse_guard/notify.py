"""
notify.py — tell a human that something needs attention.

The approval queue is useless if nobody looks at it. This module is the "hey,
look" channel. It supports stdout (always), email (SMTP), and a generic webhook
push. It never carries secrets and never talks to the agent's network path.

Design: notifications are best-effort. If a channel fails, we do not crash the
caller — we fall back to stdout and record the failure. A notification that
takes down the system is worse than a missed notification.
"""

from __future__ import annotations

import json
import os
import smtplib
import sys
from email.message import EmailMessage
from typing import Any, Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("MUSE_GUARD_NOTIFY_CONFIG", os.path.join(HERE, "notify_config.json"))


def _load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _send_stdout(message: str) -> bool:
    print(f"[muse-guard] {message}", file=sys.stdout)
    return True


def _send_email(message: str, cfg: Dict[str, Any]) -> bool:
    email_cfg = cfg.get("email", {})
    if not email_cfg.get("to"):
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = email_cfg.get("subject", "Muse Guard notification")
        msg["From"] = email_cfg.get("from", "muse-guard@localhost")
        msg["To"] = email_cfg["to"]
        msg.set_content(message)

        host = email_cfg.get("host", "localhost")
        port = int(email_cfg.get("port", 25))
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if email_cfg.get("starttls"):
                smtp.starttls()
            user = email_cfg.get("user")
            if user:
                smtp.login(user, email_cfg.get("password", ""))
            smtp.send_message(msg)
        return True
    except Exception:
        return False


def _send_push(message: str, cfg: Dict[str, Any]) -> bool:
    push_cfg = cfg.get("push", {})
    url = push_cfg.get("url")
    if not url:
        return False
    try:
        import urllib.request

        data = json.dumps({"text": message}).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def send(message: str, channel: str = "stdout") -> bool:
    """
    Send a notification. Returns True if the requested channel succeeded.

    Always also prints to stdout so there is a local record regardless.
    """
    cfg = _load_config()
    ok = False
    if channel == "email":
        ok = _send_email(message, cfg)
    elif channel == "push":
        ok = _send_push(message, cfg)
    elif channel == "stdout":
        ok = _send_stdout(message)
    else:
        ok = _send_stdout(message)

    if channel != "stdout" and not ok:
        # Fall back so the message is not lost.
        _send_stdout(f"(fallback; {channel} failed) {message}")
    elif channel == "stdout":
        pass
    else:
        _send_stdout(message)
    return ok


def _main(argv) -> int:
    if not argv:
        print("usage: notify.py <message> [--channel stdout|email|push]")
        return 2
    channel = "stdout"
    if "--channel" in argv:
        i = argv.index("--channel")
        if i + 1 < len(argv):
            channel = argv[i + 1]
        message = " ".join(argv[:i])
    else:
        message = " ".join(argv)
    send(message, channel=channel)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
