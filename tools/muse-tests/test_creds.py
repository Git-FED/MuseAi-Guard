"""
test_creds.py — prove credentials are stored safely and never leak.

The theme: 0600 perms, no path escape, no value in the redaction helper.
"""

from __future__ import annotations

import os

import pytest

from muse_proxy import creds


def test_put_and_get(isolated_env):
    creds.put("bluesky", "s3cr3t")
    assert creds.get("bluesky") == "s3cr3t"


def test_file_permissions_are_600(isolated_env):
    creds.put("bluesky", "s3cr3t")
    path = os.path.join(str(isolated_env["creds_dir"]), "bluesky")
    mode = os.stat(path).st_mode & 0o777
    assert mode == 0o600


def test_check_permissions_clean(isolated_env):
    creds.put("bluesky", "s3cr3t")
    assert creds.check_permissions() == []


def test_check_permissions_flags_world_readable(isolated_env):
    creds.put("bluesky", "s3cr3t")
    path = os.path.join(str(isolated_env["creds_dir"]), "bluesky")
    os.chmod(path, 0o644)
    problems = creds.check_permissions()
    assert any("bluesky" in p for p in problems)


def test_path_escape_rejected(isolated_env):
    with pytest.raises(ValueError):
        creds.put("../escape", "x")
    with pytest.raises(ValueError):
        creds.put("a/b", "x")


def test_missing_credential_returns_none(isolated_env):
    assert creds.get("nope") is None


def test_redact_hides_value(isolated_env):
    creds.put("bluesky", "s3cr3t")
    r = creds.redact("bluesky")
    assert "s3cr3t" not in r
    assert "bluesky" in r


def test_multi_field_credential(isolated_env):
    creds.put_fields("smtp", {"host": "mail.example", "user": "me", "password": "pw"})
    fields = creds.get_fields("smtp")
    assert fields["host"] == "mail.example"
    assert fields["password"] == "pw"


def test_list_names_excludes_tmp(isolated_env):
    creds.put("bluesky", "x")
    names = creds.list_names()
    assert "bluesky" in names
    assert not any(n.endswith(".tmp") for n in names)
