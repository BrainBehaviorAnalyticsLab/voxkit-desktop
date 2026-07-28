"""Tests for the pure path/readiness logic in voxkit.services.mfa_provision.

provision_aligner_env() itself shells out to micromamba and downloads
packages -- it is exercised by a manual integration run, not this suite.
"""

import sys

from voxkit.services import mfa_provision


def test_bundled_env_path_is_under_storage_root(monkeypatch, tmp_path):
    monkeypatch.setattr(mfa_provision, "get_storage_root", lambda: tmp_path)

    assert mfa_provision.bundled_env_path() == tmp_path / "mfa-env"


def test_mfa_root_dir_is_under_storage_root_and_distinct_from_env(monkeypatch, tmp_path):
    monkeypatch.setattr(mfa_provision, "get_storage_root", lambda: tmp_path)

    assert mfa_provision.mfa_root_dir() == tmp_path / "mfa-root"
    assert mfa_provision.mfa_root_dir() != mfa_provision.bundled_env_path()


def test_is_aligner_env_ready_false_when_marker_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(mfa_provision, "get_storage_root", lambda: tmp_path)

    assert mfa_provision.is_aligner_env_ready() is False


def test_is_aligner_env_ready_true_when_marker_present(monkeypatch, tmp_path):
    monkeypatch.setattr(mfa_provision, "get_storage_root", lambda: tmp_path)
    marker = tmp_path / "mfa-env" / "Scripts" / "mfa-script.py"
    marker.parent.mkdir(parents=True)
    marker.write_text("")

    assert mfa_provision.is_aligner_env_ready() is True


def test_lockfile_path_none_on_platform_without_a_bundled_lockfile(monkeypatch):
    monkeypatch.setattr(sys, "platform", "some-unsupported-platform")

    assert mfa_provision.lockfile_path() is None


def test_lockfile_path_none_when_file_does_not_exist(monkeypatch, tmp_path):
    monkeypatch.setattr(mfa_provision, "_bundle_root", lambda: tmp_path)
    monkeypatch.setattr(sys, "platform", "win32")

    assert mfa_provision.lockfile_path() is None


def test_lockfile_path_resolves_when_present(monkeypatch, tmp_path):
    monkeypatch.setattr(mfa_provision, "_bundle_root", lambda: tmp_path)
    monkeypatch.setattr(sys, "platform", "win32")
    lockfile = tmp_path / "config" / "mfa-env" / "aligner-win-64.lock"
    lockfile.parent.mkdir(parents=True)
    lockfile.write_text("@EXPLICIT\n")

    assert mfa_provision.lockfile_path() == lockfile


def test_vendored_micromamba_path_uses_windows_name_on_win32(monkeypatch, tmp_path):
    monkeypatch.setattr(mfa_provision, "_bundle_root", lambda: tmp_path)
    monkeypatch.setattr(sys, "platform", "win32")

    expected = tmp_path / "vendor" / "micromamba" / "micromamba.exe"
    assert mfa_provision.vendored_micromamba_path() == expected


def test_vendored_micromamba_path_uses_unix_name_elsewhere(monkeypatch, tmp_path):
    monkeypatch.setattr(mfa_provision, "_bundle_root", lambda: tmp_path)
    monkeypatch.setattr(sys, "platform", "darwin")

    expected = tmp_path / "vendor" / "micromamba" / "micromamba"
    assert mfa_provision.vendored_micromamba_path() == expected


def test_provision_aligner_env_raises_when_micromamba_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(mfa_provision, "vendored_micromamba_path", lambda: tmp_path / "nope.exe")

    try:
        mfa_provision.provision_aligner_env()
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError as exc:
        assert "micromamba" in str(exc).lower()


def test_provision_aligner_env_raises_when_lockfile_missing(monkeypatch, tmp_path):
    micromamba = tmp_path / "micromamba.exe"
    micromamba.write_text("")
    monkeypatch.setattr(mfa_provision, "vendored_micromamba_path", lambda: micromamba)
    monkeypatch.setattr(mfa_provision, "lockfile_path", lambda: None)

    try:
        mfa_provision.provision_aligner_env()
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError as exc:
        assert "lockfile" in str(exc).lower()
