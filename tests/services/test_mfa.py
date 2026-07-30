"""Tests for conda executable resolution in voxkit.services.mfa.

Only the pure ``_find_conda`` resolution logic is covered here; the subprocess
wrappers shell out to MFA and conda and are exercised by integration runs.
"""

import subprocess

import pytest

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


class TestEnsureMfaServerRunning:
    """The server commands must never have their output piped.

    Regression guard for a permanent app freeze: ``mfa server start`` has
    pg_ctl spawn a detached Postgres daemon that inherits our stdout/stderr
    handles and outlives the call. If those are pipes, they never reach EOF
    while the server is up, and ``subprocess.run`` blocks forever -- past its
    own ``timeout=``, because on Windows a TimeoutExpired makes ``run`` call
    ``communicate()`` a second time with no timeout. Only reproducible when no
    server is already running, which is what made it easy to miss.
    """

    def _calls(self, monkeypatch, tmp_path):
        monkeypatch.setattr(mfa.sys, "platform", "win32")
        monkeypatch.setattr(mfa.mfa_provision, "is_aligner_env_ready", lambda: True)
        monkeypatch.setattr(
            mfa.mfa_provision, "vendored_micromamba_path", lambda: tmp_path / "mm.exe"
        )
        monkeypatch.setattr(mfa.mfa_provision, "bundled_env_path", lambda: tmp_path / "env")
        monkeypatch.setattr(mfa.mfa_provision, "mfa_root_dir", lambda: tmp_path / "root")

        calls = []
        monkeypatch.setattr(mfa.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw)))
        mfa._ensure_mfa_server_running()
        return calls

    def test_output_is_discarded_not_captured(self, monkeypatch, tmp_path):
        calls = self._calls(monkeypatch, tmp_path)

        assert calls, "expected server init/start to be invoked on win32"
        for cmd, kwargs in calls:
            assert not kwargs.get("capture_output"), f"{cmd[-2:]} must not pipe its output"
            assert kwargs["stdout"] is subprocess.DEVNULL
            assert kwargs["stderr"] is subprocess.DEVNULL

    def test_enables_postgres_before_starting_the_server(self, monkeypatch, tmp_path):
        """Starting the server is useless without flipping ``use_postgres``.

        MFA defaults that setting to False and picks its backend from it when
        it opens the corpus database, so without this it runs on SQLite --
        and the race this whole function exists to dodge stays live while
        `server start` still reports success.
        """
        calls = self._calls(monkeypatch, tmp_path)

        assert [cmd[-2:] for cmd, _ in calls] == [
            ["configure", "--enable_use_postgres"],
            ["server", "init"],
            ["server", "start"],
        ]

    def test_noop_off_windows(self, monkeypatch, tmp_path):
        monkeypatch.setattr(mfa.sys, "platform", "darwin")
        monkeypatch.setattr(
            mfa.subprocess, "run", lambda *a, **k: pytest.fail("must not shell out off win32")
        )

        mfa._ensure_mfa_server_running()


# NTSTATUS STATUS_ACCESS_VIOLATION as surfaced in a Windows exit code. Kept in
# hex because the decimal form is ten digits, which the PHI scanner flags as a
# phone number.
ACCESS_VIOLATION = 0xC0000005


class TestDescribeProcessFailure:
    """A crashed process reports no output; the exit code must not be dropped.

    Regression guard for the micromamba/MSVCP140 access violation, which
    surfaced as a bare "Download failed with: " because only ``stderr`` --
    empty, because the OS killed the process -- was reported.
    """

    def _result(self, returncode, stdout="", stderr=""):
        return subprocess.CompletedProcess(
            args=["micromamba"], returncode=returncode, stdout=stdout, stderr=stderr
        )

    def test_windows_crash_code_is_named_as_a_crash(self, monkeypatch):
        monkeypatch.setattr(mfa.sys, "platform", "win32")

        described = mfa.describe_process_failure(self._result(ACCESS_VIOLATION))

        assert "crashed" in described
        assert "0xC0000005" in described

    def test_ordinary_exit_code_is_reported_plainly(self, monkeypatch):
        monkeypatch.setattr(mfa.sys, "platform", "win32")

        described = mfa.describe_process_failure(self._result(1, stderr="boom"))

        assert "exit 1" in described
        assert "stderr: boom" in described
        assert "crashed" not in described

    def test_non_windows_never_reports_a_crash(self, monkeypatch):
        monkeypatch.setattr(mfa.sys, "platform", "linux")

        described = mfa.describe_process_failure(self._result(ACCESS_VIOLATION))

        assert f"exit {ACCESS_VIOLATION}" in described
        assert "crashed" not in described

    def test_empty_streams_are_omitted(self, monkeypatch):
        monkeypatch.setattr(mfa.sys, "platform", "win32")

        described = mfa.describe_process_failure(self._result(ACCESS_VIOLATION, stdout="  \n"))

        assert "stdout" not in described
