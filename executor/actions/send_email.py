#!/usr/bin/env python3
"""
Send email handler. Runs only when approved.
Send-only. Approval required per send.
"""

import smtplib
import os
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get("MUSE_SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.environ.get("MUSE_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("MUSE_SMTP_USER", "")
SMTP_PASS = os.environ.get("MUSE_SMTP_PASS", "")


def run(payload):
    to = payload["to"]
    subject = payload["subject"]
    body = payload["body"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            if SMTP_USER:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return {"ok": True, "to": to, "subject": subject}
    except Exception as e:
        return {"ok": False, "error": str(e)}
