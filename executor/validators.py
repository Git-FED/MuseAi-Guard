#!/usr/bin/env python3
"""
Rule validators. Run BEFORE execution.
Each validator returns (ok, reason).
"""

FORBIDDEN_DOMAINS = [
    "cloudflare.com",
    "workers.dev",
    "fedos.workers.dev",
    "musefm.lol",
    "lemmy.zip",
]

FORBIDDEN_ACTIONS = [
    "create_account",
    "signup",
    "register",
    "purchase",
]


def validate(intent):
    atype = intent["action_type"]
    payload = intent.get("payload", {})

    if atype in FORBIDDEN_ACTIONS:
        return False, f"Action type '{atype}' is forbidden"

    if atype == "post":
        url = payload.get("url", "")
        for domain in FORBIDDEN_DOMAINS:
            if domain in url:
                return False, f"URL contains forbidden domain: {domain}"

        account = payload.get("account", "")
        allowed = payload.get("allowed_accounts", [])
        if allowed and account not in allowed:
            return False, f"Account '{account}' not in approved list"

    if atype == "send_email":
        to = payload.get("to", "")
        for domain in FORBIDDEN_DOMAINS:
            if domain in to:
                return False, f"Recipient contains forbidden domain: {domain}"

    if atype == "write_file":
        path = payload.get("path", "")
        protected = ["persona/", "guardrails/", "proxy/credentials", ".ssh", ".gnupg"]
        for p in protected:
            if p in path:
                return False, f"Path is protected: {p}"

    return True, "ok"
