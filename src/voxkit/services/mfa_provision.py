"""MFA environment provisioning via a vendored, activation-preserving micromamba.

Bundles a small static `micromamba` binary plus a pinned, platform-specific
explicit lockfile (see `config/mfa-env/`) so VoxKit can materialize its own
"aligner" environment on first use, without requiring the user to install
conda or run any terminal commands themselves. `services/mfa.py` prefers
this bundled environment when it's ready, falling back to the existing
user-managed conda + `aligner` env mechanism otherwise.

See `docs/BUILD.md` for how to regenerate the lockfile when MFA's pinned
version changes, and where the vendored micromamba binary comes from.

API
---
- **bundled_env_path**: Where VoxKit's own managed aligner environment lives
- **mfa_root_dir**: Isolated MFA_ROOT_DIR for the bundled environment
- **is_aligner_env_ready**: Whether the bundled environment has been provisioned
- **provision_aligner_env**: Create the bundled environment from the pinned lockfile
"""

import subprocess
import sys
from pathlib import Path

from voxkit.storage.utils import get_storage_root

_PLATFORM_TAGS = {"win32": "win-64"}


def _no_window() -> dict:
    """Return creationflags to suppress console windows on Windows."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def _bundle_root() -> Path:
    """Root directory containing the vendored micromamba binary and lockfiles.

    Resolves relative to the frozen PyInstaller bundle (`sys._MEIPASS`) when
    running as a built app, or the repo root in dev.
    """
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # src/voxkit/services/mfa_provision.py -> repo root is 4 parents up.
    return Path(__file__).resolve().parents[3]


def vendored_micromamba_path() -> Path:
    """Path to the vendored micromamba binary for the current platform."""
    name = "micromamba.exe" if sys.platform == "win32" else "micromamba"
    return _bundle_root() / "vendor" / "micromamba" / name


def lockfile_path() -> Path | None:
    """Path to the pinned aligner-environment lockfile for the current platform.

    Returns None on platforms without a bundled lockfile yet (v1 ships
    win-64 only) -- callers should treat that as "bundled provisioning isn't
    available here" rather than an error, falling back to the existing
    user-managed conda mechanism.
    """
    platform_tag = _PLATFORM_TAGS.get(sys.platform)
    if platform_tag is None:
        return None
    path = _bundle_root() / "config" / "mfa-env" / f"aligner-{platform_tag}.lock"
    return path if path.exists() else None


def bundled_env_path() -> Path:
    """Fixed location where VoxKit provisions its own managed aligner environment."""
    return get_storage_root() / "mfa-env"


def mfa_root_dir() -> Path:
    """Fixed, short MFA_ROOT_DIR to use with the bundled environment.

    MFA's global config/database/working-data directory defaults to
    ``~/Documents/MFA``. Pointing the bundled environment at a VoxKit-owned
    directory instead keeps it fully isolated from any pre-existing
    conda + MFA setup a user may already have -- avoids a
    ``global_config.yaml`` version mismatch between the two (confirmed via
    real-world testing: a fresh MFA 3.4.1 environment couldn't parse a
    config written by an older MFA version), and keeps the path short
    enough to stay under PostgreSQL's 107-byte Unix-domain-socket path
    limit (also confirmed via real-world testing -- a deeply nested root
    directory made ``mfa server init`` fail outright).
    """
    return get_storage_root() / "mfa-root"


def is_aligner_env_ready() -> bool:
    """Whether the bundled aligner environment has already been provisioned."""
    return (bundled_env_path() / "Scripts" / "mfa-script.py").exists()


def provision_aligner_env() -> None:
    """Create the bundled aligner environment from the pinned lockfile.

    Safe to re-run after a failure or interruption: micromamba caches
    downloaded packages, so a re-run resumes from cache rather than
    restarting the full download.

    Raises:
        FileNotFoundError: If the vendored micromamba binary or lockfile is missing.
        subprocess.CalledProcessError: If provisioning fails.
    """
    micromamba = vendored_micromamba_path()
    if not micromamba.exists():
        raise FileNotFoundError(f"Vendored micromamba binary not found at {micromamba}")

    lockfile = lockfile_path()
    if lockfile is None:
        raise FileNotFoundError(
            f"No bundled MFA environment lockfile for platform {sys.platform!r}"
        )

    env_path = bundled_env_path()
    env_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [str(micromamba), "create", "-p", str(env_path), "--file", str(lockfile), "-y"]
    subprocess.run(cmd, check=True, capture_output=True, text=True, **_no_window())
