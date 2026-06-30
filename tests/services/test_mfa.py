"""Tests for conda executable resolution in voxkit.services.mfa.

Only the pure ``_find_conda`` resolution logic is covered here; the subprocess
wrappers shell out to MFA and conda and are exercised by integration runs.
"""

from voxkit.services import mfa


def test_find_conda_prefers_explicit_path(tmp_path, monkeypatch):
    """An existing explicit conda_path wins over PATH and the env var."""
    conda = tmp_path / "conda.exe"
    conda.write_text("")
    # Make sure the auto-detect fast path would otherwise succeed.
    monkeypatch.setattr(mfa.shutil, "which", lambda _: "conda")
    monkeypatch.delenv("VOXKIT_CONDA_PATH", raising=False)

    assert mfa._find_conda(str(conda)) == str(conda)


def test_find_conda_expands_user_home(tmp_path, monkeypatch):
    """A ``~``-prefixed configured path is expanded before the existence check."""
    conda = tmp_path / "conda.exe"
    conda.write_text("")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows home for expanduser
    monkeypatch.setattr(mfa.shutil, "which", lambda _: None)
    monkeypatch.delenv("VOXKIT_CONDA_PATH", raising=False)

    assert mfa._find_conda("~/conda.exe") == str(conda)


def test_find_conda_uses_env_var(tmp_path, monkeypatch):
    """VOXKIT_CONDA_PATH is honored when no explicit path is given."""
    conda = tmp_path / "conda.exe"
    conda.write_text("")
    monkeypatch.setattr(mfa.shutil, "which", lambda _: None)
    monkeypatch.setenv("VOXKIT_CONDA_PATH", str(conda))

    assert mfa._find_conda() == str(conda)


def test_find_conda_ignores_nonexistent_configured_path(monkeypatch):
    """A configured path that does not exist falls back to PATH detection."""
    monkeypatch.setattr(mfa.shutil, "which", lambda _: "conda")
    monkeypatch.delenv("VOXKIT_CONDA_PATH", raising=False)

    assert mfa._find_conda("/no/such/conda") == "conda"


def test_find_conda_falls_back_to_path(monkeypatch):
    """With no override, conda on PATH is returned."""
    monkeypatch.setattr(mfa.shutil, "which", lambda _: "conda")
    monkeypatch.delenv("VOXKIT_CONDA_PATH", raising=False)

    assert mfa._find_conda() == "conda"
