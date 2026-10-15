"""
test_executor.py — the executor is the only thing that actually acts, and it
runs the validators first.

Two layers are covered here:
  1. validators.validate() — the pure rule checks (forbidden actions, forbidden
     domains, protected paths). These are the tripwires.
  2. executor.run_once() — reads approved intents, skips anything already run,
     blocks anything the validators reject, and logs every outcome.
"""

from __future__ import annotations

import importlib.util
import json
import os

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Layer 1: validators
# ---------------------------------------------------------------------------

def test_forbidden_action_is_rejected(validators_mod):
    for action in validators_mod.FORBIDDEN_ACTIONS:
        ok, reason = validators_mod.validate({"action_type": action, "payload": {}})
        assert ok is False
        assert "forbidden" in reason.lower()


def test_benign_action_is_allowed(validators_mod):
    ok, reason = validators_mod.validate(
        {"action_type": "post", "payload": {"url": "https://bsky.social/xrpc/x"}}
    )
    assert ok is True
    assert reason == "ok"


def test_post_to_forbidden_domain_is_rejected(validators_mod):
    for domain in validators_mod.FORBIDDEN_DOMAINS:
        ok, reason = validators_mod.validate(
            {"action_type": "post", "payload": {"url": f"https://{domain}/evil"}}
        )
        assert ok is False, f"{domain} should be forbidden"
        assert "forbidden domain" in reason.lower()


def test_email_to_forbidden_domain_is_rejected(validators_mod):
    ok, reason = validators_mod.validate(
        {"action_type": "send_email", "payload": {"to": "someone@musefm.lol"}}
    )
    assert ok is False
    assert "musefm.lol" in reason


def test_email_to_normal_domain_is_allowed(validators_mod):
    ok, _ = validators_mod.validate(
        {"action_type": "send_email", "payload": {"to": "friend@example.com"}}
    )
    assert ok is True


def test_post_from_unapproved_account_is_rejected(validators_mod):
    ok, reason = validators_mod.validate(
        {
            "action_type": "post",
            "payload": {
                "url": "https://bsky.social/xrpc/x",
                "account": "muse3",
                "allowed_accounts": ["muse_guard"],
            },
        }
    )
    assert ok is False
    assert "not in approved list" in reason


def test_post_from_approved_account_is_allowed(validators_mod):
    ok, _ = validators_mod.validate(
        {
            "action_type": "post",
            "payload": {
                "url": "https://bsky.social/xrpc/x",
                "account": "muse_guard",
                "allowed_accounts": ["muse_guard"],
            },
        }
    )
    assert ok is True


def test_write_to_protected_path_is_rejected(validators_mod):
    for protected in ["persona/SOUL.md", "guardrails/kill_switch/state.json",
                      "proxy/credentials/bluesky.json", "/root/.ssh/id_rsa",
                      "/home/x/.gnupg/secring.gpg"]:
        ok, reason = validators_mod.validate(
            {"action_type": "write_file", "payload": {"path": protected}}
        )
        assert ok is False, f"{protected} should be protected"
        assert "protected" in reason.lower()


def test_write_to_ordinary_path_is_allowed(validators_mod):
    ok, _ = validators_mod.validate(
        {"action_type": "write_file", "payload": {"path": "memory/daily/2026-10-15.md"}}
    )
    assert ok is True


# ---------------------------------------------------------------------------
# Layer 2: executor
# ---------------------------------------------------------------------------

@pytest.fixture
def exec_mod(tmp_path, monkeypatch):
    """Load the executor with its paths redirected into a temp sandbox."""
    path = os.path.join(PROJECT_ROOT, "executor", "executor.py")
    spec = importlib.util.spec_from_file_location("proj_executor", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    approved = tmp_path / "approved.jsonl"
    executed = tmp_path / "executed.jsonl"
    actions = tmp_path / "actions"
    actions.mkdir()
    monkeypatch.setattr(mod, "APPROVED", str(approved))
    monkeypatch.setattr(mod, "EXECUTED", str(executed))
    monkeypatch.setattr(mod, "ACTIONS", str(actions))
    return mod


def _write_approved(path, intent):
    with open(path, "a") as fh:
        fh.write(json.dumps(intent) + "\n")


def _read_executed(path):
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def test_executor_blocks_forbidden_action(exec_mod):
    """An approved intent that violates a rule is blocked, not run."""
    _write_approved(exec_mod.APPROVED, {
        "id": "intent-1",
        "action_type": "create_account",
        "payload": {"service": "bluesky"},
    })
    exec_mod.run_once()

    log = _read_executed(exec_mod.EXECUTED)
    assert len(log) == 1
    assert log[0]["result"]["ok"] is False
    assert "validator" in log[0]["result"]["error"]


def test_executor_runs_benign_action(exec_mod):
    """A benign approved intent with a handler gets executed once."""
    handler = os.path.join(exec_mod.ACTIONS, "post.py")
    with open(handler, "w") as fh:
        fh.write(
            "def run(payload):\n"
            "    return {'ok': True, 'posted': payload.get('url')}\n"
        )
    _write_approved(exec_mod.APPROVED, {
        "id": "intent-2",
        "action_type": "post",
        "payload": {"url": "https://bsky.social/xrpc/x"},
    })
    exec_mod.run_once()

    log = _read_executed(exec_mod.EXECUTED)
    assert len(log) == 1
    assert log[0]["result"]["ok"] is True


def test_executor_does_not_run_twice(exec_mod):
    """Already-executed intents are skipped on subsequent passes."""
    handler = os.path.join(exec_mod.ACTIONS, "post.py")
    with open(handler, "w") as fh:
        fh.write("def run(payload):\n    return {'ok': True}\n")
    _write_approved(exec_mod.APPROVED, {
        "id": "intent-3",
        "action_type": "post",
        "payload": {"url": "https://bsky.social/xrpc/x"},
    })
    exec_mod.run_once()
    exec_mod.run_once()  # second pass must be a no-op

    log = _read_executed(exec_mod.EXECUTED)
    assert len(log) == 1


def test_executor_missing_handler_is_logged(exec_mod):
    """An approved intent with no handler fails gracefully and is logged."""
    _write_approved(exec_mod.APPROVED, {
        "id": "intent-4",
        "action_type": "read_file",
        "payload": {"path": "memory/daily/2026-10-15.md"},
    })
    exec_mod.run_once()

    log = _read_executed(exec_mod.EXECUTED)
    assert len(log) == 1
    assert log[0]["result"]["ok"] is False
    assert "handler" in log[0]["result"]["error"].lower()
