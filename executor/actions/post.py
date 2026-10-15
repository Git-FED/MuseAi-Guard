#!/usr/bin/env python3
"""
Post handler. Runs only when approved.
Uses the proxy. Never touches credentials directly.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "proxy"))
from egress_proxy import forward  # noqa: E402

ENDPOINTS = {
    "bluesky":  ("POST", "https://bsky.social/xrpc/com.atproto.repo.createRecord"),
    "mastodon": ("POST", "https://mastodon.social/api/v1/statuses"),
    "x":        ("POST", "https://api.twitter.com/2/tweets"),
    "discord":  ("POST", "https://discord.com/api/v10/channels/CHANNEL/messages"),
    "pixelfed": ("POST", "https://pixelfed.social/api/v1/statuses"),
}


def run(payload):
    platform = payload["platform"]
    content = payload["content"]
    cred = payload.get("cred_file", platform)

    if platform not in ENDPOINTS:
        return {"ok": False, "error": f"Unknown platform: {platform}"}

    method, url = ENDPOINTS[platform]
    try:
        status, body = forward(method, url, payload={"content": content}, cred_name=cred)
        return {"ok": 200 <= status < 300, "status": status, "response": body[:500].decode(errors="replace")}
    except Exception as e:
        return {"ok": False, "error": str(e)}
