# AGENTS.md

Onboarding guide for coding agents working in this repository.

## Project

VoxKit is a PyQt6 desktop application for speech pathology research — a GUI front-end over multiple speech toolkits (alignment, training, transcription). Package lives at `src/voxkit/`. Python 3.11+, managed with `uv`.

## Repository Layout

```
src/voxkit/
├── gui/         # PyQt6 (pages, components, frameworks, workers)
├── engines/     # Speech toolkit backends (abstract base + implementations)
├── analyzers/   # Dataset metadata extractors (CSV summaries)
├── storage/     # Persistence/CRUD for datasets, models, alignments
├── services/    # External subprocess integrations
└── config/      # App configuration and startup
tests/           # Pytest suite (unit + GUI via pytest-qt)
docs/            # ARCHITECTURE.md, CONTRIBUTING.md, RESEARCH.md
hooks/           # Pre-commit hooks
scripts/         # Dev scripts
main.py          # Entry point
```

Runtime data lives at `~/.voxkit/` (datasets, models, alignments, engine settings).

## Architecture

Hybrid "unstructured state + signals" PyQt pattern. See `docs/ARCHITECTURE.md` for the full picture before making structural changes. Key points:

- **Views access storage directly** — no controller intermediary. `storage/` is the model layer.
- **Async work runs in QThread workers** that emit `pyqtSignal` back to views.
- **Cross-page state** refreshes via parent window calling `reload()` on tab switch.
- **Engines** and **analyzers** each have an abstract base class and a singleton manager for discovery.

## Setup & Common Commands

Use `make` — do not invoke tools directly unless you need a flag `make` doesn't expose.

| Command | Purpose |
|---|---|
| `make setup` | Install deps + pre-commit hooks (run first) |
| `make dev` | Launch the app in dev mode |
| `make run-tests` | Unit + GUI tests |
| `make test-coverage` | Coverage for core modules |
| `make lint` / `make lint-check` | Ruff lint (fix / check) |
| `make format` / `make format-check` | Ruff format |
| `make mypy-check` | Type check |
| `make build` | Standalone executable (PyInstaller) |
| `make clean` | Remove build artifacts |
| `make help` | Full list |

## Code Standards

- **Ruff**: line length 100, double quotes, isort-managed imports. Lints: `E`, `F`, `I`, `S` (bandit). Per-file ignores in `pyproject.toml`.
- **Mypy**: Python 3.11, `warn_return_any=true`. `tests/` and `main.py` excluded.
- **Coverage targets**: 70–80% on new business logic in `storage/`, `config/`, `analyzers/`. GUI, engines, and services are deliberately omitted from coverage.
- Pre-commit runs on every commit — don't bypass with `--no-verify`.

## Testing

- Framework: `pytest`, with `pytest-qt` for GUI and `pytest-asyncio` for async.
- Write tests for new business logic in `storage/`, `config/`, `analyzers/`. GUI components are excluded from coverage metrics but still testable with `pytest-qt` when useful.
- Run `make run-tests` before reporting a task complete. For UI changes, also launch `make dev` and exercise the feature — type checks don't verify user-facing behavior.

## Commit & PR Conventions

Format: `<type>: <subject>` where type ∈ `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`. Keep commits small and logical. See `docs/CONTRIBUTING.md` for the review process.

## Gotchas for Agents

- Two test directories exist at repo root: `tests/` (the real suite, in `pyproject.toml` config) and `test/` (untracked scratch). Put new tests in `tests/`.
- The `pyproject.toml` `name` is still `pypllr-gui` (legacy) but the package is `voxkit`. Don't "fix" this without asking.
- `main.py`, `build.py`, `_frozen_patch.py` are excluded from lint/mypy/coverage — they're build/entry shims.
- Engines and services wrap external binaries; changes there are hard to unit-test and are omitted from coverage by design.
- Dependencies pin `torch==2.8.0` and pull several packages from Git SHAs — don't loosen these casually.
