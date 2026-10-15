#!/usr/bin/env python3
"""
Notify you when an action needs approval.
Channels: email (to a clean address), push (webhook), or stdout.
Config in config.json — secrets NOT in the repo.
"""

import json
import os
import smtplib
from email.mime.text import MIMEText

CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _config():
    if not os.path.exists(CONFIG):
        return {"channel": "stdout"}
    with open(CONFIG) as f:
        return json.load(f)


def notify(subject, body):
    cfg = _config()
    channel = cfg.get("channel", "stdout")

    if channel == "stdout":
        print(f"[NOTIFY] {subject}\n{body}\n")

    elif channel == "email":
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = cfg["email"]["from"]
        msg["To"] = cfg["email"]["to"]
        with smtplib.SMTP(cfg["email"]["smtp_host"], cfg["email"]["smtp_port"]) as s:
            s.starttls()
            s.login(cfg["email"]["from"], cfg["email"]["password"])
            s.send_message(msg)

    elif channel == "push":
        import urllib.request
        req = urllib.request.Request(
            cfg["push"]["url"],
            data=json.dumps({"title": subject, "body": body}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req)

    else:
        print(f"[NOTIFY:{channel}] {subject}\n{body}\n")


if __name__ == "__main__":
    import sys
    subject = sys.argv[1] if len(sys.argv) > 1 else "Muse"
    body = sys.argv[2] if len(sys.argv) > 2 else "Test notification"
    notify(subject, body)
