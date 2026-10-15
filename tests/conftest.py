"""
conftest.py — fixtures for the project-level integration tests.

These tests exercise the *project* components (guardrails/, proxy/, executor/,
logger/) together, as they are laid out in the repo — as opposed to
tools/muse-tests, which tests the standalone packaged tools.

The project components use module-level path constants, so the fixtures here
load each component by file path (avoiding import-name collisions) and
monkeypatch its path globals to point at a temp directory. The suite therefore
never mutates the real project.
"""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def load_module(unique_name: str, rel_path: str):
    """Load a Python module from a path under the project root."""
    path = os.path.join(PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(unique_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def kill_mod(tmp_path, monkeypatch):
    """The project kill switch, redirected to a temp state file."""
    mod = load_module("proj_kill_switch", "guardrails/kill_switch/kill_switch.py")
    monkeypatch.setattr(mod, "STATE", str(tmp_path / "kill_state.json"))
    return mod


@pytest.fixture
def queue_mod(tmp_path, monkeypatch):
    """The project approval queue, redirected to temp files."""
    mod = load_module("proj_queue", "guardrails/approval_queue/queue.py")
    monkeypatch.setattr(mod, "PENDING", str(tmp_path / "pending.jsonl"))
    monkeypatch.setattr(mod, "APPROVED", str(tmp_path / "approved.jsonl"))
    monkeypatch.setattr(mod, "DENIED", str(tmp_path / "denied.jsonl"))
    return mod


@pytest.fixture
def proxy_mod(tmp_path, monkeypatch):
    """The project egress proxy, redirected to a temp allowlist + creds + log."""
    mod = load_module("proj_proxy", "proxy/egress_proxy.py")
    monkeypatch.setattr(mod, "ALLOWLIST", str(tmp_path / "allowlist.json"))
    monkeypatch.setattr(mod, "CREDS", str(tmp_path / "credentials"))
    monkeypatch.setattr(mod, "LOG", str(tmp_path / "request_log.jsonl"))
    return mod


@pytest.fixture
def log_mod(tmp_path, monkeypatch):
    """The project action log, redirected to a temp log file."""
    mod = load_module("proj_action_log", "logger/action_log.py")
    monkeypatch.setattr(mod, "LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(mod, "LOG_FILE", str(tmp_path / "logs" / "actions.jsonl"))
    return mod


@pytest.fixture
def validators_mod():
    """The project validators module."""
    return load_module("proj_validators", "executor/validators.py")
