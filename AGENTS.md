# AGENTS.md

Onboarding guide for coding agents working in this repository.

## Project

VoxKit is a PyQt6 desktop application for speech pathology research; a GUI front-end over multiple speech toolkits (alignment, training, transcription) with a shared storage for interacting with and processing speech datasets. Package lives at `src/voxkit/`. Python 3.11+, managed with `uv`.

## Repository Layout

```
src/voxkit/
├── gui/         # PyQt6 (pages, components, frameworks, workers)
├── engines/     # Speech toolkit backends (abstract base + implementations)
├── analyzers/   # Dataset metadata extractors (CSV summaries)
├── storage/     # Persistence/CRUD for datasets, models, alignments
├── services/    # External subprocess integrations
└── config/      # App configuration loaders (profile-aware)
config/
├── VERSION                    # Single source of truth for app version
├── profile.txt                # Active profile name
├── app_info.yaml              # Legacy fallback metadata
├── pipeline_definitions.yaml  # Legacy fallback metadata
└── profiles/<name>/           # Per-profile yaml configurations
tests/           # Pytest suite (unit + GUI via pytest-qt)
docs/            # ARCHITECTURE.md, CONTRIBUTING.md, RESEARCH.md
hooks/           # Build-time hooks to fix dependency problems in the build
scripts/         # Dev scripts (incl. build.py for PyInstaller)
installer/       # Platform installer scripts (Inno Setup for Windows)
main.py          # Entry point
```

Runtime data lives at `~/.voxkit/` (datasets, models, alignments, engine settings).

## Architecture

Hybrid "unstructured state + signals" PyQt pattern. See `docs/ARCHITECTURE.md` for the full picture before making structural changes. Key points:

- **Views access storage directly** — no controller intermediary. `storage/` is the model layer.
- **Async work runs in QThread workers** that emit `pyqtSignal` back to views.
- **Cross-page state** refreshes via parent window calling `reload()` on tab switch.
- **Engines** and **analyzers** each have an abstract base class and a singleton manager for discovery.
- **Config profiles**: `config/profile.txt` selects an active profile under `config/profiles/<name>/`. The loader is in (`src/voxkit/config/app_config.py`).

## Setup & Common Commands

> **IMPORTANT (read before touching anything):**
> 1. **Run `invoke setup` first, every fresh checkout.** It installs dependencies (`uv sync`), wires up pre-commit hooks, and prepares the local environment.
> 2. **Use `invoke` tasks for everything during development.** Do **not** reach for `pytest`, `ruff`, `mypy`, `pyinstaller`, or `uv run …` directly. The tasks in `tasks.py` set the right flags, paths, and env vars; bypassing them produces results that won't match CI or other contributors. Only call a tool directly if you genuinely need a flag the task doesn't expose, and prefer adding the flag to the task over a one-off workaround.

Tasks are defined in `tasks.py` (pyinvoke).

| Command | Purpose |
|---|---|
| `invoke setup` | Install deps + pre-commit hooks (run first) |
| `invoke dev` | Launch the app in dev mode |
| `invoke watch` | Dev mode with auto-reload on source changes |
| `invoke run-tests` | Unit + GUI tests |
| `invoke test-coverage` | Coverage for core modules |
| `invoke generate-coverage-badge` | Refresh `coverage.svg` |
| `invoke generate-documentation` | Build pdoc HTML into `docs/` |
| `invoke lint` / `invoke lint-check` | Ruff lint (fix / check) |
| `invoke format` / `invoke format-check` | Ruff format |
| `invoke mypy-check` | Type check |
| `invoke macos-build` / `linux-build` / `windows-build` | Standalone executable (PyInstaller) |
| `invoke clean` | Remove build artifacts |
| `invoke fresh-slate` | Remove virtual environment and lock file (Dependency troubleshooting) |
| `invoke --list` | Full list |

## Versioning

`config/VERSION` is the single source of truth. All consumers read it:

- `pyproject.toml` via `[tool.setuptools.dynamic] version = {file = ["config/VERSION"]}`
- `src/voxkit/__init__.py` (`__version__` read at import, handles PyInstaller `_MEIPASS`)
- `AppConfig.from_yaml` overrides any YAML `version:` with this file (legacy behavior)
- `installer/windows/VoxKit.iss` reads it via ISPP at compile time

To bump the version, edit `config/VERSION` and nothing else. Do not reintroduce hardcoded version strings in `__init__.py`, `app_info.yaml`, or the installer.

## Testing

- Framework: `pytest`, with `pytest-qt` for GUI and `pytest-asyncio` for async.
- Write tests for new business logic in `storage/`, `config/`, `analyzers/`. GUI components are excluded from coverage metrics but still testable with `pytest-qt` when useful.

## Gotchas for Agents

- `main.py`, `build.py`, `_frozen_patch.py` are excluded from lint/mypy/coverage — they're build/entry shims.
- `src/voxkit/__init__.py` eagerly imports all subpackages (including PyQt6 via `gui`) so pdoc can discover them. `import voxkit` is therefore expensive — fine for the app, painful for scripts that just want `__version__`. Don't "optimize" by removing the imports without checking pdoc output.
- Engines and services wrap external binaries; changes there are hard to unit-test and are omitted from coverage by design.
- Dependencies pin `torch==2.8.0` and pull several packages from Git SHAs — don't loosen these casually.
- PyInstaller bundles `config/` via `scripts/build.py` (`--add-data`); anything new in `config/` that the runtime needs will ship automatically, but custom paths outside `config/` will not.

### MFA runtime state on Windows

Two failure modes here are environmental, not code bugs. Both surface as an opaque `MFA alignment failed (exit 1)` in the GUI, so check these before debugging VoxKit.

**A half-deleted Postgres data directory deadlocks alignment permanently.** `mfa server start` spawns a *detached* Postgres that outlives the app, so it still holds handles under `~/.voxkit/mfa-root/pg_mfa_global/`. Deleting `~/.voxkit` while it runs strips the contents but cannot unlink the directory itself — leaving an empty shell. MFA keys both commands off directory *existence*, so that state is unrecoverable via its CLI:

- `server init` — refuses outright (`command_line/utils.py`, "The server directory already exists")
- `server start` — sees the directory, so never calls `initialize_server()`, then runs `pg_ctl -D <empty dir> start` and fails

Symptom is `DatabaseError: There was an error connecting to the global MFA database server`, and it will not self-heal. Fix by removing the empty `pg_mfa_global/` so `init` can run. `_ensure_mfa_server_running` in `src/voxkit/services/mfa.py` deliberately ignores return codes, which hides both failures — validate the data dir (`PG_VERSION`, `global/pg_control`) before `init` rather than trusting that the calls worked. When cleaning `~/.voxkit` by hand, stop the server first.

**Developer Mode changes MFA's alignment code path.** At `alignment/multiprocessing.py` (MFA 3.3.x) MFA symlinks `ali.*.ark` → `ali_first_pass.*.ark`, with an `except OSError → shutil.copyfile` fallback for platforms that can't symlink. With Developer Mode **on**, `os.symlink` succeeds unprivileged, so the fallback never fires — and if anything in the process tree enforces redirection trust, the later `ali_path.exists()` fails with `OSError [WinError 448] untrusted mount point` and kills the run. Developer Mode **off** yields `WinError 1314`, which is an `OSError`, so MFA copies instead and the run completes. Don't assume the copy path is dead code; on a dev machine it may never execute.
