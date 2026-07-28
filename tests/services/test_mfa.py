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


class TestMfaInvocation:
    """_mfa_invocation() must prefer the bundled environment when it's ready,
    and otherwise fall back to exactly the pre-bundling conda behavior."""

    def test_falls_back_to_conda_when_bundle_not_ready(self, monkeypatch):
        monkeypatch.setattr(mfa.mfa_provision, "is_aligner_env_ready", lambda: False)
        monkeypatch.setattr(mfa.shutil, "which", lambda _: "conda")
        monkeypatch.delenv("VOXKIT_CONDA_PATH", raising=False)

        prefix, extra_env = mfa._mfa_invocation()

        assert prefix == ["conda", "run", "-n", "aligner", "mfa"]
        assert extra_env == {}

    def test_prefers_bundled_env_when_ready(self, monkeypatch, tmp_path):
        env_path = tmp_path / "mfa-env"
        micromamba = tmp_path / "micromamba.exe"
        mfa_root = tmp_path / "mfa-root"

        monkeypatch.setattr(mfa.mfa_provision, "is_aligner_env_ready", lambda: True)
        monkeypatch.setattr(mfa.mfa_provision, "vendored_micromamba_path", lambda: micromamba)
        monkeypatch.setattr(mfa.mfa_provision, "bundled_env_path", lambda: env_path)
        monkeypatch.setattr(mfa.mfa_provision, "mfa_root_dir", lambda: mfa_root)

        prefix, extra_env = mfa._mfa_invocation()

        assert prefix == [
            str(micromamba),
            "run",
            "-p",
            str(env_path),
            str(env_path / "python.exe"),
            str(env_path / "Scripts" / "mfa-script.py"),
        ]
        assert extra_env == {"MFA_ROOT_DIR": str(mfa_root)}

    def test_bundled_env_takes_precedence_over_explicit_conda_path(self, monkeypatch, tmp_path):
        """A user-configured conda_path is irrelevant once the bundle is ready --
        the whole point is that most users never need to touch that setting."""
        env_path = tmp_path / "mfa-env"
        monkeypatch.setattr(mfa.mfa_provision, "is_aligner_env_ready", lambda: True)
        monkeypatch.setattr(
            mfa.mfa_provision, "vendored_micromamba_path", lambda: tmp_path / "mm.exe"
        )
        monkeypatch.setattr(mfa.mfa_provision, "bundled_env_path", lambda: env_path)
        monkeypatch.setattr(mfa.mfa_provision, "mfa_root_dir", lambda: tmp_path / "mfa-root")

        prefix, _ = mfa._mfa_invocation(conda_path="/some/explicit/conda")

        assert "conda" not in prefix[0]
