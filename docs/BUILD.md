# Building VoxKit and the bundled MFA environment

This covers two things: how VoxKit's own executable is built, and how it
provisions the Montreal Forced Aligner (MFA) so end users never have to
install conda or run a conda command themselves.

## Table of Contents

- [How MFA setup works for end users](#how-mfa-setup-works-for-end-users)
- [Regenerating the pinned MFA environment lockfile](#regenerating-the-pinned-mfa-environment-lockfile)
- [The vendored micromamba binary](#the-vendored-micromamba-binary)
- [Building the VoxKit executable](#building-the-voxkit-executable)
- [Troubleshooting / the conda-path fallback](#troubleshooting--the-conda-path-fallback)

---

## How MFA setup works for end users

VoxKit ships a small (~10MB) static [micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html)
binary (`vendor/micromamba/`) plus a pinned, platform-specific *explicit*
lockfile (`config/mfa-env/aligner-<platform>.lock`) describing an environment
equivalent to `conda create -n aligner -c conda-forge montreal-forced-aligner`.

On first launch, `config/startup_config.py`'s `startup_routine()` calls
`voxkit.services.mfa_provision.provision_aligner_env()`, which runs:

```
micromamba create -p ~/.voxkit/mfa-env --file config/mfa-env/aligner-win-64.lock -y
```

This installs the exact pinned package set directly from URLs, with no
dependency solve step -- fast, reproducible, and safe to just re-run if it's
interrupted (micromamba caches downloaded packages). It requires one
~1-2GB download, same order of magnitude as `conda create` would need
anyway, just automated and without a terminal.

`voxkit.services.mfa._mfa_invocation()` prefers this bundled environment
whenever it's ready. If a user already has their own working conda +
`aligner` environment (e.g. from before this feature existed, or via the
"Conda Path" setting), that continues to work exactly as before with zero
behavior change -- the bundled environment is purely additive.

If first-run provisioning ever fails (e.g. a network hiccup mid-download),
it does **not** block the rest of app setup or W2TG usage. It also isn't
retried automatically on next launch (unlike the app's other first-run
downloads) -- retry it manually via the **"Repair/Reinstall MFA
Environment"** button on the Generate Alignments page.

### Real-world gotchas discovered building this (read before touching `_mfa_invocation`)

These were all found via actual hands-on testing while building this
feature, not theoretical:

- **The `mfa`/`mfa.exe` entry-point stub can fail to launch** ("failed to
  create process") on at least one real Windows machine, even inside a
  correctly-activated `micromamba run -p <env>` environment. Invoking
  `python <env>/Scripts/mfa-script.py` directly (still via `micromamba run
  -p <env>`, so the environment is still activated) works reliably where the
  stub does not. `_mfa_invocation()` uses this form for the bundled
  environment specifically for this reason -- don't change it back to
  calling `mfa`/`mfa.exe` without re-verifying on a real machine.
- **Environment activation matters for native libraries.** Calling
  `<env>/python.exe` *without* going through `micromamba run -p <env>` first
  breaks DLL loading for `libsndfile`/Kaldi (the env's `Library/bin` isn't
  on the search path). Always invoke through `micromamba run -p <env>`.
- **MFA's global config/database directory must be isolated.** MFA defaults
  to `~/Documents/MFA` for its global config and Postgres data. A
  pre-existing config written by a different MFA version can fail to load
  under a newer version's stricter YAML loader (confirmed: a real
  `global_config.yaml` from an older MFA install couldn't be read by a
  fresh 3.4.1 environment). Setting the `MFA_ROOT_DIR` environment variable
  to a VoxKit-owned directory (`~/.voxkit/mfa-root`, via
  `mfa_provision.mfa_root_dir()`) keeps the bundled environment's MFA state
  fully separate from any pre-existing user setup.
- **PostgreSQL's Unix-domain socket path has a hard 107-byte limit.**
  `mfa server init`/`start` (the Windows SQLite-race workaround) fails
  outright with a deeply nested `MFA_ROOT_DIR` -- confirmed via
  reproduction. `~/.voxkit/mfa-root` is short enough to be safe for the
  vast majority of users, but be aware of this limit if you ever change
  where that directory lives.

## Regenerating the pinned MFA environment lockfile

Only needed when bumping the pinned MFA version, or adding a new platform.
This is a developer maintenance task, not part of VoxKit's own release
process -- it does not require conda or conda-lock, just the vendored
micromamba binary.

```powershell
# From the repo root, using the already-vendored micromamba binary:
.\vendor\micromamba\micromamba.exe create -p .\_tmp-aligner -c conda-forge montreal-forced-aligner -y

# Export the explicit, pinned lockfile:
.\vendor\micromamba\micromamba.exe env export -p .\_tmp-aligner --explicit --md5 `
    | Out-File -Encoding ascii config\mfa-env\aligner-win-64.lock

# Validate the round-trip before committing -- create a fresh env from just
# the lockfile (no solve, pure download) and confirm `mfa` actually works:
.\vendor\micromamba\micromamba.exe create -p .\_tmp-aligner-verify --file config\mfa-env\aligner-win-64.lock -y
$env:MFA_ROOT_DIR = "C:\_tmp-mfa-root"
.\vendor\micromamba\micromamba.exe run -p .\_tmp-aligner-verify python .\_tmp-aligner-verify\Scripts\mfa-script.py version

# Clean up the local scratch environments (do not commit them):
Remove-Item -Recurse -Force .\_tmp-aligner, .\_tmp-aligner-verify
```

Commit only `config/mfa-env/aligner-win-64.lock` -- never the scratch
environment directories themselves (multi-GB).

mac/linux lockfiles (`aligner-osx-64.lock`, `aligner-linux-64.lock`, etc.)
are a natural follow-up once this pattern is proven further on Windows, not
required today -- `mfa_provision.lockfile_path()` returns `None` on
platforms without one, and every call site treats that as "fall back to a
user-managed conda + aligner environment," not an error.

## The vendored micromamba binary

`vendor/micromamba/micromamba.exe` is the official static release from
[mamba-org/micromamba-releases](https://github.com/mamba-org/micromamba-releases).
To update it:

```powershell
curl -L -o vendor\micromamba\micromamba.exe `
    https://github.com/mamba-org/micromamba-releases/releases/latest/download/micromamba-win-64
```

Re-run the lockfile validation steps above afterward to confirm the new
binary still provisions and invokes correctly.

## Building the VoxKit executable

Unchanged from before this feature: `invoke windows-build` (or
`macos-build`/`linux-build`) wraps `scripts/build.py`, which drives
PyInstaller directly (no committed `.spec` file). `vendor/` and `config/`
are both bundled via `--add-data`, resolved at runtime through
`sys._MEIPASS` when frozen (see `mfa_provision._bundle_root()`).

The Windows Inno Setup installer (`installer/windows/VoxKit.iss`) needs no
changes -- `vendor/`+`config/` are already inside the PyInstaller bundle
(`dist/VoxKit.exe`), not separate installer assets.

## Troubleshooting / the conda-path fallback

If a user's platform has no bundled lockfile yet, or they prefer their own
MFA install, the pre-existing "Conda Path" field in MFA engine settings
(Generate Alignments -> ⚙️) still works exactly as it always has: point it
at a `conda`/`conda.exe` with an `aligner` environment
(`conda create -n aligner -c conda-forge montreal-forced-aligner`), and
`_mfa_invocation()` falls back to that path whenever the bundled
environment isn't ready.
