# VoxKit Desktop — Technical Debt Audit

**Date:** 2026-08-19 · **Commit:** `d6032e0` · **Scope:** whole repository

An eleven-way parallel audit: one pass per module of `src/voxkit/`, one over `tests/`, and one over the root (build chain, CI, docs, dependencies). Every finding cites `file:line` and was required to be verified against the code rather than inferred — several sections record hypotheses that were checked and disproved, and those are noted in place.

**171 findings — 45 High, 93 Medium, 33 Low.**

## How to read this

**Severity** — `High`: actively causes bugs, ships broken behaviour, or blocks change. `Medium`: slows work, will bite later. `Low`: cleanup.

**Effort** — `S`: under an hour. `M`: a few hours. `L`: a day or more.

Findings are sorted High → Medium → Low within each module. IDs are stable (`ST-2`, `PL-1`, …) and are used for cross-references throughout.

---

## Executive summary

The application works and is in real use; nothing here says otherwise. But three things are true at once, and together they explain most of what follows.

**The app cannot tell you what went wrong.** `main.py:16-19` redirects `sys.stdout` to `/dev/null` whenever `sys.stdout is None` — which is always, in a `--windowed` PyInstaller build, and both the macOS and Windows build tasks pass `--windowed`. There are **251 `print()` calls** in shipped code and they are the primary diagnostic channel in every module. A full logging stack already exists (`config/logging_config.py`, a rotating file at `~/.voxkit/logs/voxkit.log`, and a Qt handler feeding an in-app log viewer), is initialised at `main.py:131` before any of those prints run, and is used by 8 files out of 29 that print. So the diagnostics are written, and then discarded, exactly in the build where they matter.

**Failure is usually silent.** There are 58 `except Exception` handlers, 22 of them in `storage/` alone. The dominant idiom is catch → `print` → return a falsy value or continue. Combined with the above, a permission error, a 404, a corrupt JSON file, and a genuine bug all present to the user as the same thing: an empty list, a missing chart, or nothing at all. Several findings here are cases where that pattern converts a recoverable error into a permanent one — `SV-5` (a half-built MFA environment latches "ready" forever), `CF-1` (a failed first launch is marked complete and never retried), `EN-5` (a failed alignment is reported to the user as a success).

**The safety nets are switched off precisely where the risk is.** `check_untyped_defs = false` means mypy does not analyse the body of any unannotated function — roughly 47% of functions in `src/`, and disproportionately the largest ones. `[tool.coverage.run] omit` excises all of `gui/` (12,960 LOC), all of `services/`, and every engine implementation, leaving a coverage denominator of **1,294 statements out of ~17,959** — so the badge describes about 7% of the application. And the test suite has been **red on macOS and Ubuntu since 2026-08-11**, with two PRs merged over the red (verified independently: 2 failures, 322 passes). The failure is in a test, not the product, which is worse — it is pure noise training the team to ignore the signal.

Set against that: repo hygiene is genuinely clean (no tracked build artifacts, `.gitignore` correct, `config/VERSION` really is a single source of truth), the `invoke` command table in `AGENTS.md` verifies command-by-command against `tasks.py`, the `tests/storage/` and `tests/services/` suites are real behaviour tests rather than mock theatre, and the comments in `services/mfa.py` encode hard-won Windows failure modes that would otherwise have been lost.

### Findings by module

| Module | LOC | Findings | High | Medium | Low |
|---|---:|---:|---:|---:|---:|
| Root, build & tooling | — | 18 | 6 | 9 | 3 |
| `storage/` | 1,967 | 18 | 3 | 13 | 2 |
| `engines/` | 1,164 | 18 | 6 | 8 | 4 |
| `services/` | 508 | 16 | 4 | 9 | 3 |
| `config/` | 665 | 14 | 3 | 7 | 4 |
| `analyzers/` | 655 | 13 | 3 | 5 | 5 |
| `gui/pages/pipeline/` | 6,736 | 11 | 5 | 5 | 1 |
| `gui/frameworks/` | 1,436 | 20 | 3 | 13 | 4 |
| `gui/components/` + `styles/` | 2,667 | 14 | 3 | 7 | 4 |
| `gui/pages/{datasets,models}/` + `workers/` | 2,121 | 18 | 5 | 12 | 1 |
| `tests/` | 5,281 | 11 | 4 | 5 | 2 |
| **Total** | | **171** | **45** | **93** | **33** |

---

## Cross-cutting themes

These are patterns no single module could see. Each is the reason several individual findings exist, and fixing the pattern is usually cheaper than fixing its instances one at a time.

### 1. Diagnostics are written and then thrown away — *fixed 2026-08-19, see `RT-6`*

251 `print()` calls across `src/`, `scripts/`, and `hooks/`, all discarded in the shipped build (`RT-6`). The heaviest concentrations: `pllr_stacker.py` (70), `w2tg_engine.py` (20), `startup_config.py` (18), `storage/models.py` (14), `services/mfa.py` (13). Two of these print full dataset metadata and absolute participant-derived paths to stdout (`PL-6`), in a project that runs a PHI scanner in pre-commit specifically to keep patient identifiers out of the tree.

The project has already written down that this is wrong. `startup_config.py:126-128` states it in prose: *"in a `--windowed` PyInstaller build `sys.stdout` is redirected to devnull (see `main.py`), so `print()` diagnostics from this path are discarded exactly when they are most needed."* The convention exists; it just was not applied.

*Related:* `RT-6`, `AN-6`, `EN-6`, `SV-7`, `CF-1`, `ST-17`, `PL-6`, `GC-5`, `GF-10`, `PW-7`.

### 2. Silent failure is the default error contract

Four sibling functions in `storage/` handle "metadata is unreadable" four incompatible ways — return `None`, print-and-return-`None`, print-and-re-raise, and raise (`ST-5`). Callers cannot reason about any storage call without reading its body. The same inconsistency shows up between engines (`EN-1`: one raises where its sibling returns) and between pages.

The consequences compound with theme 1. `AN-1`: an analyzer failure surfaces to the user as an unrelated CSV error while the real cause goes to a discarded stdout. `PW-1`: an unguarded worker `run()` means a raising storage call kills the thread, the completion signal never fires, and the UI hangs indefinitely with no message.

*Related:* `AN-1`, `EN-5`, `CF-1`, `SV-3`, `ST-5`, `ST-9`, `PW-1`, `PW-9`, `GF-4`.

### 3. Copy-paste siblings that have already diverged

This is the single largest structural cost in the codebase, and in every measured case the copies have **already** drifted:

| Where | Scale | Evidence of drift |
|---|---|---|
| `viewer` / `comparison` / `correct_alignments` stackers | 4,577 LOC, 27–52% verbatim | `_update_active_segment_label` dropped from two of three (`PL-1`) |
| `default_analyzer` / `clip_duration_statistics` charts | 87 of ~115 lines identical | one asserts `a is not None`, the other dropped it (`AN-2`) |
| `mfa_engine.align` / `w2tg_engine.align` | full lifecycle | diverged three ways, incl. `EN-5`'s silent success (`EN-1`) |
| `datasets_page` / `models_page` | 6 paired blocks | `PW-5`: a whole dead module left behind, now broken |
| root vs profile YAML | 288 identical lines | "PLLR" vs "GOP" already differ (`RT-10`) |
| `DNAStrandWidget` / `_WaveformStrip` | full paint routine | two different brand colours (`GC-7`) |
| dropdown population | 12 hand-written sites | training page shows different columns before vs after reload (`PL-5`) |

*Related:* `PL-1`, `PL-5`, `AN-2`, `EN-1`, `PW-6`, `RT-10`, `GC-4`, `GC-7`, `SV-10`, `ST-12`.

### 4. Values declared twice, then drifted

Every `settings.get(key, default)` restates a `default_value` already declared in a `FieldConfig`. `EN-2` is the shipped consequence: commit `3f678bb` flipped W2TG's speaker-adaptation default to `True` in the field config and left the runtime fallback at `False`, so an install whose settings file predates the key runs with adaptation off while the UI says on — and the vendored `align_dirs` rejects that combination outright for the default model. The same double-declaration exists for log rotation (five places, `CF-5`), `UIConfig` (`CF-11`), and Whisper's model-size list (`EN-16`).

*Related:* `EN-2`, `EN-4`, `CF-5`, `CF-11`, `EN-16`, `RT-13`.

### 5. `self.parent` is a bound method, and two features have never worked

`QWidget.parent` is a method. Code that stores no separate reference and then probes `hasattr(self.parent, "…")` always takes the false branch:

- `PL-4`: `training_stacker.py:259` — a newly trained model has **never once** refreshed the Prediction page's model list, though the docstring promises it.
- `GF-6`: `generic.py:228` — settings dialogs have **never** been centred on the main window; the surrounding `except AttributeError: pass` is the fossil of someone hitting this and suppressing the symptom.

Both sit in function bodies mypy does not check (theme 7). Two independent agents found this in unrelated files, which is what makes it a pattern rather than a bug.

### 6. Layering runs backwards in three places

`docs/ARCHITECTURE.md` describes `gui` as the presentation layer over independent backend layers. In practice:

- **`engines/` imports from `gui/`** — all three engines pull `FieldConfig`/`FieldType`/`SettingsConfig` from `gui.frameworks.settings_modal` purely to describe their settings schema. `base.py` then cannot name the type, so `get_settings_config()` returns `Any` — and the docstrings were mechanically find-and-replaced along with it, leaving `"Return the :class:`Any` for a tool type"` in the published API docs (`EN-10`).
- **`config/` imports `services/` and `storage/`** — the lowest layer has the most dependencies; `import voxkit.config` transitively initialises half the app and takes ~7.7s (`CF-7`).
- **`analyzers/` duplicates the GUI palette** as hex literals rather than importing it, because importing it would invert the layering (`AN-11`).

The clean fix for the first is the same as for the third: `settings_modal/api.py` is pure dataclasses with zero Qt imports and belongs somewhere neutral.

### 7. Type checking and coverage are disabled exactly where the risk concentrates

`check_untyped_defs = false` means mypy skips the *body* of any unannotated function. Measured per module: 97 of 261 functions in `gui/pages/pipeline/` lack return annotations (`PL-10`), 56 of 69 in `gui/components/` (`GC-9`), 40 of 74 in pages+workers (`PW-11`), and `categorical_table.py` is *entirely* invisible at 688 LOC (`GF-15`). The largest, most bug-prone functions are precisely the unannotated ones — `on_train_model` (94 lines), `build_ui` (274 lines), `extract_pllr_logic` (146 lines).

Coverage omits `gui/**`, `services/**`, and every `*_engine.py`, so the badge's denominator is 1,294 of ~17,959 statements (`TS-2`). The omit list is also now factually wrong about `services/`, which has 27 passing tests. And `scripts/build.py` — which contains `RT-1` and `RT-2` — is excluded from both ruff and mypy (`RT-9`).

*Related:* `TS-1`, `TS-2`, `RT-4`, `RT-9`, `PL-10`, `GC-9`, `PW-11`, `GF-15`, `SV-9`, `ST-18`.

### 8. The Qt threading layer is unsupervised

No worker anywhere has an owner, a cancellation path, or a shutdown hook — `requestInterruption`, `isInterruptionRequested`, and `isRunning` have **zero occurrences** across `gui/` (`PW-2`). All four workers shadow the built-in `QThread.finished` signal, which makes the standard `finished.connect(deleteLater)` cleanup idiom actively unsafe, and that trap is inherited by 8 more instantiation sites in the pipeline page (`PW-3`). Worker bodies read `QComboBox` state off the GUI thread (`PL-3`), and in one case a completion handler re-reads the dropdown instead of the captured value, so changing selection during a long transcription marks the **wrong** dataset (`PL-3`).

Meanwhile the heaviest operations — multi-gigabyte `shutil.copytree` import/export — run synchronously on the UI thread, while the lighter registration path is the one that got a worker (`PW-4`).

*Related:* `PW-1`, `PW-2`, `PW-3`, `PW-4`, `PL-3`, `GF-12`, `SV-13`, `EN-17`.

### 9. Persistence has no atomicity, no schema, and no migration path

Every metadata write in `storage/` is a truncate-in-place `open(path, "w")` + `json.dump` — there is no `os.replace`, no temp-file-rename, and no `fsync` anywhere in the module — and `update_alignment` is an unlocked read-modify-write called from a worker thread while the GUI thread reads the same files (`ST-2`). None of the three persisted formats carries a `schema_version`, and a hand-rolled compatibility shim already exists to prove it is needed (`ST-8`). The settings framework has the same gap: a `FieldConfig` type change between releases becomes an unhandled `TypeError` on dialog open for every existing user (`GF-9`).

`AGENTS.md:98-105` already documents that users kill this app and hand-delete `~/.voxkit` mid-run, so the crash window is not hypothetical.

### 10. The style system is half-adopted, and the root cause is one CSS rule

`gui/__init__.py:77-82` applies `QWidget { border: none; }` globally, which cascades to every widget in the app. That single rule is why `styles/` carries so many constants whose only job is to put the border back, and it is upstream of the sprawl: 27 of 56 style constants never reference the `Colors` palette, four rival blue families coexist, and the app's *real* global stylesheet lives as a 93-line string literal in `gui/__init__.py` — 53 lines below a docstring claiming styling is centralised in `styles/` (`GC-2`, `GC-3`). Repo-wide, 38 `setStyleSheet` calls pass inline literals, concentrated in the pipeline stackers (`PL-9`, `PW-12`), and painted widgets bypass QSS entirely (`GC-6`).

### 11. Several of these were already diagnosed in the repo's own prose

This is worth calling out separately because it changes what the fix is. In at least four cases the team found the problem, wrote it down, and the code never changed:

- `AGENTS.md:103` specifies the exact fix for `_ensure_mfa_server_running`'s swallowed return codes — validate `PG_VERSION` / `global/pg_control` before `init`. Not implemented (`SV-3`).
- `mfa_engine.py:217-251` is a 60-line block under a `TEMP FIX` banner whose own comment says the fix belongs in `storage/models.py:create_model`. Both halves are still there (`EN-7`, `ST-3`).
- `ensure_mfa_environment`'s docstring describes the swallow-and-mark-complete bug as *fixed* — but the identical bug is still live for acoustic-model downloads two functions away (`CF-1`).
- `docs/BUILD.md:44-47` now states the **opposite** of what `main.py:143-145` does about MFA retry, and `main.py`'s comment was written specifically to record the change (`SV-16`).

---

## Priority: quick wins

High-severity findings that are `S` effort — an hour or less each. Fifteen of the forty-five.

| ID | Module | Finding |
|---|---|---|
| `TS-1` | tests | CI is red on 2 of 3 platforms; the bug is in the test, not the product |
| `RT-1` | root | PyInstaller hidden-imports name two engine modules that don't exist |
| `RT-4` | root | Add `pre-commit run --all-files` to CI so the PHI scanner actually gates PRs |
| `EN-5` | engines | `W2TGEngine.align` returns success when the alignment record fails |
| `EN-2` | engines | Speaker-adaptation default drifted between config and runtime fallback |
| `EN-4` | engines | Merge defaults into existing settings files so new fields don't break upgrades |
| `SV-2` | services | `_find_conda` returns a directory where an executable is expected |
| `CF-2` | config | Frozen build uses the wrong config resolver; profiles break only in the installer |
| `CF-3` | config | One `or {}` guard prevents a launch crash from user-edited YAML |
| `AN-1` | analyzers | Move the `try` inside the loop so one bad speaker dir doesn't truncate the scan |
| `GC-1` | gui-components | `LogViewerDialog` leaks a live log subscriber on every close |
| `GF-3` | gui-frameworks | `GenericDialog` never removes its blur; 7 call sites work around it |
| `GF-2` | gui-frameworks | Expose an insertion point so the models page stops walking the layout tree |
| `PW-1` | pages/workers | Wrap the two registration workers' `run()` in try/except |
| `PW-5` | pages/workers | Delete `datasets/utils.py` — dead, duplicated, and broken |

### Suggested sequence

1. **Unblock the signal** — `TS-1` (green CI), then `RT-4` (make CI enforce what pre-commit does). Nothing else is safely verifiable until the suite is trustworthy.
2. **Stop shipping silence** — `RT-6` package by package, starting with `services/mfa.py`, `config/startup_config.py`, and `engines/w2tg_engine.py`, which cover the failure modes `docs/BUILD.md` already catalogues. Add ruff `T20` so it cannot regress.
3. **Fix what is actively wrong** — the quick-wins table above.
4. **Then the structural work** — `PL-1` (extract the shared timeline widget, ~1,000 lines deleted), `EN-1` (template-method the alignment lifecycle), `ST-2` (one atomic writer), `GC-3` (kill the global `border: none`).

---

## Module reports

---

## Root, build & tooling

**Health:** The app builds and ships — but only from one developer's machine, and CI verifies none of it. | **Findings:** 18 (6 High / 9 Medium / 3 Low)

Repo hygiene is genuinely good: nothing generated is tracked, `.gitignore` covers `build/`, `dist/`, `*.spec`, and `.DS_Store`, and `config/VERSION` really is a single source of truth honored by `pyproject.toml`, `src/voxkit/__init__.py`, and `installer/windows/VoxKit.iss`. The debt is concentrated in two places. First, **the build chain is entirely un-CI'd and machine-specific**: three `invoke *-build` tasks and an Inno Setup script that no workflow ever runs, a macOS path hardcoded to `libpython3.11.dylib` with an ad-hoc signature that Gatekeeper will reject on any other Mac, and PyInstaller hidden-imports naming two engine modules that were deleted or renamed long ago. Second, **CI is strictly weaker than pre-commit**: the `shredguard` patient-ID/PHI scan configured in `pyproject.toml` runs only on developers who ran `invoke setup`, and never on a pull request. Documentation drift is broad but shallow — six README badges still point at the old `PyPLLR_GUI` repo, `docs/CONTRIBUTING.md` links a `TESTING.md` that does not exist, and `docs/BUILD.md` states the opposite of what `main.py` now does about MFA retry. Underneath all of it sits a cross-cutting logging failure: ~250 `print()` calls in `src/` that the shipped `--windowed` build discards to `/dev/null` by design.

### Repo-wide debt heat map

Counts over tracked files only (`git ls-files`), so nothing from `dist/`, `build/`, or `.venv/` is included. `print(` was swept over `*.py` excluding `tests/`.

| Directory | TODO/FIXME | `except Exception` | `type: ignore` | `# noqa` | `print(` | Notes |
|---|---|---|---|---|---|---|
| `src/voxkit/gui/` | 5 | 20 | 3 | 11 | **131** | `pllr_stacker.py` alone has 70 prints; 9 of 11 noqa live in `pages/pipeline/` |
| `src/voxkit/storage/` | 0 | **22** | 6 | 0 | 24 | Highest `except Exception` density in the repo — 22 in one 6-file package |
| `src/voxkit/engines/` | 0 | 5 | 0 | 0 | 31 | `w2tg_engine.py` 20 prints |
| `src/voxkit/config/` | 0 | 3 | 1 | 0 | 18 | all 18 in `startup_config.py` |
| `src/voxkit/services/` | 0 | 0 | 1 | 0 | 13 | `mfa.py` |
| `src/voxkit/analyzers/` | 0 | 5 | 0 | 0 | 4 | |
| `scripts/` | 0 | 1 | 0 | 0 | 21 | `build.py`, excluded from ruff + mypy |
| `hooks/` | 0 | 0 | 0 | 0 | 2 | debug prints left in `hook-speechbrain.py:7`, `hook-Wav2TextGrid.py:14` |
| root (`main.py`, `tasks.py`, `_frozen_patch.py`) | 0 | 2 | 1 | 5 | 7 | `main.py:33` swallows the Windows UTF-8 setup failure silently |
| `tests/` | 0 | 0 | 0 | 0 | n/a | clean on every counted axis |
| `docs/`, `.github/`, `config/`, `README.md` | 3 | — | — | — | — | 2 are the `<TODO>` citation placeholders in `README.md:75,81` |
| **Total** | **8** | **58** | **12** | **16** | **251** | |

### Findings

#### RT-1. PyInstaller hidden imports name two engine modules that do not exist — `High` / `S`
**Where:** `scripts/build.py:150-151`
**What:** The `default_hidden` list forces `'voxkit.engines._w2tg_engine'` and `'voxkit.engines._whisperx_engine'`. Neither module exists: `src/voxkit/engines/` contains `base.py`, `constants.py`, `faster_whisper_engine.py`, `mfa_engine.py`, `w2tg_engine.py`. A repo-wide grep for `_w2tg_engine|_whisperx_engine|whisperx` in `src/` returns zero hits — the only references are these two build.py lines. Meanwhile the two engines that *do* exist and are *not* on the list are `voxkit.engines.w2tg_engine` and `voxkit.engines.faster_whisper_engine`; only `voxkit.engines.mfa_engine` (line 152) is correct.
**Why it's debt:** PyInstaller silently warns-and-continues on a missing hidden import, so the build stays green while two of the three shipped engines rely purely on static-analysis discovery. If either is loaded through the engine-manager's dynamic discovery rather than a literal `import`, it will be absent from the bundle and fail only for end users. The `_whisperx_engine` entry also encodes a backend (`WhisperX`) that `config/app_info.yaml:27` still advertises as "in development" but which has no module at all.
**Fix:** Replace the two stale names with `voxkit.engines.w2tg_engine` and `voxkit.engines.faster_whisper_engine`. Better: derive the list from `pkgutil.iter_modules(voxkit.engines.__path__)` so it cannot drift again, and add a post-build smoke check that imports each engine from `dist/`.

#### RT-2. macOS build hardcodes Python 3.11 and ships an ad-hoc signature — `High` / `M`
**Where:** `scripts/build.py:66`, `:90`, `:211`; `scripts/build.py:39-45`
**What:** Three separate lines hardcode `libpython3.11.dylib` — `python_lib_dest = internal_dir / "libpython3.11.dylib"`, `install_name_tool -id "@loader_path/libpython3.11.dylib"`, and `python_lib = Path(sys.base_prefix) / "lib" / "libpython3.11.dylib"`. `pyproject.toml:9` allows `requires-python = ">=3.11"` and `uv.lock:4-9` carries resolution markers for 3.12, 3.13, and 3.15. Separately, `codesign_macos_app()` signs with `--sign -` (ad-hoc) and there is no notarization anywhere: `grep -rn "notarize|hdiutil|\.dmg|productbuild|Developer ID" tasks.py scripts/ docs/ .github/ installer/` returns nothing.
**Why it's debt:** Any contributor on Python 3.12+ produces a silently broken `.app` — `python_lib_source.exists()` is False, the copy is skipped, and `install_name_tool -change` runs with `check=False` (line 87-92) so the failure is never surfaced. And because the bundle is only ad-hoc signed and never notarized or stapled, a downloaded `.app` is quarantined and refused by Gatekeeper on every Mac except the one that built it, so macOS has no viable distribution story at all.
**Fix:** Derive the dylib name from `f"libpython{sys.version_info.major}.{sys.version_info.minor}.dylib"`, and make the `install_name_tool` calls `check=True` so a mismatch fails loudly. For distribution, add a Developer ID signing + `notarytool submit --wait` + `stapler staple` step, gated on the signing identity being present.

#### RT-3. There is no build or release automation, and the PR template documents one that doesn't exist — `High` / `L`
**Where:** `.github/workflows/` (5 files); `.github/PULL_REQUEST_TEMPLATE/main_merge.md:33`; `installer/windows/VoxKit.iss`
**What:** `grep -rn "tags:|release:|workflow_dispatch" .github/workflows/` returns nothing — every workflow triggers only on `push`/`pull_request` to `main`/`develop`. There is no job that runs `invoke macos-build`, `linux-build`, or `windows-build`, and no job that compiles `installer/windows/VoxKit.iss` (`grep -rn "iss\b|Inno|ISCC" tasks.py scripts/ .github/` → nothing). Yet `main_merge.md:33` instructs the releaser to "Push tag syntax to trigger build of assets."
**Why it's debt:** Every release artifact for all three platforms is produced by hand on one machine, which is exactly why RT-1 and RT-2 have gone unnoticed — nothing else ever exercises that code path. The release checklist tells maintainers to push a tag and wait for assets that will never appear. It also means the Windows installer (`VoxKit.iss`) is compiled by hand in the Inno Setup GUI, with no verification that `dist/VoxKit.exe` (`VoxKit.iss:44`) even exists.
**Fix:** Add a `release.yml` triggered on `push: tags: ['v*']` with a matrix of `macos-latest`/`ubuntu-latest`/`windows-latest` running the corresponding `invoke *-build`, an `ISCC` step for the `.iss`, and `softprops/action-gh-release` to upload. Even a `workflow_dispatch`-only build job that just proves all three builds still compile would catch RT-1 and RT-2 today.

#### RT-4. CI enforces strictly less than pre-commit — the PHI scanner never runs on a PR — `High` / `S`
**Where:** `.pre-commit-config.yaml:1-32` vs `.github/workflows/code-quality.yml:38-47`; `pyproject.toml:220-229`
**What:** pre-commit runs five things: `shredguard check`, `ruff --fix`, `ruff-format`, `mypy .`, and `trailing-whitespace`/`end-of-file-fixer`/`check-yaml`. CI runs three: `invoke format-check`, `invoke lint-check`, `invoke mypy-check`. **`shredguard` is not in CI.** `pyproject.toml:222-229` configures it with two patterns — a 10-digit phone-number regex and `\d{3,5}_[MF]_+` described as "Patient ID". Additionally the two ruff installs are different versions: `.pre-commit-config.yaml:11` pins `ruff-pre-commit` at `rev: v0.14.10`, while `pyproject.toml:45` floats `ruff>=0.14.0` and `uv.lock:3488-3489` has resolved it to `0.15.12` — the version CI actually uses.
**Why it's debt:** The only thing standing between a speech-pathology dataset's patient identifiers and a public git history is a hook that lives on individual laptops. A contributor who clones without running `invoke setup`, or who uses `git commit --no-verify`, bypasses it entirely and CI will not notice. The ruff skew is the classic "green locally, red in CI (or vice versa)" generator — a rule added or changed between 0.14.10 and 0.15.12 fires in exactly one of the two places.
**Fix:** Add a `pre-commit run --all-files` step to `code-quality.yml` (this subsumes lint, format, mypy, *and* shredguard in one gate), and pin the pre-commit ruff `rev` and the `[dependency-groups] dev` ruff specifier to the same exact version, bumped together.

#### RT-5. Four runtime dependencies track moving git branches, and `invoke fresh-slate` deletes the only thing pinning them — `High` / `M`
**Where:** `pyproject.toml:64-68`; `tasks.py:228-238`; `AGENTS.md:91`
**What:** All four git sources use `branch = ...`, not `rev`/tag: `pypllrcomputer` → `pkadambi/PyPhonemePronunciationScorer@voxkit-windows-variant`, `wav2textgrid` → `pkadambi/Wav2TextGrid@voxkit-windows-variant`, `alignment-comparison-plots` → `WISCLab/alignment-comparison-plots@voxkit-windows-variant`, `speechbrain` → `BeckettFrey/speechbrain@fix/windows-lazy-import-inspect-path` — a personal fork. `uv.lock` does pin commits (`uv.lock:3068`, `4189`, `156`, `3826`), but `tasks.py:237` — the documented `invoke fresh-slate` "dependency troubleshooting" task — runs `(ROOT / "uv.lock").unlink(missing_ok=True)`. `AGENTS.md:91` claims these "pull several packages from Git SHAs", which is true only of the lock, not of the declared dependency.
**Why it's debt:** The documented remedy for a broken environment throws away the only reproducibility guarantee the project has, and the next `uv sync` re-resolves four packages against whatever those branch heads point at now. Three of the four branches live in accounts outside the owning org; a force-push, branch deletion, or account change breaks every fresh checkout with no warning and no path back. `speechbrain` in particular is a patched fork of a 1.1.0 release carrying a Windows fix, with no upstream-PR link recorded anywhere and no mechanism to notice when it can be dropped.
**Fix:** Change all four `[tool.uv.sources]` entries from `branch = "..."` to `rev = "<sha>"` using the SHAs already in `uv.lock`, so the pin survives lockfile deletion. Make `fresh-slate` delete `.venv` only (or require an explicit `--lock` flag). Add a comment beside the `speechbrain` fork naming the upstream issue/PR and the condition for removing it.

#### RT-6. ~250 `print()` calls in `src/` are discarded by the shipped build — `High` / `L`

> **Status: fixed (2026-08-19).** All 221 production `print()` calls under `src/voxkit/` now go
> through `logging.getLogger(__name__)`; 26 modules carry a logger. Pure debug noise was deleted
> rather than converted (`datasets.py`'s bare `print(now)`, `datasets_page.py`'s per-row alignment
> dumps, ~30 control-flow narration lines in `pllr_stacker.py`). Ruff `T20` is enabled to prevent
> regression, with per-file ignores for `scripts/`, `hooks/`, `tasks.py`, and `_frozen_patch.py`,
> which run at build time with a real console. Demo `__main__` blocks are `# noqa: T201`-marked
> pending their deletion under `GC-11`/`GF-14`/`PW-8`. Verified end-to-end with stdout redirected
> to `/dev/null`: diagnostics land in `~/.voxkit/logs/voxkit.log` with module names and tracebacks.
**Where:** `main.py:16-19`; 251 call sites across `src/`, `scripts/`, `hooks/` (see heat map)
**What:** `main.py:16-19` reassigns `sys.stdout`/`sys.stderr` to `open(os.devnull, "w")` when they are `None`, which is always the case in a `--windowed` PyInstaller build (both `macos-build` and `windows-build` pass `--windowed`, `tasks.py:99,189`). Meanwhile the codebase contains 251 `print()` calls outside tests, concentrated in `src/voxkit/gui/pages/pipeline/pllr_stacker.py` (70), `src/voxkit/engines/w2tg_engine.py` (20), `src/voxkit/config/startup_config.py` (18), `src/voxkit/storage/models.py` (14), `src/voxkit/services/mfa.py` (13). The project already has a full logging stack: `src/voxkit/config/logging_config.py`, a rolling file at `~/.voxkit/logs/voxkit.log` (`config/app_info.yaml:9-11`), and a Qt-aware handler wired up at `main.py:131-132` that feeds an in-app log viewer.
**Why it's debt:** Every one of those 251 diagnostics is invisible in the only build users run. `docs/BUILD.md:49-97` is a long catalogue of MFA failures that were painful to diagnose precisely because the app produces no usable output — and `AGENTS.md:96` notes users see nothing but "an opaque `MFA alignment failed (exit 1)`". The infrastructure to fix this already exists and is already initialized before any of these run; it is simply not used. This is the single highest-leverage cross-cutting change in the repo.
**Fix:** Convert `print(` → `logger.info/debug/warning` package by package (each module agent owns its own files; `startup_config.py`, `services/mfa.py`, and `engines/w2tg_engine.py` are the highest value since they cover the failure modes documented in BUILD.md). Then add `T20` (flake8-print) to `[tool.ruff.lint] select` in `pyproject.toml:93-98` with a per-file ignore for `scripts/` and `hooks/`, so the count cannot grow back.

#### RT-7. Dev-only tooling is declared as a production dependency — `Medium` / `S`
**Where:** `pyproject.toml:24-25`, `:39-44`
**What:** `[project.dependencies]` lists `"pre-commit>=4.3.0"` and `"pytest>=8.4.2"` alongside `torch` and `pyqt6`. Both are *also* correctly listed in `[dependency-groups] dev` (lines 39-40), and `pre-commit>=4.3.0` is listed **twice inside the dev group** (lines 39 and 44).
**Why it's debt:** `uv sync` in CI and `pyinstaller` both resolve `[project.dependencies]`, so pre-commit, pytest, and their transitive trees (identify, nodeenv, virtualenv, pluggy, iniconfig, …) are candidates for inclusion in the shipped bundle — pure bloat in a build that is already enormous. It also makes the dev/prod boundary meaningless: nothing stops the next dev tool from landing in the runtime set.
**Fix:** Delete lines 24-25 from `[project.dependencies]` and the duplicate `pre-commit` at line 44.

#### RT-8. Lint and type-check config points at five files that do not exist — `Medium` / `S`
**Where:** `pyproject.toml:87-88`, `:112`, `:127-134`, `:159`; `.gitignore:60`; `AGENTS.md:88`
**What:** Verified missing from disk: `example_startup_script.py` (ruff exclude line 87, mypy exclude line 130), `test_imports.py` (ruff line 88, mypy line 131, `.gitignore:60`), `src/voxkit/gui/pages/pipeline/evaluation_stacker.py` (per-file-ignores line 112), `src/voxkit/config.py` (coverage omit line 159), and top-level `build.py` (ruff line 86 / mypy line 129 — the real file is `scripts/build.py`, which matches only incidentally because these are substring patterns). Related: `AGENTS.md:88` states "`main.py`, `build.py`, `_frozen_patch.py` are excluded from lint/mypy/coverage" — but `_frozen_patch.py` appears in *neither* the ruff exclude nor the mypy exclude, only in `[tool.coverage.run] omit` (line 165). `_frozen_patch.py:24` carries a `# type: ignore[assignment]`, which proves mypy is checking it.
**Why it's debt:** Five dead entries make the config unreadable and unsafe to prune — a reader cannot tell which exclusions still matter. The `evaluation_stacker.py` per-file-ignore in particular means whoever eventually adds subprocess calls to a pipeline stacker will hit an unexplained `S603` and have no idea an exemption was once granted. And the AGENTS.md claim actively misleads: an agent told `_frozen_patch.py` is exempt will not run the checks that would catch a break there.
**Fix:** Delete the five phantom entries. Anchor the two real ones as `scripts/build.py` and `main.py`. Correct `AGENTS.md:88` to say `_frozen_patch.py` is excluded from coverage only.

#### RT-9. mypy is configured so it skips nearly half the codebase, plus 560 lines exempted outright — `Medium` / `M`
**Where:** `pyproject.toml:121-135`
**What:** `check_untyped_defs = false` combined with `ignore_missing_imports = true`. With `check_untyped_defs` off, mypy does not analyze the *body* of any function lacking annotations. In `src/` there are 591 `def`/`async def` statements and only 313 carry a `->` return annotation — so roughly 278 function bodies (47%) are never type-checked at all. On top of that, `exclude` removes `tests/` entirely, and `main.py` + `scripts/build.py` (with `_frozen_patch.py` de-facto included per RT-8) account for 560 lines of the startup and build path.
**Why it's debt:** `invoke mypy-check` passing is close to meaningless as a signal, which is dangerous because it is one of only three CI gates. RT-1 (two module names that don't resolve) and RT-2 (a hardcoded 3.11 path) both live in `scripts/build.py`, inside the excluded region — the type checker was never given a chance. `warn_return_any = true` (line 124) is largely inert for the same reason.
**Fix:** Flip `check_untyped_defs = true` and fix the fallout incrementally, or adopt per-module `[[tool.mypy.overrides]]` to ratchet strictness package by package starting with `storage/` and `config/`. Drop `main.py`/`scripts/build.py` from the exclude list — they are 416 lines of the most fragile, least-tested code in the repo.

#### RT-10. The legacy top-level config duplicates the `default` profile and has already drifted — `Medium` / `S`
**Where:** `config/app_info.yaml` vs `config/profiles/default/app_info.yaml`; `config/pipeline_definitions.yaml` vs `config/profiles/default/pipeline_definitions.yaml`
**What:** `config/pipeline_definitions.yaml` and `config/profiles/default/pipeline_definitions.yaml` are **byte-identical** (230 lines each). `config/app_info.yaml` and `config/profiles/default/app_info.yaml` are 58 lines each and differ by exactly one word, on line 23: the top-level copy says "Goodness of Pronunciation (PLLR) scores", the profile copy says "(GOP) scores". `AGENTS.md:22-23` labels the top-level pair "Legacy fallback metadata".
**Why it's debt:** 288 duplicated lines with a live divergence already in them, and the divergence is in user-visible introduction text. The active profile is `explanatory` (`config/profile.txt`), so nobody notices which copy of the "default" text is stale. Anyone editing pipeline definitions must remember to edit two identical files or the fallback silently rots further.
**Fix:** Delete the two top-level files and make `get_active_profile()`'s fallback (`src/voxkit/config/app_config.py:52`, already returns `"default"` when `profile.txt` is missing) the only fallback path. If a genuine legacy path must remain, symlink or generate them rather than maintaining copies.

#### RT-11. Documentation drift across README, CONTRIBUTING, BUILD, AGENTS, and package metadata — `Medium` / `M`
**Where:** eight verified sites
**What:**
- `README.md:6,7,14,15,16,17` — all six badge URLs point at `BrainBehaviorAnalyticsLab/PyPLLR_GUI`, while `README.md:53` tells you to clone `BrainBehaviorAnalyticsLab/voxkit-desktop`. Every badge and every badge link is therefore either broken or reporting a different repository's status.
- `pyproject.toml:5` — `name = "pypllr-gui"`, the old name, while `[project.urls]` (lines 60-62) all point at `voxkit-desktop`. This is why the untracked build dir is `src/pypllr_gui.egg-info/`.
- `README.md:75,81` — the BibTeX and APA citation blocks are literally `<TODO>`, in a research tool whose entire pitch (`docs/RESEARCH.md`) is academic use.
- `README.md:34-40` — "Project Structure" lists five packages and omits `services/`, which `AGENTS.md:17` does include.
- `docs/CONTRIBUTING.md:52` — links `[TESTING.md](./TESTING.md)`; `docs/` contains only ARCHITECTURE, BUILD, CONTRIBUTING, RESEARCH.
- `docs/BUILD.md:24` — "`config/startup_config.py`'s `startup_routine()`"; the file is `src/voxkit/config/startup_config.py`.
- `docs/BUILD.md:45-47` — "It also isn't retried automatically on next launch … retry it manually via the **Repair/Reinstall MFA Environment** button." `main.py:143-145` says the opposite in a comment written specifically to record the change: "Gated on the environment being missing rather than on first launch, so a failed or interrupted setup is retried instead of being lost forever."
- `AGENTS.md:26` — "docs/ ARCHITECTURE.md, CONTRIBUTING.md, RESEARCH.md" omits `BUILD.md`, the largest and most operationally important doc in the folder (12KB).

**Why it's debt:** The BUILD.md/main.py contradiction is the costly one — it will send the next person debugging a failed MFA provision down the wrong path, and BUILD.md is otherwise the highest-signal document in the repo. The rest is credibility drag: a public-facing README whose badges are all wrong and whose citation block says `<TODO>` undermines a tool asking researchers to depend on it. (Credit where due — the `invoke` command table at `AGENTS.md:53-68` was verified command-by-command against `tasks.py` and every entry is accurate.)
**Fix:** Sweep the eight sites. Rename the distribution to `voxkit` in `pyproject.toml:5`. Either write `docs/TESTING.md` or point the link at the testing section of `CONTRIBUTING.md` itself (lines 56-61 already cover it). Add a "docs match code" line to the release-branch PR checklist.

#### RT-12. `invoke generate-documentation` dumps generated HTML into the tracked `docs/` directory — `Medium` / `S`
**Where:** `tasks.py:267`; `.github/workflows/sync-docs.yml:28`; `.gitignore`
**What:** The task runs `pdoc -o docs src/voxkit`, writing `index.html`, `voxkit.html`, `search.js`, and a per-module tree straight into `docs/`, which holds the four tracked markdown files. `git check-ignore docs/index.html` confirms nothing in `.gitignore` covers it. The CI workflow does the same job correctly, into `./docs_output`.
**Why it's debt:** Anyone following `AGENTS.md:61` ("`invoke generate-documentation` | Build pdoc HTML into `docs/`") pollutes their working tree with dozens of untracked HTML files sitting next to the hand-written docs, and it is one careless `git add docs/` from being committed. The local task and the CI job also disagree about the output location for no reason.
**Fix:** Change `tasks.py:267` to `-o docs_output` to match CI, and add `docs_output/` to `.gitignore`. Update the `AGENTS.md:61` table row.

#### RT-13. Shipped release metadata is stale by four minor versions — `Medium` / `S`
**Where:** `config/app_info.yaml:33-45` (and the identical `config/profiles/default/` and `config/profiles/explanatory/` copies)
**What:** `config/VERSION` reads `0.5.0`. All three `app_info.yaml` files carry `release_date: "2026-02-10"` and a `release_notes` block whose first line is `v0.1.0 - Initial Configurable Release`, describing initial-release features ("Declarative pipeline configuration via YAML", "Startup routines for automated asset downloads").
**Why it's debt:** `AppConfig` overrides the YAML `version:` from `config/VERSION` (per `AGENTS.md:76`), so the app correctly reports 0.5.0 — but then displays release notes for 0.1.0 beside it. Users see a self-contradicting About panel, and there is no CHANGELOG anywhere in the repo (`ls CHANGELOG*` → no matches) to consult instead, despite `main_merge.md:25` carrying a "Changelog updated" checkbox.
**Fix:** Either update `release_date`/`release_notes` as part of the version-bump procedure documented in `AGENTS.md:70-79`, or remove both keys from the YAML and render release notes from a real `CHANGELOG.md`.

#### RT-14. The target Python version is declared four different ways — `Medium` / `S`
**Where:** `.python-version:1`; `pyproject.toml:9`, `:72`, `:122`; `uv.lock:4-9`
**What:** `.python-version` says `3.11.9`. `pyproject.toml:9` says `requires-python = ">=3.11"`. `[tool.ruff] target-version = "py310"` (line 72) — *older* than the floor the project declares. `[tool.mypy] python_version = "3.11"` (line 122). `uv.lock:4-9` carries resolution markers up to `python_full_version >= '3.15'`. No CI workflow pins a Python version at all (none of the five sets up `actions/setup-python` or passes `--python`).
**Why it's debt:** Ruff at `py310` will not flag 3.11-only syntax as an upgrade opportunity and applies 3.10-era rule behavior to a 3.11+ codebase. More concretely, `requires-python = ">=3.11"` invites a contributor onto 3.12/3.13, which then silently breaks the macOS build (RT-2) and leaves them on a resolution CI never exercises.
**Fix:** Set `target-version = "py311"`. Decide whether >=3.11 or ==3.11.x is the real contract; if the latter, tighten `requires-python` to `>=3.11,<3.12` so the RT-2 hardcode is at least honest. Consider pinning `python-version` explicitly in the workflows so CI's interpreter is not an implicit detail of `setup-uv`.

#### RT-15. `sync-docs.yml` runs on a macOS runner, has no `permissions` block, and pushes to another repo with a broad PAT — `Medium` / `S`
**Where:** `.github/workflows/sync-docs.yml:10`, `:22-24`, `:30-52`
**What:** `runs-on: macos-latest` for a job that only runs `pdoc` and `cp`. The workflow has no top-level `permissions:` key (the other four all set `permissions: contents: read`). It checks out `BrainBehaviorAnalyticsLab/voxkit-web` with `secrets.PRIVATE_REPO_TOKEN` and pushes directly to its `main` (line 52). Note line 24 uses `https://${{ secrets.PRIVATE_REPO_TOKEN }}@github.com/` while the other four workflows use the `x-access-token:` form — an inconsistency in how the same secret is applied.
**Why it's debt:** macOS runners bill at 10× Linux for a job with no macOS-specific need. The same `PRIVATE_REPO_TOKEN` used to read four dependency repos also has write access to `voxkit-web` main and is exposed to a workflow with default (write-all, absent an org-level default) `GITHUB_TOKEN` permissions. There is also no `if: success()` guard between pdoc generation and the `rm -rf voxkit-web/public/docs/*` at line 42, though `set -e` semantics in the multi-step form do cover the common case.
**Fix:** Switch to `ubuntu-latest`, add an explicit `permissions: contents: read`, and replace the direct push with a PR into `voxkit-web` (or a deploy key scoped to that one repo) so the docs token is not also the dependency-fetch token.

#### RT-16. Repository governance and end-user onboarding are absent — `Low` / `M`
**Where:** repo root and `.github/`; `README.md:43-66`
**What:** Verified missing: `CHANGELOG.md`, `.github/dependabot.yml`, `.github/CODEOWNERS`, `SECURITY.md`. `README.md` has exactly four top-level sections — Appendix, Project Structure, Developers, Citation, License — and no Installation or Download section; the only "getting started" path is `git clone` + `invoke setup`. Both GitHub Actions in use are a major version behind (`actions/checkout@v4`, `astral-sh/setup-uv@v3`, across all five workflows). System prerequisites are also undocumented: `tasks.py:57` tells you to install `entr` for `invoke watch` only after you've already run the task, and the Ubuntu Qt library list at `.github/workflows/tests-ubuntu.yml:27-45` (17 packages including `libxcb-cursor0`, which `tasks.py:141` separately warns about at build time) appears in no onboarding doc.
**Why it's debt:** A desktop app for non-technical speech pathology researchers has no README path that ends in a running application — only a developer path. No dependabot on a dependency tree containing `torch`, `datasets`, and four git forks means security updates arrive only when someone happens to run `uv lock --upgrade`. No CODEOWNERS on a two-org collaboration means review routing is tribal knowledge.
**Fix:** Add a Download/Install section to `README.md` pointing at Releases (blocked on RT-3). Add `dependabot.yml` for `github-actions` and `uv` ecosystems. Add `CODEOWNERS`. Bump the two actions to `@v5`/`@v6`. Move the Ubuntu Qt package list from the workflow into `docs/CONTRIBUTING.md`.

#### RT-17. Three packages under `src/voxkit/` have no `__init__.py` — `Low` / `S`
**Where:** `src/voxkit/services/`, `src/voxkit/gui/pages/`, `src/voxkit/gui/frameworks/`
**What:** Every other directory under `src/voxkit/` has one; these three are implicit namespace packages. `src/voxkit/services/` contains `mfa.py` and `mfa_provision.py` and is listed as a first-class layer in `AGENTS.md:17`. They *are* picked up by the build (`src/pypllr_gui.egg-info/SOURCES.txt:71-72` lists both service modules) because `[tool.setuptools.packages.find]` defaults `namespaces = true` — so this is not currently breaking anything.
**Why it's debt:** It depends on an implicit setuptools default staying true, and it breaks the one-look-tells-you-everything property of the tree. `src/voxkit/__init__.py:17` eagerly imports `analyzers, config, engines, gui, storage` — notably *not* `services`, so `services` is also absent from pdoc output and from the `__all__` list at lines 31-40, meaning the layer documented in ARCHITECTURE.md never appears in the generated API docs.
**Fix:** Add the three `__init__.py` files with a one-line docstring each, and add `services` to the eager-import line and `__all__` in `src/voxkit/__init__.py` so it shows up in pdoc alongside the other layers.

#### RT-18. The coverage badge is a tracked artifact nothing displays — `Low` / `S`
**Where:** `assets/coverage.svg`; `tasks.py:255-261`; `AGENTS.md:60`
**What:** `assets/coverage.svg` is tracked in git and regenerated by `invoke generate-coverage-badge`, which is a documented task. `grep -rn "coverage.svg"` over all markdown, YAML, Python, and TOML finds it referenced **only** in `tasks.py:260-261`, `pyproject.toml:89` (a ruff exclude for a `.svg` file, which ruff would never read anyway), and the `AGENTS.md:60` command table — **never in `README.md`**, whose badge rows (lines 6-17) list release, downloads, Jira, GitHub Projects, ShredGuard, and four CI statuses.
**Why it's debt:** A checked-in binary artifact that is manually regenerated, never rendered, and goes stale the moment anyone forgets — plus a documented task whose output has no consumer. Coverage is also not measured in CI at all (`invoke run-tests` runs plain `pytest tests/`, `tasks.py:244`), so the number the badge would show is nobody's responsibility.
**Fix:** Either add the badge to the README block and generate it in CI, or delete `assets/coverage.svg`, the `generate-coverage-badge` task, the `genbadge[coverage]` dev dependency (`pyproject.toml:48`), and the `AGENTS.md` row.

### Architectural observations

**The build chain has no single source of truth for what gets bundled.** The dependency graph is `tasks.py` → `scripts/build.py` → PyInstaller (+ `hooks/`) → `installer/`, and knowledge leaks across every hop. `scripts/build.py:141-163` hardcodes a 22-entry hidden-import list; `hooks/hook-speechbrain.py` and `hooks/hook-Wav2TextGrid.py` each independently `collect_submodules` for packages that *also* appear in that list; `hooks/hook-typeguard.py` uses `collect_all` for a package that is *also* patched at runtime by `_frozen_patch.py:12-25`. Three mechanisms, three files, one concern. The generated `VoxKit.spec` (untracked, correctly gitignored) shows the collapsed result and is the only place where the full picture exists — but it exists only after a successful local build, with absolute paths baked in (`/Users/beckettfrey/Repos/voxkit-desktop/config`), so it can never be the artifact of record. RT-1 is the direct consequence: the hidden-import list drifted from reality and nothing anywhere could notice.

**`main.py` carries application logic that its own tooling exempts from checking.** Lines 52-111 implement conda discovery across six candidate install locations, Qt plugin-path resolution, and environment construction — genuine behavior that determines whether MFA alignment works at all — inside a file excluded from ruff (`pyproject.toml:85`), mypy (`:129`), and coverage (`:164`). The exemption is justified as "build/entry shim" (`AGENTS.md:88`), but the file stopped being a shim some time ago. The same is true of `scripts/build.py` at 250 lines. Note also `main.py:150-155`, which loads `AppConfig`/`PipelineConfig` from the profile path when `sys._MEIPASS` is set — this is redundant, since `VoxKitGUI.__init__` already falls back to `get_app_config()`/`get_pipeline_config()` (`src/voxkit/gui/__init__.py:224-225`) and those go through the same `get_profile_config_path()` resolution (`src/voxkit/config/app_config.py:30-36`). Two paths to the same config, one of which only executes in frozen builds — so the dev-mode path is the one that gets exercised and the frozen-mode path is the one that ships.

**Windows is the only platform with a complete story, and the asymmetry is undocumented as a risk.** `vendor/micromamba/` contains only `micromamba.exe` + three MSVC DLLs; `config/mfa-env/` contains only `aligner-win-64.lock`. `docs/BUILD.md:152-156` frames mac/Linux lockfiles as "a natural follow-up… not required today," and the fallback is honest (`lockfile_path()` returns `None` → user-managed conda). But combined with RT-2 (macOS bundles are ad-hoc signed and un-notarized) and RT-3 (no CI build for any platform), the practical state is that macOS and Linux users get an app that cannot do forced alignment out of the box *and* may not launch past Gatekeeper. The three-platform test matrix in CI creates an impression of parity that the distribution story does not match.

**`except Exception` is load-bearing in the persistence layer.** 22 of the repo's 58 broad catches sit in `src/voxkit/storage/` — the layer `docs/ARCHITECTURE.md:34-42` designates as the Model, accessed directly by views with no controller between them. Combined with RT-6 (the diagnostic that would explain the swallow goes to `/dev/null` in the shipped build), a storage failure surfaces to the user as a silently missing dataset row. `AGENTS.md:103` already identifies this exact anti-pattern in a different file — "`_ensure_mfa_server_running` … deliberately ignores return codes, which hides both failures" — which suggests the pattern is recognized but has not been swept. The `storage/` module agent owns the per-site detail; the cross-cutting point is that the "views talk straight to storage" architecture makes storage's error contract the app's error contract, and that contract is currently "return `None`, print to a stream nobody reads."


---

## Module: `src/voxkit/storage/`

**Health:** Functional but structurally soft — three correctness-grade defects (a lying `local` flag, non-atomic cross-thread metadata writes, a `ModelMetadata` type that has two runtime shapes) sit under a layer of inconsistent error contracts and hardcoded path strings. | **Files:** 6 | **LOC:** 1967 | **Findings:** 18 (3 High / 13 Medium / 2 Low)

This is VoxKit's model layer: it owns `~/.voxkit/`, generates timestamp IDs, and does CRUD on three JSON artifact formats (`voxkit_dataset.json`, `voxkit_model.json`, `voxkit_alignment.json`) plus the directory trees around them. Per `AGENTS.md` the GUI reads it directly with no controller, and engine work runs in `QThread` workers — so this module is simultaneously a cross-thread mutation point and a GUI-facing API, and it is hardened for neither. The dominant shape of the debt is *contract drift*: docstrings, TypedDict annotations, and the `local` flag all describe behavior the code stopped implementing, while every persisted format is schema-less and every write is a truncate-in-place. A secondary theme is that the three submodules were clearly written independently — `datasets.py`, `models.py`, and `alignments.py` disagree on error handling, path construction style, and case sensitivity for the same concepts.

### Findings

#### ST-1. `local` flag means two different things, silently corrupting `tg_path` on dataset import — `High` / `M`
**Where:** `src/voxkit/storage/alignments.py:203-205`, `src/voxkit/storage/alignments.py:78-79`, `src/voxkit/storage/datasets.py:475`
**What:** `AlignmentMetadata` documents `local` as "Whether TextGrid files are stored locally (cached) or at original path." `create_alignment` sets:
```python
local = dataset_metadata["cached"]
tg_path = alignment_root / "textgrids"
```
i.e. `tg_path` is *always* inside the alignment directory, but `local` is copied from the dataset's `cached` flag. So an automatic alignment on a **non-cached** dataset gets `local=False` while its TextGrids genuinely live locally. `create_hand_alignment` (`alignments.py:328-333`) *does* honor the documented meaning (`local=False` → `original_path/textgrids`), so the two creators disagree.

`_rewrite_imported_alignments` then trusts the flag:
```python
if not alignment_metadata.get("local"):
    continue
```
**Why it's debt:** Export→import of a non-cached dataset leaves every automatic alignment's `tg_path` pointing at the *source machine's* `~/.voxkit/datasets/<old_id>/alignments/<id>/textgrids`. That path does not exist on the importing machine, so the viewer, comparison, PLLR, and training stackers (all of which read `alignment_meta["tg_path"]` raw — `viewer_stacker.py:1687`, `comparison_stacker.py:73`, `pllr_stacker.py:448`, `training_stacker.py:185`) silently show empty/missing TextGrids. The existing regression test `tests/storage/test_datasets.py:476` hand-writes `"local": True` into its fixture, so it cannot catch this. `delete_alignment`'s docstring (`alignments.py:595`) repeats the same false claim.
**Fix:** Make `local` derived, not copied: set `local = True` in `create_alignment` since it always owns its `textgrids` dir (or drop the field and have `_rewrite_imported_alignments` test `Path(tg_path).is_relative_to(dataset_root)` instead, which is what the rewrite actually needs to know). Add a test that creates an alignment on a `cached=False` dataset, exports, imports, and asserts the rewritten `tg_path`.

#### ST-2. Every metadata write is a non-atomic truncate-in-place, and reads race worker threads — `High` / `M`
**Where:** `src/voxkit/storage/alignments.py:516-529`, `src/voxkit/storage/datasets.py:356-358`, `src/voxkit/storage/models.py:220-230`, `src/voxkit/storage/utils.py:123-125`
**What:** Every persisted write is `open(path, "w")` + `json.dump(...)`. There is no `os.replace`, no temp-file-then-rename, no `fsync` anywhere in the module (verified: `grep -rn "os.replace\|NamedTemporaryFile\|fsync" src/voxkit/storage/` returns nothing). `update_alignment` is a read-modify-write with no lock:
```python
with open(metadata_path, "r", encoding="utf-8") as f:
    metadata = json.load(f)
...
with open(metadata_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=4)
```
This runs on a `WorkerThread` (`gui/workers/worker_thread.py:30` → `prediction_stacker.py:186` → `mfa_engine.py:182,188` / `w2tg_engine.py:178,186`) while the GUI thread concurrently calls `list_alignments`/`get_alignment_metadata` on the same files.
**Why it's debt:** A crash, force-quit, or full disk during any status update leaves a truncated JSON. `get_alignment_metadata` re-raises on parse failure (`alignments.py:485`), so a corrupt file becomes an unhandled exception in a GUI slot rather than a recoverable error. The GUI thread can also observe a zero-length file mid-write with no crash at all — just a phantom "alignment disappeared". `AGENTS.md:98-105` already documents that users kill this app and hand-delete `~/.voxkit` mid-run, so the crash window is not hypothetical.
**Fix:** Route every write through one `utils.save_json` that writes to `path.with_suffix(".tmp")` then `os.replace()`. Add a module-level `threading.RLock` (or per-alignment lock) around the read-modify-write in `update_alignment`/`update_dataset_metadata`/`update_model_metadata`.

#### ST-3. `ModelMetadata` annotates `Path` but is `str` at rest; `create_model` mkdirs the "entrypoint file" as a directory — `High` / `M`
**Where:** `src/voxkit/storage/models.py:60-67`, `src/voxkit/storage/models.py:139-160`, `src/voxkit/storage/models.py:305-307`
**What:** Three separate problems in one type:
1. `ModelMetadata` declares `model_path: Path`, `data_path: Path`, `eval_path: Path`, `train_path: Path`. `create_model` returns real `Path` objects; `get_model_metadata` returns `json.load(f)` (`models.py:306`), i.e. **`str`**. Same TypedDict, two runtime shapes depending on which function you called. mypy cannot see it because `json.load` is `Any`.
2. `model_path = model_root / "entrypoint.model"` (line 139) is then `model_path.mkdir(parents=True, exist_ok=False)` (line 157) — the "model entrypoint file" is created as a **directory**.
3. `model_path=model_path.with_suffix(".model")` (line 148) is a no-op — the path already ends in `.model`.

The docstring at line 127 claims "If source_path is a .model file or directory, copies via copytree", but `shutil.copytree` requires a directory source, so the `.model`-file branch raises `NotADirectoryError`.
**Why it's debt:** Callers must defensively re-wrap (`Path(model_metadata["model_path"])` at `mfa_engine.py:156`, `Path(model_meta["model_path"])` at `w2tg_engine.py:208`) while others pass it straight through as a string (`w2tg_engine.py:159,174`). Worse, `mfa_engine.py:217-251` carries an explicit block labelled `# ========= TEMP FIX FOR MFA MODEL EXTENSION ========` whose comment says *"This should ideally be handled in the storage/models.py create_model function"* — it rewrites `.model`→`.zip`, hand-serializes `voxkit_model.json` itself, and `touch()`es an empty file, all to work around this API.
**Fix:** Declare the path fields as `str` (they are strings on disk) and expose typed accessors returning `Path`, or normalize on read in `get_model_metadata`/`list_models`. Stop `mkdir`ing `entrypoint.model`; create the model root only and let the source copy decide file-vs-directory. Then delete the mfa_engine TEMP FIX.

#### ST-4. Dead code: an unreachable error branch and an uncalled path helper — `Medium` / `S`
**Where:** `src/voxkit/storage/alignments.py:181-183`, `src/voxkit/storage/models.py:86-98`
**What:** `create_alignment` opens with:
```python
model_metadata = get_model_metadata(engine_id, model_id)
if not model_metadata:
    return False, f"Model '{model_id}' for engine '{engine_id}' not found"
```
But `get_model_metadata` (`models.py:299-304`) **raises `FileNotFoundError`** when the model is missing — it never returns a falsy value. The guard is unreachable, and the docstring's promise of `(False, error_message)` for a missing model is false. `tests/storage/test_alignments.py:120-136` confirms it, asserting `pytest.raises(FileNotFoundError)`.

Separately, `_get_models_root(engine_id)` at `models.py:86` has zero call sites anywhere in `src/`, `tests/`, or `scripts/` (verified by grep). `create_model:130` and `list_models:258` each rebuild the identical path inline instead.
**Why it's debt:** The unreachable branch means `mfa_engine.align`/`w2tg_engine.align` get an exception where they expect a `(False, msg)` tuple — the `if not result: raise ValueError(...)` handler at `mfa_engine.py:164` is bypassed and the user sees a raw `FileNotFoundError`. The dead helper invites the next contributor to "fix" it and wonder why nothing changes.
**Fix:** Pick one contract for `get_model_metadata` (returning `ModelMetadata | None` matches `get_dataset_metadata`) and make the guard real, or delete the guard and document the raise. Delete `_get_models_root` or make `create_model`/`list_models` use it.

#### ST-5. Four sibling functions, four different error contracts for "metadata is unreadable" — `Medium` / `M`
**Where:** `src/voxkit/storage/datasets.py:127-135`, `datasets.py:287-289`, `datasets.py:305-321`, `alignments.py:483-485`, `models.py:415`
**What:** The same failure mode is handled four incompatible ways:
- `datasets._get_dataset_metadata:134` — `except Exception: return None`. A corrupt/unparseable `voxkit_dataset.json` is indistinguishable from an absent one.
- `datasets.get_dataset_metadata:287` — catches, `print`s, returns `None`.
- `alignments.get_alignment_metadata:483-485` — catches, `print`s, then `raise e` (re-raises).
- `models.get_model_metadata:301` — raises `FileNotFoundError` and never catches.

Additionally `list_datasets_metadata` resolves its root **outside** its own `try` (`datasets.py:307` vs the `try:` at 309), so its documented "Returns empty list on error" (line 303) doesn't hold if `~/.voxkit/datasets` is gone — `_get_datasets_root` uses `mkdir(parents=False)` (`datasets.py:83`) and will raise `FileNotFoundError`. Same pattern in `delete_dataset:393` and `export_dataset:430`, both outside their `try` blocks despite returning `Tuple[bool, str]`.

And `models.delete_model:415` calls `shutil.rmtree(model_path)` with **no** `try` at all, while `delete_dataset:402` and `delete_alignment:603` both wrap theirs — so a permission error deleting a model escapes as an exception into the GUI while the identical dataset/alignment operations return `(False, msg)`.
**Why it's debt:** Callers cannot reason about what any storage call does on failure without reading its body, so GUI code either over-catches or crashes. A corrupt dataset file surfaces to the user as "Dataset not found", sending them to look for the wrong problem.
**Fix:** Define one convention (recommend: `get_*` returns `T | None` and logs; `create_/update_/delete_` returns `(bool, str)` and never raises) and enforce it across all three submodules. Move root resolution inside the `try` in `list_datasets_metadata`, `delete_dataset`, `export_dataset`.

#### ST-6. Directory and filename literals hardcoded at 25+ sites while `constants.py` sits half-empty — `Medium` / `S`
**Where:** `src/voxkit/storage/constants.py:17-21` vs `datasets.py:128,209,312,356`; `alignments.py:219,357,439,514,562` + `datasets.py:465`; `models.py:161,219,266,302,441,492`; `datasets.py:114,215,520`; `alignments.py:204,330,332,420` + `datasets.py:478`
**What:** `constants.py` defines only `STORAGE_ROOT`, `MODELS_ROOT`, `DATASETS_ROOT`, `ALIGNMENTS_ROOT`, `SUPERSET_AUDIO_EXTENSIONS`. The rest of the layout is string literals scattered through the code: `"voxkit_dataset.json"` ×4, `"voxkit_alignment.json"` ×6, `"voxkit_model.json"` ×6, `"textgrids"` ×5, `"cache"` ×3, plus `"entrypoint.model"`/`"entrypoint.zip"` (`models.py:139,171`), `"data"`/`"eval"`/`"train"` (`models.py:140-142`), `".first_launch_complete"` (`utils.py:102,110`), and the `f"{analysis_method.lower()}_summary.csv"` naming convention (`datasets.py:221`, matched by a glob in `datasets_page.py:936`).
**Why it's debt:** Renaming any artifact requires a repo-wide grep with no compiler help, and the literals have already escaped the module — `mfa_engine.py:232` hardcodes `"voxkit_model.json"`, `faster_whisper_engine.py:116` hardcodes `"cache"`, `viewer_stacker.py:147-148` hardcodes `"cache"`. Constants also fail to prevent typos in the string, which is exactly the class of bug the file exists to prevent.
**Fix:** Move all of them into `constants.py` (`DATASET_METADATA_FILE`, `ALIGNMENT_METADATA_FILE`, `MODEL_METADATA_FILE`, `CACHE_DIR`, `TEXTGRIDS_DIR`, `MODEL_ENTRYPOINT`, …) and import from there in every submodule.

#### ST-7. Callers reach around the storage API — private helpers and hand-built paths outside the module — `Medium` / `M`
**Where:** `src/voxkit/engines/faster_whisper_engine.py:112-118`, `src/voxkit/gui/pages/datasets/datasets_page.py:925`, `src/voxkit/gui/pages/models/utils.py:110`, `src/voxkit/engines/mfa_engine.py:232-242`
**What:** Three call sites outside `storage/` use underscore-private helpers:
- `faster_whisper_engine.py:113` calls `datasets._get_dataset_root(dataset_id)` and then reimplements `get_dataset_data_path` inline (`audio_root = dataset_root / "cache"` else `Path(dataset_meta["original_path"])`) — a verbatim duplicate of `datasets.py:104-115`. Every other engine and stacker uses the public helper (`mfa_engine.py:152`, `w2tg_engine.py:165`, `training_stacker.py:147`, `viewer_stacker.py:1581`, `comparison_stacker.py:618`, `correct_alignments_stacker.py:682`).
- `datasets_page.py:925` calls `datasets._get_dataset_root` to glob `*_summary.csv`.
- `models/utils.py:110` calls `models._get_model_root` to build an export copy.

And `mfa_engine.py:232-242` opens and rewrites `voxkit_model.json` by hand instead of calling `models.update_model_metadata`.
**Why it's debt:** The `_`-prefix promises the module can refactor these freely; it can't. The duplicated `cache` resolution in `faster_whisper_engine` is exactly the bug `mfa_engine.py:145-151`'s comment warns about ("passing the dataset root here buries every TextGrid under a spurious extra `cache/` level") — the fix was applied in one place and missed in the other.
**Fix:** Promote `_get_dataset_root` and `_get_model_root` to public (`get_dataset_root`, `get_model_root`) or add the narrow public helpers callers actually want (`get_dataset_analysis_csv(meta)`, `get_model_export_source(engine_id, model_id)`). Replace `faster_whisper_engine.py:112-118` with `datasets.get_dataset_data_path(dataset_meta)`.

#### ST-8. No schema version on any persisted format, and a hand-rolled migration already exists to prove it's needed — `Medium` / `M`
**Where:** `src/voxkit/storage/alignments.py:101-115`, `alignments.py:97-98`, `datasets.py:50-73`, `models.py:46-67`
**What:** None of the three TypedDicts carries a `schema_version`. `AlignmentMetadata` has already grown two `NotRequired` fields (`source_alignment_id`, `alignment_type`) and needs a bespoke reader to cope:
```python
def get_alignment_type(meta):
    if "alignment_type" in meta: return meta["alignment_type"]
    if meta["engine_id"] == HAND_ALIGNMENT_SENTINEL: return "hand"
    if meta["engine_id"] == CORRECTED_ALIGNMENT_SENTINEL: return "corrected"
    return "automatic"
```
whose own docstring says it exists for "alignments created by an earlier version of `create_corrected_alignment`". `DatasetMetadata.hand_alignments_path` is likewise newer than the format and is read via `.get()` in some places and `[]` in others.
**Why it's debt:** Every future field addition needs another ad-hoc `in meta` fallback in a new place, and there is no way to detect a *forward*-incompatible file (a newer VoxKit's artifact opened by an older one) — it just KeyErrors somewhere deep in the GUI. `import_dataset`/`import_models` accept arbitrary third-party directories with no version check at all.
**Fix:** Add `schema_version: int` to all three TypedDicts, write it on create, and add one `_migrate(meta)` per module called from every read path. Reject unknown-future versions with a clear message in `import_dataset`/`import_models`.

#### ST-9. Update functions silently drop unrecognized fields and report success — `Medium` / `S`
**Where:** `src/voxkit/storage/datasets.py:351-353`, `src/voxkit/storage/alignments.py:521-526`, `src/voxkit/storage/models.py:225-227`
**What:** Three different silent-no-op patterns, all returning `(True, "…updated successfully")`:
- `update_dataset_metadata` iterates a hardcoded whitelist `for field in ("description", "cached", "anonymize", "transcribed")` — passing `name` or `hand_alignments_path` is discarded.
- `update_alignment` uses `if key in metadata:` — so a field the alignment doesn't already have (e.g. adding `alignment_type` to a legacy record) is discarded.
- `update_model_metadata` uses `metadata[key] = str(value)` — coercing every value to a string, so a boolean update lands as `"True"` and an int as `"5"`.

**Why it's debt:** Callers get `True` and assume the write happened. `transcription_stacker.py:192,213` and `startup_config.py:69` all ignore the returned tuple. The whitelist is decoupled from `DatasetMetadata`'s actual keys, so adding a field to the TypedDict silently makes it un-updatable. The `str()` coercion in `update_model_metadata` actively corrupts non-string fields.
**Fix:** Validate keys against the TypedDict (`DatasetMetadata.__annotations__`) and return `(False, "unknown field: …")` for anything unrecognized. Drop the `str(value)` coercion in `update_model_metadata` — serialize `Path` only.

#### ST-10. `validate_dataset` is case-sensitive on extensions, mixes `os.path` with `pathlib`, and rescans each directory 3× — `Medium` / `S`
**Where:** `src/voxkit/storage/datasets.py:599-656`
**What:** In a module whose sibling docstring claims "All paths are managed using pathlib" (`alignments.py:31`, `models.py:30`), this function uses `os.listdir`/`os.path.join`/`os.path.isdir` throughout and only reaches for `Path` to get `.stem`. It calls `os.listdir(dataset_path)` at lines 605, 607, and 621 (three full scans), and `os.listdir(speaker_path)` at 630 and 636 (two scans per speaker). Extension matching is case-sensitive:
```python
audio_files = [f for f in os.listdir(speaker_path) if f.endswith(tuple(SUPERSET_AUDIO_EXTENSIONS))]
```
(the `tuple(...)` is also rebuilt inside the per-speaker loop). Compare `alignments.validate_hand_alignments:274`, which does the same job case-**in**sensitively: `f.suffix.lower() in _AUDIO_EXTS`.
**Why it's debt:** A corpus of `SPEAKER_01/UTT_001.WAV` fails registration with "No audio files found in speaker directory" — while the *same* corpus passes `validate_hand_alignments`. Clinical/legacy speech corpora routinely ship uppercase extensions. The repeated scans make registration of a large corpus noticeably slow over a network share, and this runs on the GUI's registration worker (`datasets_thread.py:55`).
**Fix:** Rewrite with a single `os.scandir` pass per directory using `Path.suffix.lower() in SUPERSET_AUDIO_EXTENSIONS`, matching `validate_hand_alignments`. Add a test with an uppercase-extension fixture.

#### ST-11. Unsanitized user-supplied dataset name is joined straight into an export path — `Medium` / `S`
**Where:** `src/voxkit/storage/datasets.py:439`
**What:** `dest_path = output_root / (dataset_meta["name"] + "_" + dataset_id)`. `name` comes from a free-text `FieldType.LINEEDIT` in the registration dialog (`datasets_page.py:689-696`) and is only checked for non-emptiness (`datasets_page.py:784`). It is never validated at write time in `create_dataset` either.
**Why it's debt:** A name containing `/` or `..` escapes `output_root`; a name containing `:`/`?`/`*`/`|` produces an opaque `OSError` on Windows (a supported platform — see `installer/windows/`); a trailing space or dot silently produces a different directory name on Windows. The failure surfaces as a generic `f"Failed to export dataset: {e}"`. `dataset_id` is safe (generated), but `name` is not.
**Fix:** Sanitize in `create_dataset` (reject or slugify path separators and reserved characters), and in `export_dataset` assert `dest_path.resolve().is_relative_to(output_root.resolve())` before copying.

#### ST-12. Circular dependency between `datasets` and `alignments`, papered over with a function-local import — `Medium` / `M`
**Where:** `src/voxkit/storage/datasets.py:226`, `src/voxkit/storage/alignments.py:45`
**What:** `alignments.py:45` does `from .datasets import _get_dataset_root, get_dataset_metadata` at module scope. `datasets.create_dataset` needs to go back the other way, so it hides the import inside the function body:
```python
if hand_alignments_path:
    from voxkit.storage.alignments import create_hand_alignment
```
Additionally `datasets._rewrite_imported_alignments` (`datasets.py:447-483`) reimplements alignment-metadata reading and writing by hand — hardcoding `"voxkit_alignment.json"`, `"textgrids"`, and the `local` semantics — rather than calling into `alignments`, precisely to avoid the cycle.
**Why it's debt:** The cycle is why ST-1 exists: `_rewrite_imported_alignments` has its own private copy of alignment layout knowledge that drifted out of sync with `create_alignment`. Function-local imports also hide import errors until the branch is taken at runtime.
**Fix:** Extract `_get_datasets_root`/`_get_dataset_root`/`_get_alignments_root`/`_get_alignment_root` into a `storage/paths.py` that neither module imports the other for, then let `datasets` import `alignments` at module scope and have `_rewrite_imported_alignments` use `alignments.list_alignments`/`update_alignment`.

#### ST-13. Importing the package has a filesystem side effect, contradicting the comment two lines above it — `Medium` / `S`
**Where:** `src/voxkit/storage/__init__.py:29-54`
**What:**
```python
# Import utils but don't call get_storage_root() at module import time
from . import alignments, datasets, models, utils
...
_ensure_storage_root()   # line 54 — calls get_storage_root() at module import time
```
`_ensure_storage_root` also `print`s on failure and does a bare `raise e` (re-raising with a rebuilt traceback rather than a plain `raise`).
**Why it's debt:** `AGENTS.md:89` notes that `src/voxkit/__init__.py` eagerly imports all subpackages, so `import voxkit` — for anything, including reading `__version__` — creates `~/.voxkit/` on the developer's real home directory. Every `tests/storage/*` module triggers it despite the tests monkeypatching `get_storage_root` to a temp path. The comment actively misleads the next reader about what the module does.
**Fix:** Delete line 54 and call `_ensure_storage_root()` from the app startup routine (`config/startup_config.py` already exists for this), or delete the stale comment and accept the eager behavior explicitly. Replace `print` + `raise e` with `logging` + bare `raise`.

#### ST-14. Storage tests write into a relative, non-gitignored directory in the repo root — `Medium` / `S`
**Where:** `tests/storage/test_setup.py:22-23`, `tests/storage/test_setup.py:16-19`
**What:**
```python
def mock_get_storage_root():
    return Path("./temp_test_storage_models")
```
and teardown does `shutil.rmtree(storage_root)` on that relative path. There is no `tests/conftest.py`, and `temp_test_storage_models` is absent from `.gitignore` (verified). `pytest-qt` and `tmp_path` are both available and used elsewhere in the suite (`tests/engines/test_base.py:70`, `tests/services/test_mfa_provision.py:15` both use `tmp_path`).
**Why it's debt:** Test artifacts land in the working directory, become untracked repo noise on any interrupted run, and cannot be run in parallel (`pytest -n`) because every storage test shares one fixed path. Because the path is relative, the tests only pass when pytest is invoked from the repo root — running `invoke run-tests` from a subdirectory silently targets a different location. The `rmtree` of a relative path is the kind of thing that goes wrong badly exactly once.
**Fix:** Add a `tests/storage/conftest.py` fixture that monkeypatches `get_storage_root` in `datasets`, `models`, and `utils` to a per-test `tmp_path`, and delete `mock_get_storage_root`.

#### ST-15. `import_models` leaves partial state on failure while `create_dataset`/`import_dataset` roll back — `Medium` / `S`
**Where:** `src/voxkit/storage/models.py:437-500`, contrast `datasets.py:234-241` and `datasets.py:561-566`
**What:** `import_models` loops over source directories and `return False, ...` on the first bad one (lines 443, 452, 461, 465, 498). Models copied in earlier iterations stay in `~/.voxkit/<engine>/train/` with fresh IDs and rewritten metadata. There is no cleanup block. Every other import/create in the module does roll back (`create_dataset:236-238` rmtrees the partial dataset, `import_dataset:562-564` rmtrees `dataset_dest`, `create_model:190-191`, `create_alignment:227-229`, `create_hand_alignment:364-365`, `create_corrected_alignment:446-447`).

Relatedly, the error strings returned are bare fragments (`f"{source_model_path.name} (missing metadata file)"`) with no leading verb, so the GUI shows the user something like `english_us_arpa (missing metadata file)`.
**Why it's debt:** A partially-failed bulk import leaves the models page in a half-imported state with no indication of which models landed, and re-running the import duplicates the successful ones. Contradicts the module-family invariant stated in `storage/__init__.py:26` ("Failed operations clean up partial changes").
**Fix:** Collect created destination paths and rmtree them in an `except`/failure path, or switch to a two-pass design (validate every source first, then copy). Prefix the failure messages with what failed.

#### ST-16. `import_dataset` validates a directory it may not need, and ships a debug `print` — `Medium` / `S`
**Where:** `src/voxkit/storage/datasets.py:519-524`, `datasets.py:544-545`
**What:**
```python
valid, valid_msg = validate_dataset(dataset_path / "cache", transcribed=transcribed_flag)
now = generate_unique_id()
print(now)
```
`validate_dataset` is called unconditionally, before the `if not dataset_metadata["cached"]` branch at line 534 decides whether the `cache` directory is even relevant. For a non-cached dataset the path doesn't exist, so the result is discarded (the `elif not valid` at 544 is only reached in the cached branch). For a cached dataset it is a full recursive listing of the entire corpus that runs *before* the cheap existence checks. `print(now)` is a leftover debug statement emitting a bare timestamp.
**Why it's debt:** Importing a large cached dataset does a redundant multi-scan of the corpus (see ST-10 for the per-directory cost), on the GUI thread in some paths. The stray `print` produces unexplained output in the packaged app's console.
**Fix:** Move the `validate_dataset` call inside the `else:` branch that actually consumes it. Delete `print(now)`.

#### ST-17. `print()` used for all diagnostics in a module that is neither GUI nor coverage-excluded — `Low` / `S`
**Where:** 24 sites: `models.py:136,188,235,273,278,331,339,357,367,371,375,379,408,414`; `datasets.py:240,288,320,472,483,524,565`; `alignments.py:484,572`; `__init__.py:50`
**What:** The project has `src/voxkit/config/logging_config.py` with a rotating file handler at `~/.voxkit/logs/voxkit.log` and a GUI log handler (`gui/components/log_handler.py`), and several modules use `logging.getLogger` (`analyzers/audio_format_profile.py`, `analyzers/clip_duration_statistics.py`, `config/startup_config.py`, `engines/w2tg_engine.py`, `gui/workers/startup.py`). `storage/` uses none of it. Several of the prints are pure debug noise: `print(f"Creating model at: {model_root}")` (`models.py:136`), `print(f"Attempting to delete model: …")` (`models.py:408`), `print(f"Deleting model at path: {model_path}")` (`models.py:414`), `print(now)` (`datasets.py:524`).
**Why it's debt:** In the PyInstaller build there is no console, so every storage-layer diagnostic is lost — including the swallowed exceptions from ST-5, which are the ones you most need when debugging a user's `~/.voxkit`. `AGENTS.md:96` explicitly calls out debugging opaque storage/MFA failures as a recurring support burden.
**Fix:** `logger = logging.getLogger(__name__)` per submodule; `logger.exception(...)` in the `except` blocks, `logger.debug(...)` for the trace lines, delete the pure-debug ones.

#### ST-18. Weak/missing type hints and a vestigial alias — `Low` / `S`
**Where:** `src/voxkit/storage/datasets.py:326`, `alignments.py:488`, `models.py:196`, `models.py:419`, `alignments.py:233`, `datasets.py:44`
**What:**
- `updates: dict` (bare, no parameters) in all three update functions — `update_dataset_metadata:326`, `update_alignment:488`, `update_model_metadata:196`.
- `def import_models(engine_id, new_models_root: Path)` — `engine_id` has no annotation at all, and the function has no explicit return-type problems only because `Tuple[bool, str]` is declared.
- `_AUDIO_EXTS = SUPERSET_AUDIO_EXTENSIONS` (`alignments.py:233`) — a bare re-alias with no added meaning, placed mid-file between two function definitions.
- `datasets.py:44` imports `List`, `Tuple` from `typing` and uses them alongside modern builtin generics (`list[dict[str, Any]]` at line 145, `tuple[Literal[True], …]` at line 148) in the same file. `alignments.py` and `models.py` do the same.

**Why it's debt:** `mypy` runs with `check_untyped_defs = false` (`pyproject.toml`), so an unannotated parameter turns off checking for that function body entirely — `import_models` is effectively unchecked. `dict` without parameters means no key/value checking on the very functions ST-9 shows are already too permissive.
**Fix:** `updates: dict[str, Any]`, `engine_id: str`, delete `_AUDIO_EXTS` in favor of the imported name, standardize on builtin generics (a one-shot ruff `UP` rule would enforce it if added to `select`).

### Cross-module notes

- **`utils.save_json` is duplicated in the engines layer.** `src/voxkit/engines/base.py:170-182` defines `_save_json` with a body functionally identical to `storage/utils.py:114-125` (mkdir parents, open "w", `json.dump(indent=4)`). Meanwhile `storage/`'s own submodules use neither — they all hand-roll `open()`+`json.dump` (with inconsistent `indent=2` in `datasets.py:211,358` vs `indent=4` everywhere else). One shared atomic writer would fix ST-2 for both layers at once. Belongs to `engines/`.
- **`config/logging_config.py:17` hardcodes `Path.home() / ".voxkit"`** instead of importing `storage.utils.get_storage_root()` / `storage.constants.STORAGE_ROOT`. If the storage root ever becomes configurable, logs silently split off to a different location. Belongs to `config/`.
- **`gui/pages/pipeline/viewer_stacker.py:147-148`** probes `tg_root / "cache" / …` when resolving TextGrids — hardcoding storage's `cache` directory name into the GUI's search order. Belongs to `gui/`.
- **`engines/mfa_engine.py:217-251`'s "TEMP FIX"** is self-documented debt pointing at ST-3; it cannot be removed until `create_model` stops creating `entrypoint.model` as a directory. Coordinate the two.
- **Duplicated test class:** `tests/storage/test_alignments.py` defines `TestGetAlignmentType` twice — nested at line 414 and again at module level at line 830 — with near-identical assertions. Harmless but confusing; one should go.
- **Untested public surface in this module:** `create_hand_alignment`, `validate_hand_alignments`, `get_dataset_data_path`, and `download_and_copy_huggingface_model` have no tests (grep across `tests/` returns nothing for the first three; the last is network-bound and reasonably skipped). `create_hand_alignment` is reachable from the primary registration flow via `create_dataset(hand_alignments_path=…)` (`datasets.py:226`), and `validate_hand_alignments` gates it in the GUI at `datasets_page.py:792` — both are user-facing and unverified.


---

## Module: `src/voxkit/engines/`

**Health:** Leaky — the base class abstracts JSON settings, not engines; the real alignment lifecycle is copy-pasted and has already diverged | **Files:** 6 | **LOC:** 1164 | **Findings:** 18 (6 High / 8 Medium / 4 Low)

`src/voxkit/engines/` wraps three external speech toolkits (Montreal Forced Aligner via subprocess, Wav2TextGrid via in-process Python, Faster-Whisper via CTranslate2) behind an `AlignmentEngine` ABC and an `EngineManager` singleton. `base.py` is honest about only half its job: it owns settings persistence/validation and tool discovery (`has_tool`, `get_settings`, `get_settings_config`), which the GUI call sites do use polymorphically — but the actual work each engine performs (create storage record → run tool → mark completed/failed) is duplicated verbatim between `mfa_engine.align` and `w2tg_engine.align` and the two copies have already drifted apart in error handling. The sharpest debt is not structural though: three separate settings-plumbing defects mean user-visible settings are silently ignored or silently wrong (`EN-2`, `EN-3`, `EN-4`), and the module's ~35 `print()` diagnostics are provably discarded in the shipped windowed build. There are no tests for any of the three engines.

### Findings

#### EN-1. `base.py` abstracts settings, not engines — the alignment lifecycle is copy-pasted and diverging — `High` / `L`
**Where:** `src/voxkit/engines/mfa_engine.py:138-193` vs `src/voxkit/engines/w2tg_engine.py:131-191`; `src/voxkit/engines/base.py:80-114`
**What:** Both `align()` implementations run the identical six-step skeleton: resolve dataset metadata + None-check, resolve corpus dir via `datasets.get_dataset_data_path(...)` + None-check, fetch `models.get_model_metadata(...)["model_path"]`, call `alignments.create_alignment(engine_id=self.id, model_id=..., dataset_id=...)`, `assert not isinstance(msg, str)`, then `try: <tool call>; alignments.update_alignment(..., {"status": "completed"}) except: alignments.update_alignment(..., {"status": "failed"}); raise`. Even the "must be the directory that *directly* contains the speaker subdirs" comment is duplicated (`mfa_engine.py:147-151`, `w2tg_engine.py:161-164`). `base.py` provides none of this — its only abstract members are `align`, `train_aligner`, and the two validators, all of which are pure `raise NotImplementedError()` stubs. The copies have already diverged: MFA raises `ValueError` when `create_alignment` fails (`mfa_engine.py:164-165`) while W2TG `return`s (`w2tg_engine.py:143-145`, see EN-5); W2TG calls `self.get_settings("align")` up front, MFA never does (see EN-3); W2TG emits `logger.exception` on failure (`w2tg_engine.py:185`), MFA emits nothing.
**Why it's debt:** Any change to the alignment lifecycle — a new status value, cancellation, progress reporting, a cleanup step — has to be made twice and correctly, and the record already shows that doesn't happen. Adding a fourth engine means transcribing the skeleton a third time.
**Fix:** Turn `align` into a template method on `AlignmentEngine`: base resolves dataset/model/corpus paths, creates the alignment record, and owns the completed/failed status transitions; subclasses implement a narrow `_run_align(corpus_dir: Path, model_path: Path, output_dir: Path, settings: dict) -> None`. Same treatment for `train_aligner` and the model-record lifecycle.

#### EN-2. Runtime fallback defaults duplicate the `FieldConfig` defaults and have already drifted — `High` / `S`
**Where:** `src/voxkit/engines/w2tg_engine.py:88` (`default_value=True`) vs `src/voxkit/engines/w2tg_engine.py:176` (`settings.get("use_speaker_adaptation", False)`)
**What:** Every `settings.get(key, default)` call restates the `default_value` already declared in the `FieldConfig`. Commit `3f678bb` ("Default W2TG 'Use Speaker Adaptation' to on") changed only the `FieldConfig` at line 88 and left the runtime fallback at line 176 at `False`. So when the key is absent from `W2TGENGINE/aligner/aligner_settings.json`, alignment runs with speaker adaptation **off** while the UI says on. Worse, `align_dirs` in the vendored Wav2TextGrid (`.venv/.../Wav2TextGrid/wav2textgrid.py:113-116`) raises `ValueError("The default aligner model requires speaker adaptation...")` when `use_speaker_adaptation=False` and the model is `pkadambi/Wav2TextGrid` — so the drift converts a silent misconfiguration into a hard failure on the default model. The same double-declaration pattern exists at `w2tg_engine.py:236,242,243,246` and `faster_whisper_engine.py:124-127` (currently in agreement, but unguarded).
**Why it's debt:** Defaults are declared in two places with no mechanism keeping them in sync, and the divergence is invisible to tests, mypy, and ruff. This one already shipped.
**Fix:** Have `get_settings` merge missing keys from `_get_default_settings(cfg)` (see EN-4) so callers can use plain `settings[key]` and delete every literal fallback.

#### EN-3. MFA's `dictionary`, `file_type`, `num_iterations`, and `use_gpu` settings are never read — `High` / `M`
**Where:** `src/voxkit/engines/mfa_engine.py:76-127` (declared), `mfa_engine.py:176-181` and `mfa_engine.py:264-269` (call sites)
**What:** `MFAEngine` exposes four settings fields the user can edit and VoxKit persists, but `align()` calls `run_mfa_align(corpus_dir=..., model_path=..., output_dir=..., conda_path=...)` and `train_aligner()` calls `run_mfa_adapt(corpus_dir=..., base_model_path=..., output_model_path=..., conda_path=...)` — neither passes `dictionary_name`, `num_iterations`, or anything derived from `file_type`/`use_gpu`. `src/voxkit/services/mfa.py:243` and `:294-295` therefore always use the defaults `dictionary_name="english_us_arpa"` and `num_iterations=1`. A repo-wide grep for `"dictionary"`, `num_iterations`, `file_type`, and `use_gpu` confirms the only MFA consumer of its own settings is `_configured_conda_path` reading `conda_path`. `MFAEngine.align` never calls `self.get_settings("align")` at all.
**Why it's debt:** A researcher who sets `dictionary: english_mfa` gets ARPAbet alignments anyway, with no warning — silently wrong scientific output, and the UI actively misleads. `num_iterations` is documented in the module docstring (`mfa_engine.py:15`) as a real train setting.
**Fix:** Read `self.get_settings(tool_type)` in both methods and forward `dictionary_name` and `num_iterations` to the service functions; either wire `file_type`/`use_gpu` to real MFA flags or delete the fields and the docstring lines that advertise them.

#### EN-4. `get_settings` never reconciles an existing settings file with new/changed fields — `High` / `S`
**Where:** `src/voxkit/engines/base.py:250-267`
**What:** `settings = self._load_json(settings_path)` then `if not settings: settings = self._get_default_settings(cfg); self._save_json(...)`. The defaults branch fires only when the file is missing or empty. If a `FieldConfig` is added to an engine after a user has already written that engine's JSON, the new key is never merged in — `settings.get(new_key)` returns `None` forever. For W2TG that is fatal, not cosmetic: `_validate_align_settings` (`w2tg_engine.py:256-266`) requires `isinstance(settings.get("use_speaker_adaptation"), bool)`, so a missing key makes the validator return `False` and `get_settings` raise `ValueError(f"Invalid align settings: {settings}")` (`base.py:266-267`) — breaking alignment entirely for existing installs. Conversely, keys removed from a config linger in the file forever.
**Why it's debt:** Every future settings field is an upgrade-path landmine that only bites users with pre-existing `~/.voxkit` state — i.e. never in dev, always in the field.
**Fix:** Merge defaults under loaded values (`merged = {**self._get_default_settings(cfg), **settings}`), drop keys not present in `cfg.fields`, and re-persist when the merged result differs from what was on disk.

#### EN-5. `W2TGEngine.align` returns normally when the alignment record can't be created — the GUI reports success — `High` / `S`
**Where:** `src/voxkit/engines/w2tg_engine.py:143-145`
**What:** `if not result: print(f"Alignment creation failed: {msg}"); return`. The caller is `PredictionStacker.predict_alignments_logic` (`src/voxkit/gui/pages/pipeline/prediction_stacker.py:200-205`), which then unconditionally `return "Alignments predicted successfully"`, and `on_predict_finished` shows `QMessageBox.information(self, "Success", message)`. The sibling `MFAEngine.align` handles the same condition correctly with `raise ValueError(f"Alignment creation failed: {msg}")` (`mfa_engine.py:164-165`).
**Why it's debt:** A failed alignment is reported to the user as a completed one, and the only diagnostic is a `print` that is discarded in the shipped build (EN-6). The user then looks for TextGrids that were never produced.
**Fix:** Raise, matching `mfa_engine.py:164-165` — and once EN-1 lands, this branch lives in one place.

#### EN-7. `MFAEngine.train_aligner` is a 60-line self-admitted "TEMP FIX" that orphans files and leaves broken records behind — `High` / `M`
**Where:** `src/voxkit/engines/mfa_engine.py:195-271` (hack block at `:217-253`)
**What:** After `models.create_model`, the method rewrites the storage layer's decision about file extensions inline under a banner comment reading `========= TEMP FIX FOR MFA MODEL EXTENSION ========` / `This should ideally be handled in the storage/models.py create_model function`. Concretely it: (a) string-splits the path — `Path(str(new_model_path).split(".model")[0] + ".zip")` at `:227`, which mangles any path containing `.model` earlier in it; (b) hand-serializes the metadata dict with `import json` *inside the function body* at `:240` and a manual `json.dump`, duplicating `base.py:170-182`'s `_save_json`; (c) `new_path.touch()` at `:251` creates an **empty** `.zip` placeholder with the comment "Ignore old model path and create new file" — the `entrypoint.model` created by `create_model` is never removed, so every MFA training run leaves an orphan; (d) has a typo in its own comment, `metadata['modle_path']` at `:222`. Then `except Exception as e: raise RuntimeError(f"MFA model training failed: {e}")` at `:270-271` — no `from e` (traceback chain lost) and, unlike `W2TGEngine.train_aligner` which calls `models.delete_model(engine_id=self.id, model_id=new_model_actual_id)` on failure (`w2tg_engine.py:249-254`), no cleanup: a failed MFA training leaves a registered model whose file is a 0-byte `.zip`, which the models page will happily offer for alignment.
**Why it's debt:** Every failed training run pollutes `~/.voxkit` with a model that looks valid and isn't; the extension policy lives in two places that must agree; the lost traceback makes MFA failures harder to diagnose than W2TG ones.
**Fix:** Move extension selection into `storage/models.py:139-175` (which already branches on `.zip` vs `.model` for imports) — e.g. `create_model(engine_id, model_name, extension=...)`; use `self._save_json` instead of the inline `json.dump`; add the same `delete_model` cleanup W2TG has; `raise RuntimeError(...) from e`.

#### EN-6. ~35 `print()` calls in a module whose own repo documents that `print` is discarded in shipped builds — `Medium` / `M`
**Where:** `src/voxkit/engines/w2tg_engine.py:132,135,141,144,154-157,160,223,231-232,258,261,264,270,273,276,279`; `src/voxkit/engines/mfa_engine.py:139,170,257`; `src/voxkit/engines/faster_whisper_engine.py:129,142,145,154,175,178,181`; `src/voxkit/engines/__init__.py:76`
**What:** The project has a real logging stack — `src/voxkit/config/logging_config.py` installs a `RotatingFileHandler` at `~/.voxkit/logs/voxkit.log`, and `src/voxkit/gui/components/log_handler.py` bridges stdlib logging into a Qt signal so the GUI can show live output. `main.py:16-17` does `if sys.stdout is None: sys.stdout = open(os.devnull, "w", ...)`, and `src/voxkit/config/startup_config.py:126-128` states the convention explicitly: *"Logs rather than prints: in a `--windowed` PyInstaller build `sys.stdout` is redirected to devnull (see `main.py`), so `print()` diagnostics from this path are discarded exactly when they are most needed."* The engines ignore this wholesale. `w2tg_engine.py:38` even defines `logger = logging.getLogger(__name__)` and then uses it only twice (`:185`, `:250`) while printing 20 times around it. Every validator failure reason (`w2tg_engine.py:258-279`, `faster_whisper_engine.py:175-181`) is printed and then thrown away — the raised `ValueError` from `base.py:267` carries only the settings dict, not which field failed.
**Why it's debt:** In the artifact users actually run, the engines produce zero diagnostics in the log file or the GUI log viewer. `AGENTS.md:96` documents exactly this pain ("Both surface as an opaque `MFA alignment failed (exit 1)` in the GUI"). Field bug reports are unactionable.
**Fix:** Replace `print` with a module-level `logger` in all four files (mechanical); make validators return a reason string or raise with the offending field name so `get_settings` can report it.

#### EN-8. `_configured_conda_path` swallows every exception, silently discarding the user's conda path — `Medium` / `S`
**Where:** `src/voxkit/engines/mfa_engine.py:280-283`
**What:** `try: value = self.get_settings(tool_type).get("conda_path") except Exception: return None`. `get_settings` can raise `ValueError` (settings invalid, or tool not configured), `JSONDecodeError` (corrupt file), or `OSError`. All become `None`, which the service layer treats as "auto-detect" (`services/mfa.py:_find_conda`).
**Why it's debt:** This field exists specifically for Windows users whose conda isn't on PATH (`mfa_engine.py:44-49`). A corrupt settings file turns their explicit configuration into silent auto-detection, and auto-detection then fails with a message about conda not being found — pointing the user at the wrong problem.
**Fix:** Catch only `(ValueError, OSError, json.JSONDecodeError)`, and log at warning level before returning `None`.

#### EN-9. `FasterWhisperEngine` reimplements `get_dataset_data_path` against a private storage function — `Medium` / `S`
**Where:** `src/voxkit/engines/faster_whisper_engine.py:111-118`
**What:**
```python
if dataset_meta["cached"]:
    dataset_root = datasets._get_dataset_root(dataset_id)
    ...
    audio_root = dataset_root / "cache"
else:
    audio_root = Path(dataset_meta["original_path"])
```
This is a line-for-line reimplementation of `src/voxkit/storage/datasets.py:104-115` `get_dataset_data_path(meta)`, which both other engines call (`mfa_engine.py:152`, `w2tg_engine.py:165`). It reaches through to the underscore-prefixed `datasets._get_dataset_root`, and uses `dataset_meta["cached"]` where the shared helper uses `.get("cached")` — so a metadata file predating the `cached` field raises `KeyError` here but not in the helper.
**Why it's debt:** Commit `ee37272` ("Resolve dataset corpus paths via get_dataset_data_path in aligners") already did this consolidation for the two aligners and missed the transcriber; the next change to the cache layout will break this copy only.
**Fix:** `audio_root = datasets.get_dataset_data_path(dataset_meta)` with a `None` check, matching `mfa_engine.py:152-154`.

#### EN-10. The backend engine layer imports PyQt6 GUI types, and `base.py` papers over it with `Any` — including in its docstrings — `Medium` / `M`
**Where:** `src/voxkit/engines/mfa_engine.py:30-34`, `w2tg_engine.py:27-31`, `faster_whisper_engine.py:29-33`; `base.py:65,208-218,271-287`
**What:** All three engines import `FieldConfig`, `FieldType`, `SettingsConfig` from `voxkit.gui.frameworks.settings_modal`, whose `__init__.py:54` imports `GenericDialog` → PyQt6. `docs/ARCHITECTURE.md:25-49` describes `voxkit.gui` as the presentation layer and `voxkit.engines` as a separate backend layer; the dependency runs backwards. `base.py` then can't name the type, so `settings_configurations: dict[AVAILABLE_TOOLS, Any]` (`:65`) and `get_settings_config(...) -> Any` (`:271`). The docstrings show this was a mechanical `SettingsConfig` → `Any` replacement and were corrupted by it: `"Extract default values from Any fields"` and `"cfg: The Any object containing field definitions"` (`:210-214`), `"defaults ... extracted from the Any fields"` (`:228-229`), `"Return the :class:`Any` for a tool type"` (`:273`).
**Why it's debt:** `get_settings_config` returns `Any`, so mypy validates nothing at the GUI call sites (`prediction_stacker.py:55`, `training_stacker.py:64-66`, `transcription_stacker.py:58`); the engines cannot be imported or unit-tested headless; and the docstrings that pdoc publishes (`invoke generate-documentation`) are nonsense.
**Fix:** Move the `FieldConfig`/`FieldType`/`SettingsConfig` dataclasses out of `gui/frameworks/` into a UI-agnostic schema module (they are plain dataclasses — `settings_modal/api.py:1-3` imports only stdlib), import the real type in `base.py`, and restore the docstrings.

#### EN-11. Module-level singletons force torch, Wav2TextGrid, faster-whisper, and PyQt6 to load on any `import voxkit.engines` — `Medium` / `M`
**Where:** `src/voxkit/engines/__init__.py:96-99`; `w2tg_engine.py:33-34`; `faster_whisper_engine.py:27`
**What:** `__init__.py` constructs all three engines at import time (`w2tg = W2TGEngine(id="W2TGENGINE")` etc.). `w2tg_engine.py` does top-level `from Wav2TextGrid.wav2textgrid import align_dirs` / `from Wav2TextGrid.wav2textgrid_train import train_aligner` (pulling torch + speechbrain), and `faster_whisper_engine.py:27` does `from faster_whisper import WhisperModel` — all unconditionally, even for a user who only ever runs MFA. `AGENTS.md:89` already flags `import voxkit` as expensive; this is the largest contributor, and it applies to `import voxkit.engines` on its own.
**Why it's debt:** Slow app startup and slow test collection (`tests/engines/test_engine_manager.py:3` imports the package and therefore torch); a broken optional dependency takes down engine *discovery*, not just that one engine.
**Fix:** Move the heavy third-party imports inside the methods that use them (`align`, `train_aligner`, `transcribe`), the way GUI pages already lazily do `from voxkit.engines import engines` inside `__init__` (`training_stacker.py:40`, `prediction_stacker.py:35`).

#### EN-12. MFA's two required validators are no-op stubs with "implement this" comments — `Medium` / `M`
**Where:** `src/voxkit/engines/mfa_engine.py:288-292`
**What:** `def _validate_align_settings(self, settings: dict) -> bool: return True  # Implement validation logic for align settings here` and the identical `_validate_train_settings`. These are `@abstractmethod`s on the base (`base.py:116-142`), so the ABC forces every engine to declare them, and MFA satisfies the contract by doing nothing. W2TG (`w2tg_engine.py:256-281`) and FasterWhisper (`faster_whisper_engine.py:172-183`) implement real checks.
**Why it's debt:** A hand-edited or partially-migrated `MFAENGINE/*/settings.json` — e.g. `num_iterations` as a string — passes validation and reaches the MFA subprocess as a malformed CLI argument, surfacing as the opaque `MFA alignment failed (exit 1)` that `AGENTS.md:96` calls out.
**Fix:** Validate the declared field types (mirroring the `isinstance` checks W2TG uses), or better, derive validation generically from `FieldConfig.field_type`/`min_value`/`max_value` in `base.py` and delete all three hand-written validators.

#### EN-17. `FasterWhisperEngine.transcribe` hardwires the corpus layout, the audio extension, and decoding parameters, with no cancellation — `Medium` / `M`
**Where:** `src/voxkit/engines/faster_whisper_engine.py:95-154`
**What:** The walk at `:133-137` iterates `audio_root.iterdir()`, skips anything that isn't a directory, and globs `*.wav` one level down — so audio sitting directly in `audio_root`, or nested two levels deep, is silently skipped with no warning and no count of what was processed. The extension is hardcoded `.wav` (`:137`) even though both sibling engines expose a `file_type` setting for exactly this; `beam_size=5` (`:149`) is a magic literal with no setting behind it; existing `.lab` files are skipped silently (`:141-143`), so a re-run after a bad transcription is a no-op with no way to force it. The loop can run for many minutes inside a `WorkerThread` (`transcription_stacker.py:188-189`) with no cancellation check and no progress signal. The docstring at `:103` promises `RuntimeError: If transcription fails for any file` — nothing in the body raises `RuntimeError`; an exception from `model.transcribe` propagates raw and aborts the whole dataset mid-way, leaving a partially-transcribed corpus.
**Why it's debt:** "Transcribed 0 files, reported success" is indistinguishable from "transcribed everything" for a user with a flat corpus; a long run cannot be cancelled or resumed cleanly.
**Fix:** Reuse `get_dataset_data_path` (EN-9) and glob recursively over a configurable extension; expose `beam_size` and an overwrite flag as `FieldConfig`s; count and log processed/skipped files; accept a cancellation token / progress callback so the worker can interrupt; fix or honor the docstring's `RuntimeError` contract.

#### EN-18. Zero test coverage of all three engines, and nothing in them is structured to be testable — `Medium` / `M`
**Where:** `tests/engines/` (only `test_base.py`, `test_engine_manager.py`); `pyproject.toml` `[tool.coverage.run] omit = ["src/voxkit/engines/*_engine.py", ...]`
**What:** `test_base.py` exercises `AlignmentEngine` through a local `ConcreteTestEngine` with mock configs (good), and `test_engine_manager.py` covers registration/lookup. Neither touches `MFAEngine`, `W2TGEngine`, or `FasterWhisperEngine`. `AGENTS.md:90` sanctions this ("Engines and services wrap external binaries; changes there are hard to unit-test and are omitted from coverage by design") — but a meaningful slice of the untested code is pure logic with no external tool involved: `MFAEngine._configured_conda_path`'s blank/whitespace normalization (`mfa_engine.py:273-286`), the `.model`→`.zip` path rewrite (`mfa_engine.py:226-228`), all three engines' validators, and `FasterWhisperEngine`'s audio-root resolution and speaker-dir walk (`faster_whisper_engine.py:111-137`). They are untested because the external calls are module-level imports and direct `voxkit.storage` references with no seam, not because they're inherently untestable.
**Why it's debt:** Every finding above (EN-2's default drift, EN-4's merge gap, EN-5's silent return, EN-9's duplicated path logic) is exactly the kind of defect a handful of unit tests would have caught, and the coverage `omit` guarantees none of them ever show up as a gap.
**Fix:** Once the heavy imports are function-local (EN-11), the tool calls (`run_mfa_align`, `align_dirs`, `WhisperModel`) are monkeypatchable. Add tests for the pure helpers and for the lifecycle template method from EN-1, and narrow the coverage `omit` to the thin `_run_*` adapters rather than whole files.

#### EN-13. The base class's own "how to write an engine" example cannot be instantiated, and the documented storage layout matches no engine — `Low` / `S`
**Where:** `src/voxkit/engines/base.py:5-30`; `src/voxkit/engines/__init__.py:27-38`
**What:** `base.py:17-29` shows `class MyEngine(AlignmentEngine)` defining only `align`. Since `train_aligner`, `_validate_train_settings`, and `_validate_align_settings` are all `@abstractmethod`, instantiating that class raises `TypeError`. The surrounding instructions (`:11-12`) do list the four methods, so the example contradicts its own text. Separately, `__init__.py:31-38` documents the on-disk layout as `~/.voxkit/{engine_id}/aligner/aligner_settings.json`, `train/trainer_settings.json`, `transcribe/transcriber_settings.json` — but MFA actually uses `MFAENGINE/align/settings.json` and `MFAENGINE/train/settings.json` (`mfa_engine.py:93,125`). The same docstring names tools `alignment`/`training`/`transcription` while `AVAILABLE_TOOLS` is `"train" | "align" | "transcribe"` (`constants.py:4`).
**Why it's debt:** These docstrings are the module's onboarding path and are published by pdoc; following them produces a class that won't construct and a wrong mental model of the settings tree.
**Fix:** Make the example complete (or mark it a fragment), and regenerate the storage-layout block from the actual `store_file` values. Standardize the paths while you're there (see EN-14).

#### EN-14. `store_file` hardcodes the engine ID that is otherwise injected via the `id=` parameter — `Low` / `S`
**Where:** `src/voxkit/engines/mfa_engine.py:93,125`; `w2tg_engine.py:76,106`; `faster_whisper_engine.py:76`; instantiation at `__init__.py:96-98`
**What:** Engines take `id` as a constructor argument (`MFAEngine(id="MFAENGINE")`) and use `self.id` for all model/alignment storage (`models.create_model(engine_id=self.id, ...)`, `alignments.create_alignment(engine_id=self.id, ...)`). But settings paths are string literals baked into module-level `SettingsConfig` objects: `store_file="MFAENGINE/align/settings.json"`. Construct `MFAEngine(id="MFA_EXPERIMENTAL")` and its models go to a new directory while its settings still read and write `MFAENGINE/`. The W2TG configs are module-level globals (`w2tg_engine.py:40,79`) shared across every instance, so two instances cannot have distinct settings at all. The naming is also inconsistent across siblings: `align/settings.json` vs `aligner/aligner_settings.json` vs `transcribe/transcriber_settings.json`.
**Why it's debt:** The `id` parameter promises multi-instance/renameable engines and doesn't deliver; the inconsistent paths make the layout unguessable and are what `__init__.py`'s docstring got wrong (EN-13).
**Fix:** Build `store_file` from `self.id` in `AlignmentEngine.__init__` (e.g. `f"{self.id}/{tool}/settings.json"`) rather than hardcoding it per engine, with a one-time migration for existing files.

#### EN-15. `EngineManager.list_engines()` prints as a side effect and is called on every GUI reload — `Low` / `S`
**Where:** `src/voxkit/engines/__init__.py:73-77`
**What:** `keys = list(self._engines.keys()); print(f"[engines.__init__] Registered engines: {keys}"); return keys`. Callers are `models_page.get_engines()` (`src/voxkit/gui/pages/models/models_page.py:88`) and `datasets_page.get_engines()` (`src/voxkit/gui/pages/datasets/datasets_page.py:62`), both of which run on tab-switch `reload()` — and `models_page.py:213-214` calls `self.get_engines()` twice in a single expression.
**Why it's debt:** A pure accessor with an I/O side effect; noise in dev consoles proportional to UI navigation.
**Fix:** Drop the print (or `logger.debug` it once at construction).

#### EN-16. Assorted verified cleanups: commented-out code, a duplicated option list, and a repeated type-narrowing assert — `Low` / `S`
**Where:** `w2tg_engine.py:126-129`; `faster_whisper_engine.py:48` vs `:174`; `mfa_engine.py:167,215` and `w2tg_engine.py:147,206`
**What:** (a) `W2TGEngine.__init__` ends with four commented-out lines (`# for tool, config in self.settings_configurations.items(): ... os.makedirs(...)`) — dead since `base._save_json` already does `path.parent.mkdir(parents=True, exist_ok=True)` (`base.py:180`). (b) The Whisper model-size list `["tiny", "base", "small", "medium", "large-v3"]` is written once as `FieldConfig.options` (`:48`) and again as the validator's membership tuple (`:174`); adding `large-v3-turbo` requires editing both or the UI offers a size the validator rejects. (c) `assert not isinstance(msg, str)` appears four times purely to narrow `tuple[Literal[True], Metadata] | tuple[Literal[False], str]` for mypy; `S101` is globally ignored in `pyproject.toml`, so nothing flags it, and under `python -O` the narrowing silently disappears.
**Why it's debt:** Small, but (b) is a real drift vector and (c) is a load-bearing runtime check that can be compiled away.
**Fix:** Delete (a); define the option list once as a module constant and reference it from both places for (b); for (c) restructure as `if not result: raise ...` plus an explicit `isinstance(msg, dict)` guard, ideally hoisted into the base template method from EN-1.

### Cross-module notes

- `scripts/build.py:150-151` lists PyInstaller hidden imports `voxkit.engines._w2tg_engine` and `voxkit.engines._whisperx_engine`. Neither module exists anywhere in the repo (verified by grep — those two lines are the only hits). Meanwhile the modules that *do* exist and are imported dynamically-ish, `voxkit.engines.w2tg_engine` and `voxkit.engines.faster_whisper_engine`, are **not** in the list; only `voxkit.engines.mfa_engine` is. Stale and probably incomplete.
- `src/voxkit/gui/pages/models/models_page.py:158-165` (`scrub_training_runs`) maps engine display names back to IDs by substring — `if "MFA" in mode: mode = "MFAENGINE" elif "W2TG" in mode: mode = "W2TGENGINE" else: raise ValueError("Invalid mode")`. This reverse-engineers `human_readable_name` into `id` and hard-fails for any third engine. Belongs to the GUI module but is driven entirely by the engines' identity fields.
- `src/voxkit/gui/pages/pipeline/prediction_stacker.py:222` gates the "Repair/Reinstall MFA Environment" button on `!= "MFAENGINE"`. This is a genuine engine capability leaking into the GUI as a string comparison; a per-engine capability/action hook would keep it in the engine layer.
- Engine-ID string literals as fallback defaults are scattered through the GUI: `models_page.py:213` and `:234` default to `"MFAENGINE"`, `import_dialog.py:34` defaults to `"W2TGENGINE"`. Two different arbitrary defaults for the same concept.
- `src/voxkit/storage/models.py:139-175` owns the `.model` vs `.zip` extension policy that `mfa_engine.py:217-229` hacks around at runtime — the hack's own comment says the fix belongs there. Storage-module owner should take this.
- `src/voxkit/services/mfa.py:341-345` (`run_mfa_adapt`) re-raises the bare `CalledProcessError` while its sibling `run_mfa_align:284-287` wraps it in a `RuntimeError` with captured stderr. Training failures therefore reach the GUI with a much less useful message than alignment failures. Services module, but it's why `mfa_engine.train_aligner`'s error path is worse than `align`'s.


---

## Module: `src/voxkit/services/`

**Health:** Battle-hardened comments over structurally raw code — the failure paths that matter most are the ones that swallow errors silently | **Files:** 2 (508 LOC src, 342 LOC tests) | **Findings:** 16 (4 High / 9 Medium / 3 Low)

This module is VoxKit's only bridge to the Montreal Forced Aligner: `mfa_provision.py` materializes a pinned conda environment from a vendored micromamba binary + explicit lockfile, and `mfa.py` shells out to that environment (or a user's own conda) to download dictionaries, align, adapt, and fetch acoustic models. The comments are unusually good — they encode real Windows failure modes (detached Postgres pipes, MSVCP140 access violations, entry-point stub failures) that would otherwise be lost. The debt is not in what the authors *knew*, it's in what the code *does*: every long-running subprocess is a silent, uncancellable, unmeasured blocking call; provisioning has no partial-failure cleanup and a one-file readiness probe that can latch permanently broken; and the Windows-only environment layout is hardcoded in two modules with no platform abstraction. Two of the highest-severity findings are already documented as bugs in the repo's own `AGENTS.md` and `docs/BUILD.md` — they were diagnosed and never fixed.

### Findings

#### SV-2. `_find_conda` returns a *directory* as the conda executable when `CONDA_PREFIX` is set — `High` / `S`
**Where:** `src/voxkit/services/mfa.py:119-127`

**What:**
```python
conda_prefix = os.environ.get("CONDA_PREFIX") or os.environ.get("CONDA_EXE", "")
if conda_prefix:
    candidates.insert(0, Path(conda_prefix).parent / "conda.exe")
    candidates.insert(0, Path(conda_prefix))
...
for path in candidates:
    if path.exists():
        return str(path)
```
One variable holds two semantically different values. `CONDA_PREFIX` is an environment *directory*; `CONDA_EXE` is a path to the *executable*. `Path.exists()` is true for directories, and `Path(conda_prefix)` is inserted at index 0 — so it is checked first and wins. Reproduced against the real function with `sys.platform` forced to `win32`, `shutil.which` returning `None`, and `CONDA_PREFIX=<tmp>/miniconda3/envs/aligner`:

```
returned: /.../miniconda3/envs/aligner
is a directory (NOT an executable): True
```

The derived candidate is wrong in both directions too: if the value came from `CONDA_EXE` (already `.../Scripts/conda.exe`), then `Path(conda_prefix).parent / "conda.exe"` resolves to `.../Scripts/Scripts/conda.exe`… no — to `.../Scripts/conda.exe`'s parent's `conda.exe`, i.e. the same file, harmlessly; but if it came from `CONDA_PREFIX`, `.parent` climbs one level *above* the env root, so the `conda.exe` it looks for is in the wrong directory entirely.

**Why it's debt:** The returned directory is handed straight to `subprocess.run([conda, "run", "-n", "aligner", "mfa", ...])` at `mfa.py:72` → `mfa.py:155`, producing an opaque `PermissionError`/`OSError` instead of the carefully-written "conda not found, set it in MFA engine settings" message at `mfa.py:129-135`. It fires exactly in the configuration this fallback exists to serve: a Windows user running from an activated conda env whose `conda` is not on `PATH`. It is masked whenever `shutil.which("conda")` succeeds (`mfa.py:103`), which is why it has survived. The entire `sys.platform == "win32"` candidate block (`mfa.py:106-127`) has zero test coverage — `tests/services/test_mfa.py:14-60` only exercises the explicit-path, env-var, and PATH branches.

**Fix:** Split the two env vars. Use `CONDA_EXE` directly as an executable candidate; derive from `CONDA_PREFIX` as `Path(prefix) / "Scripts" / "conda.exe"` (and `Path(prefix) / "condabin" / "conda.bat"`). Guard the loop with `path.is_file()` rather than `path.exists()`. Add a test for the win32 candidate branch.

#### SV-3. `_ensure_mfa_server_running` swallows every failure — a fix already documented in `AGENTS.md` and never implemented — `High` / `M`
**Where:** `src/voxkit/services/mfa.py:221-236`; documented as a known defect at `AGENTS.md:98-103`

**What:** All three server commands run with return codes ignored entirely and the only exception handler being `except (subprocess.TimeoutExpired, FileNotFoundError): pass`:
```python
for sub in (("configure", "--enable_use_postgres"), ("server", "init"), ("server", "start")):
    try:
        subprocess.run([*prefix, *sub], stdout=DEVNULL, stderr=DEVNULL, timeout=60, ...)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
```
`AGENTS.md:103` states the requirement verbatim: *"`_ensure_mfa_server_running` in `src/voxkit/services/mfa.py` deliberately ignores return codes, which hides both failures — validate the data dir (`PG_VERSION`, `global/pg_control`) before `init` rather than trusting that the calls worked."* No such validation exists in the module.

**Why it's debt:** `AGENTS.md:96-103` describes the concrete consequence: a half-deleted `~/.voxkit/mfa-root/pg_mfa_global/` leaves an empty directory that makes `server init` refuse and `server start` run `pg_ctl -D <empty dir>` and fail. Both failures are discarded here, so alignment proceeds, MFA falls through to SQLite or fails to connect, and the user sees only `MFA alignment failed (exit 1)` from `mfa.py:287`. The state is permanent and unrecoverable through MFA's own CLI. The onboarding doc exists *because* this function hides the diagnosis — the documentation is a workaround for the code.

Secondary: `_mfa_invocation(conda_path)` is called at `mfa.py:199`, **outside** the `try`, so a `FileNotFoundError` from `_find_conda` (`mfa.py:129`) escapes a function whose contract is best-effort. And `PermissionError` — the exact error SV-2 produces — is an `OSError` but not a `FileNotFoundError`, so it is not caught either.

**Fix:** Implement the documented check: before `server init`, verify `mfa_root_dir() / "pg_mfa_global"` either does not exist or contains `PG_VERSION` and `global/pg_control`; remove the empty shell if it is neither. Capture each command's `returncode` and log a warning naming which subcommand failed (a `WARNING`-level log, not a raise — the best-effort contract is fine, the silence is not). Move the `_mfa_invocation` call inside the guarded region or catch `OSError`.

#### SV-4. `download_acoustic_model` shells out to `curl` without `--fail`, silently saving HTTP error pages as model archives — `High` / `M`
**Where:** `src/voxkit/services/mfa.py:348-363`; consumed at `src/voxkit/config/startup_config.py:66-76`

**What:**
```python
url = f"https://github.com/MontrealCorpusTools/mfa-models/releases/download/{release_path}"
cmd = ["curl", "-L", "-o", output_file, url]
subprocess.run(cmd, check=True, **_no_window())
```
`curl -L` without `--fail` exits **0** on an HTTP 404/500 and writes the response body — GitHub's HTML error page — into `output_file`. `check=True` therefore does not catch a failed download. There is no timeout, no retry, no `Content-Length`/checksum verification, and the write is not atomic (no temp-file-plus-rename), so an interrupted transfer leaves a truncated file indistinguishable from a complete one.

**Why it's debt:** `startup_config.py:66-76` treats a non-raising call as success and immediately records the path as a valid model: `models.update_model_metadata("MFAENGINE", metadata["id"], {"model_path": str(output_file)})`. So a typo'd release path, a retired release tag, or a captive-portal network yields a registered model that fails much later, deep inside MFA, as an unrelated archive-parse error. The two hardcoded release paths (`startup_config.py:44-45`) pin MFA model versions `v3.0.0`/`v3.3.0` while the bundled lockfile pins `montreal-forced-aligner-3.4.1` — a mismatch that will eventually retire a release tag and turn this into a fleet-wide silent corruption.

Also: `curl` is assumed present. It ships with Windows 10+ and macOS, but is not guaranteed on minimal Linux images, and this is a cross-platform app. `requests`/`urllib` are already in the dependency tree transitively.

**Fix:** Replace the `curl` subprocess with `urllib.request`/`requests`: check `response.status`, stream to a `.part` file with a timeout, verify size, then `os.replace()` onto the final path. Raise a typed error naming the URL and status on failure. Move the release paths and the base URL out of both `mfa.py:355` and `startup_config.py:43-46` into `config/`.

#### SV-5. Provisioning has a one-file readiness probe and no cleanup on failure — a half-built env latches permanently — `High` / `M`
**Where:** `src/voxkit/services/mfa_provision.py:103-105, 108-133`

**What:** Readiness is a single existence check:
```python
def is_aligner_env_ready() -> bool:
    return (bundled_env_path() / "Scripts" / "mfa-script.py").exists()
```
and provisioning is one unguarded call with no cleanup — the only filesystem operation besides `subprocess.run` is `env_path.parent.mkdir(parents=True, exist_ok=True)` at `:130`:
```python
cmd = [str(micromamba), "create", "-p", str(env_path), "--file", str(lockfile), "-y"]
subprocess.run(cmd, check=True, capture_output=True, text=True, **_no_window())
```
No `try`/`except`, no `shutil.rmtree(env_path)` on failure (grep for `rmtree|unlink` in the file returns nothing).

**Why it's debt:** If a ~1-2GB provisioning run is interrupted — network drop, user quits the app, machine sleeps — *after* micromamba has written `Scripts/mfa-script.py` but before the environment is complete, then `is_aligner_env_ready()` returns `True` forever. Every gate in the app keys off that: `startup_config.py:140` returns early, `gui/workers/startup.py:140` no-ops, and `mfa.py:62` selects the broken bundled env in preference to the user's working conda. The user's only escape is discovering the "Repair/Reinstall MFA Environment" button in `gui/pages/pipeline/prediction_stacker.py:220-244`. This is structurally the same trap `AGENTS.md:98-103` documents for the Postgres data directory: readiness inferred from the existence of one path rather than from a completion marker.

The docstring at `:110-112` ("Safe to re-run after a failure or interruption: micromamba caches downloaded packages, so a re-run resumes from cache") is true about the *package cache* but says nothing about the prefix directory — and `micromamba create -p` into a non-empty, non-valid prefix is not a clean resume.

**Fix:** Write an explicit completion marker (e.g. `<env>/.voxkit-provisioned` containing the lockfile's hash) as the last step, and make `is_aligner_env_ready()` test that marker plus the lockfile hash — which also gives free invalidation when the lockfile is regenerated. Wrap the `subprocess.run` so a failure `shutil.rmtree(env_path, ignore_errors=True)` before re-raising, or provision into `<env>.tmp` and `os.replace` on success.

#### SV-1. `services/` has no `__init__.py` — excluded from wheel builds and from generated docs — `Medium` / `S`
**Where:** `src/voxkit/services/` (no `__init__.py`); `pyproject.toml:214-215`; `src/voxkit/__init__.py:17,31-40`

**What:** `[tool.setuptools.packages.find] where = ["src"]` uses setuptools' `find_packages`, which only discovers directories containing `__init__.py`. Verified by running it against this tree:

```
find_packages(where='src') -> voxkit, voxkit.analyzers, voxkit.config,
   voxkit.engines, voxkit.gui, voxkit.gui.components, voxkit.gui.styles,
   voxkit.gui.workers, voxkit.storage
```

`voxkit.services` is absent. So is `voxkit.gui.frameworks` and `voxkit.gui.pages` (the audit brief's premise that services is uniquely missing one is not quite right — three subpackages lack it; the other two belong to the GUI module).

Separately, `src/voxkit/__init__.py:17` reads `from . import analyzers, config, engines, gui, storage` — `services` is omitted there, from `__all__` (`:31-40`), and from the module docstring's "Subpackages" list (`:4-11`). `AGENTS.md:89` states the eager-import block exists specifically "so pdoc can discover them," so `invoke generate-documentation` produces docs with no `services` section at all.

**Why it's debt:** The packaging half is latent, not currently breaking: the dev venv uses an editable install (`__editable__.pypllr_gui-0.5.0.pth`, which puts `src/` on `sys.path` wholesale) and PyInstaller builds from source, so both current paths mask it. But `pip install .` yields a distribution where `src/voxkit/engines/mfa_engine.py:35` (`from voxkit.services.mfa import run_mfa_adapt, run_mfa_align`) raises `ImportError` — a landmine for anyone who tries to ship a wheel or CI-install the package non-editably. The pdoc gap is active today: the module with the hairiest external-tool knowledge in the codebase is the one absent from the generated docs.

**Fix:** Add `src/voxkit/services/__init__.py` with a module docstring following the same "API" convention as `src/voxkit/gui/workers/startup.py:1-10`, add `services` to the import and `__all__` in `src/voxkit/__init__.py`, and add it to the docstring's Subpackages list. (Same treatment for `gui/frameworks` and `gui/pages` belongs to the GUI module — flagged in Cross-module notes.)

#### SV-6. `assert` used for control flow, with a fragile stdout substring match as the fallback — `Medium` / `S`
**Where:** `src/voxkit/services/mfa.py:161-174`

**What:**
```python
if result.returncode != 0:
    list_cmd = [*prefix, "model", "list", "dictionary"]
    list_result = subprocess.run(list_cmd, capture_output=True, text=True, ...)
    assert dictionary_name in list_result.stdout, (...)
```
Three problems in four lines. (a) `assert` is the mechanism by which a user-facing "dictionary unavailable" condition is reported — `run_mfa_align`'s docstring even advertises `Raises: AssertionError` (`mfa.py:259`). (b) `list_result.returncode` is never checked, so if `model list` *itself* fails, `stdout` is empty and the assertion message blames the dictionary. (c) The check is a bare substring test against tool stdout: `"english_us_arpa" in stdout` matches a line containing `english_us_arpa_v2`, `english_us_arpa_old`, or any incidental mention, so a *wrong* dictionary can satisfy the check.

**Why it's debt:** `AssertionError` is the wrong type for an environmental condition — it signals a broken invariant, and it is stripped entirely under `python -O`/`PYTHONOPTIMIZE`, turning a hard failure into a silent fall-through into `run_mfa_align`. `VoxKit.spec:15` currently sets `optimize=0`, so the build is safe *today*, but the safety is incidental and one spec edit away from vanishing. Ruff will not flag it: `pyproject.toml:101` globally ignores `S101` (justified as "OK in tests", but applied repo-wide).

**Fix:** Raise a typed exception (`RuntimeError`, or a module-level `MFAError`). Check `list_result.returncode` and report the two failures distinctly via `describe_process_failure`. Match against parsed lines (`dictionary_name in list_result.stdout.split()`) rather than a substring of the whole blob. Correct the `Raises:` sections in `mfa.py:147-148, 258-260, 309-311`.

#### SV-7. `print()` throughout `mfa.py` — diagnostics discarded in the shipped build, against the project's own stated standard — `Medium` / `S`
**Where:** `src/voxkit/services/mfa.py:154, 172, 174, 274, 283, 286, 331, 340, 342, 344, 358, 360, 362` (13 sites; the module imports no `logging`)

**What:** Every diagnostic in `mfa.py` is a `print()`. The project has already written down why that is wrong — `src/voxkit/config/startup_config.py:126-128`, in the docstring of the function that calls into this module:

> *"Logs rather than prints: in a `--windowed` PyInstaller build `sys.stdout` is redirected to devnull (see `main.py`), so `print()` diagnostics from this path are discarded exactly when they are most needed."*

Confirmed at `main.py:16-19`: `if sys.stdout is None: sys.stdout = open(os.devnull, "w", ...)`. `mfa_provision.py` correctly avoids printing; `mfa.py` did not get the same treatment.

**Why it's debt:** A direct deviation from a standard the repo articulates in prose, in a sibling module, about this module. The information lost is the highest-value diagnostic in the app: `mfa.py:274` prints the fully-resolved MFA command line, and `mfa.py:286`/`:344` print the aligner's stderr. In the shipped `--windowed` build all of it goes to `/dev/null`, which is precisely the "opaque `MFA alignment failed (exit 1)`" experience `AGENTS.md:96` complains about.

**Fix:** `log = logging.getLogger(__name__)` and convert the 13 sites — `log.info` for progress, `log.error`/`log.exception` for failures, `log.debug` for the command line. Matches `startup_config.py:13` and `gui/workers/startup.py:21`.

#### SV-8. `describe_process_failure` exists to solve a problem 3 of 4 call sites still have, and its signature forces a `type: ignore` on its only external caller — `Medium` / `S`
**Where:** `src/voxkit/services/mfa.py:17-36` (definition), `:284-287` and `:341-345` (call sites that don't use it), `:361-362`; `src/voxkit/config/startup_config.py:146-148`

**What:** `describe_process_failure` was written (per its own docstring at `:18-25`) because "a process killed by the OS produces no stdout/stderr at all, so reporting only `stderr` yields an empty message." It is used in exactly one place inside the module — the assertion at `:167-171` — and ignored by every other failure path:

- `run_mfa_align` (`:284-287`): `stderr_msg = e.stderr.strip() if e.stderr else "(no output captured)"` — hand-rolls the exact fallback, minus the crash-code detection.
- `run_mfa_adapt` (`:341-345`): worse — prints `{e}` (the `CalledProcessError` repr, i.e. `Command '[...]' returned non-zero exit status 1`) and then bare-`raise`s the original, so the GUI shows a message containing no stderr at all.
- `download_acoustic_model` (`:361-363`): same pattern, prints `{e}` and re-raises.

The two aligner entry points also diverge in *what* they raise: `run_mfa_align` wraps into `RuntimeError` (`:287`), `run_mfa_adapt` re-raises `CalledProcessError` (`:345`) — yet both docstrings claim `Raises: subprocess.CalledProcessError` (`:260`, `:311`), so the align docstring is simply wrong.

Separately, the signature is `def describe_process_failure(result: subprocess.CompletedProcess) -> str`, but its only cross-module caller passes a `CalledProcessError` and must suppress the type error to do it — `startup_config.py:148`:
```python
log.error("MFA environment setup failed: %s", describe_process_failure(e))  # type: ignore[arg-type]
```

**Why it's debt:** The abstraction that makes MFA failures legible is bypassed on the two paths users actually hit (align and adapt), so an adapt failure in the GUI reads as a bare exit status with no aligner output. The `type: ignore` is the type checker correctly reporting that the parameter type is too narrow for the function's actual contract — it only touches `.returncode`, `.stdout`, `.stderr`, both classes have all three.

**Fix:** Route `run_mfa_align`, `run_mfa_adapt`, and `download_acoustic_model` through `describe_process_failure`, and make both aligner functions raise the same wrapped error type. Widen the parameter to a small `Protocol` (or `CompletedProcess | CalledProcessError`) and drop the `type: ignore` at `startup_config.py:148`. Fix the `Raises:` docstrings.

#### SV-9. The module's public API is almost entirely unannotated, and mypy is configured not to look inside — `Medium` / `S`
**Where:** `src/voxkit/services/mfa.py:239-246, 290-297, 348`; `pyproject.toml:124`

**What:** The three functions that other modules call have no parameter types:
```python
def run_mfa_align(corpus_dir, model_path, output_dir, dictionary_name="english_us_arpa",
                  eval_dir=None, conda_path=None) -> None:
def run_mfa_adapt(corpus_dir, base_model_path, output_model_path,
                  dictionary_name="english_us_arpa", num_iterations=1, conda_path=None) -> None:
def download_acoustic_model(release_path, output_file):   # no return annotation either
```
Callers pass `str(...)` conversions defensively (`engines/mfa_engine.py:177-180`) because the contract is undocumented — `str` vs `Path` is genuinely load-bearing here since the values go straight into an argv list. Return types are also under-specified: `_no_window() -> dict` and `_mfa_invocation(...) -> tuple[list[str], dict]` (`mfa.py:10, 39`) use bare `dict` where `dict[str, int]` and `dict[str, str]` are meant.

Docstring styles are inconsistent between the two: `run_mfa_align` uses bare `corpus_dir:` while `run_mfa_adapt` uses `corpus_dir (str):`.

**Why it's debt:** Compounding, not standalone: `pyproject.toml:124` sets `check_untyped_defs = false`, so mypy skips the *bodies* of every unannotated function. Combined with `pyproject.toml:156` omitting `src/voxkit/services/**/*.py` from coverage and `AGENTS.md:90` declaring services "omitted from coverage by design," the module with the most external-process risk in the app has neither type checking nor coverage measurement. Nothing would catch a `Path`-where-`str`-expected regression until an MFA run fails at a customer site.

**Fix:** Annotate the three public functions (`str | Path` where genuinely permissive, plus `-> None`). Parameterize the `dict` returns. Normalize the docstring style to the repo's bare-name Google form.

#### SV-11. Windows-only environment layout is hardcoded across two modules with no platform abstraction — `Medium` / `M`
**Where:** `src/voxkit/services/mfa_provision.py:27, 105`; `src/voxkit/services/mfa.py:59-67`

**What:** The conda-env layout is spelled out in Windows form in two separate files. `mfa_provision.py:105` probes `bundled_env_path() / "Scripts" / "mfa-script.py"`; `mfa.py:65-66` builds `env_path / "python.exe"` and `env_path / "Scripts" / "mfa-script.py"`. On POSIX conda environments these live at `bin/python` and `bin/mfa`. The only explicit platform table is `_PLATFORM_TAGS = {"win32": "win-64"}` at `mfa_provision.py:27`, and it maps platform → lockfile tag only, not platform → env layout.

The coupling is acknowledged but only in a comment (`mfa.py:59-61`): *"is_aligner_env_ready() only ever returns True on win32 in v1 (the only platform with a bundled lockfile today), so the Windows-specific env-layout paths below (Scripts/, python.exe) are always correct here."*

**Why it's debt:** The invariant holding this together — "no non-win32 lockfile exists" — is enforced nowhere in code. `docs/BUILD.md:154` frames adding a macOS/Linux lockfile as a routine follow-up. The moment someone drops `aligner-osx-arm64.lock` into `config/mfa-env/` and adds `"darwin": "osx-arm64"` to `_PLATFORM_TAGS`, provisioning succeeds, `is_aligner_env_ready()` returns `False` forever (no `Scripts/` on macOS), and the app silently falls back to the conda path — burning a 2GB download every launch with no error anywhere. The correctness argument lives in a comment in a *different file* from `_PLATFORM_TAGS`, so the person adding the tag will not see it.

**Fix:** Replace the two ad-hoc path constructions with one platform-aware accessor pair in `mfa_provision.py` (`env_python_path()`, `env_mfa_script_path()`) that branches on `sys.platform` alongside `_PLATFORM_TAGS`, and have `mfa._mfa_invocation` consume those. Add an assertion or test that every key in `_PLATFORM_TAGS` has a corresponding layout.

#### SV-12. The provisioning readiness gate is duplicated at three call sites, and `provision_aligner_env` reports the wrong error when it's bypassed — `Medium` / `S`
**Where:** `src/voxkit/config/startup_config.py:133-141`; `src/voxkit/gui/workers/startup.py:140`; `src/voxkit/gui/pages/pipeline/prediction_stacker.py:230`; `src/voxkit/services/mfa_provision.py:119-127`

**What:** Three callers each reimplement "should I provision?" from the module's raw primitives:
- `startup_config.py:133` + `:140` — `if lockfile_path() is None: ... if is_aligner_env_ready(): return True`
- `gui/workers/startup.py:140` — `if mfa_provision.lockfile_path() is None or mfa_provision.is_aligner_env_ready(): return`
- `prediction_stacker.py:230` — `if mfa_provision.lockfile_path() is None:` (checks the lockfile but *not* readiness, since it's a deliberate re-install)

Each pairs the check with its own bespoke user-facing message about the same condition. Meanwhile `provision_aligner_env` itself checks in the opposite order (`mfa_provision.py:119-127`): micromamba binary first, lockfile second. So calling it on macOS — where provisioning is genuinely unsupported — raises `FileNotFoundError("Vendored micromamba binary not found at .../vendor/micromamba/micromamba")` rather than the accurate `"No bundled MFA environment lockfile for platform 'darwin'"`.

**Why it's debt:** The module exports primitives where callers need a decision, so the policy is smeared across three modules in two layers (config and GUI) and can drift — it already has: `prediction_stacker.py` checks one condition, the other two check both. And because the guard lives in the callers, the module's own error message for the unsupported-platform case is unreachable through normal flow and therefore wrong without anyone noticing.

**Fix:** Expose one function from `mfa_provision` — e.g. `provisioning_status() -> Literal["unsupported", "ready", "needed"]` — and have all three callers switch on it. Reorder the checks in `provision_aligner_env` so the platform/lockfile check precedes the binary check.

#### SV-13. No timeout, no cancellation, and no progress on a multi-gigabyte download — `Medium` / `M`
**Where:** `src/voxkit/services/mfa_provision.py:133`; `src/voxkit/services/mfa.py:155, 164, 275, 332, 359`

**What:** Six of the module's seven `subprocess.run` calls take no `timeout` — only `_ensure_mfa_server_running` (`mfa.py:231`) sets one, and its comment explains at length why a timeout there is *unsafe*. All the unbounded ones use `capture_output=True`, so output is buffered and unavailable until the process exits.

**Why it's debt:** Three distinct consequences. (1) **No progress:** `provision_aligner_env` downloads 216 packages / ~1-2GB with output fully buffered, so `LoadingDialog("Setting up the MFA alignment environment…")` at `gui/workers/startup.py:145-150` is an indeterminate spinner for the entire duration. On a slow connection that is indistinguishable from a hang, and the user's rational response — quit the app — produces exactly the half-built environment of SV-5. (2) **No cancellation:** `StartupScriptWorker.run` (`gui/workers/startup.py:39-48`) just calls the function; there is no handle on the child process, so `worker.wait()` at `:171` blocks the main thread indefinitely with no way to abort. (3) **No timeout:** a stalled TCP connection inside micromamba or MFA hangs the worker forever with no upper bound.

**Fix:** Introduce a shared `_run()` in the module that takes a default timeout and streams output via `subprocess.Popen` line-by-line, invoking an optional `on_output`/`on_progress` callback. Give `provision_aligner_env` an optional `progress: Callable[[str], None] | None = None` so `execute_mfa_provisioning` can push micromamba's per-package lines into `LoadingDialog.update_subtitle` (which already exists — `gui/workers/startup.py:101`). Keep a `Popen` handle so cancellation can terminate the child.

#### SV-14. The functions with the most branching logic are untested, though the test harness for them already exists in the same file — `Medium` / `M`
**Where:** `tests/services/test_mfa.py`, `tests/services/test_mfa_provision.py`; `pyproject.toml:156`; `AGENTS.md:90`

**What:** The suite (24 tests, 342 lines) covers the pure logic well — `_find_conda`'s override branches, `_mfa_invocation`'s bundle-vs-conda selection, `describe_process_failure`'s crash-code formatting, all the `mfa_provision` path helpers, and a genuinely valuable regression guard for the Postgres pipe deadlock (`test_mfa.py:115-172`). What is untested: `ensure_dictionary_downloaded` (the assert/fallback logic of SV-6 — zero tests), `run_mfa_align` (zero), `run_mfa_adapt` (zero), `download_acoustic_model` (zero, including the `curl` URL construction of SV-4), and the entire `sys.platform == "win32"` candidate block of `_find_conda` (`mfa.py:106-127` — the code containing the SV-2 bug).

The standard objection is that these shell out. But `TestEnsureMfaServerRunning._calls` (`test_mfa.py:127-139`) already demonstrates the pattern that defeats it, in the same file:
```python
monkeypatch.setattr(mfa.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw)))
```
Every one of the untested functions is a pure command-construction-plus-branch-on-returncode, fully exercisable that way. `test_mfa_provision.py:81-101` tests only `provision_aligner_env`'s two guard clauses and never asserts the shape of the command it builds (`create -p <env> --file <lock> -y`), so a regression in the micromamba invocation itself is uncaught.

**Why it's debt:** `pyproject.toml:156` omits `src/voxkit/services/**/*.py` from coverage and `AGENTS.md:90` blesses it ("hard to unit-test and are omitted from coverage by design"), so the gap is invisible in the coverage badge — the module reads as intentionally-untested rather than accidentally-undertested. Four of this report's High findings sit in code with no test asserting anything about it.

**Fix:** Add `subprocess.run` fakes for the four untested functions, asserting argv shape and each returncode branch. Add the win32 `_find_conda` case (which would have caught SV-2). Assert the micromamba argv in `test_mfa_provision.py`. Consider narrowing the coverage omit to the genuinely-unfakeable parts rather than the whole tree.

#### SV-10. `_no_window()` duplicated verbatim across both files — `Low` / `S`
**Where:** `src/voxkit/services/mfa.py:10-14` and `src/voxkit/services/mfa_provision.py:30-34`

**What:** Byte-identical, docstring included:
```python
def _no_window() -> dict:
    """Return creationflags to suppress console windows on Windows."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}
```
**Why it's debt:** Two copies of the one helper that touches every subprocess in the module; a fix to either (e.g. adding `startupinfo` with `STARTF_USESHOWWINDOW`, which is sometimes needed alongside `CREATE_NO_WINDOW`) silently applies to half the call sites. It is also the obvious anchor for the shared subprocess wrapper that SV-14 needs.

**Fix:** Move it to the `services/__init__.py` created in SV-1 (or a `services/_subprocess.py`) and import from both — ideally as part of the single `_run()` helper that also carries timeout and logging.

#### SV-15. Dead `__main__` block duplicating hardcoded model versions — `Low` / `S`
**Where:** `src/voxkit/services/mfa.py:366-375`; duplicated at `src/voxkit/config/startup_config.py:43-46`

**What:**
```python
if __name__ == "__main__":
    # Example model download
    download_acoustic_model("acoustic-spanish_mfa-v3.3.0/spanish_mfa.zip", "spanish_mfa.zip")
    download_acoustic_model("acoustic-english_us_arpa-v3.0.0/english_us_arpa.zip",
                            "english_us_arpa.zip")
```
Unreachable in the app (grep confirms no invocation of `mfa.py` as a script anywhere in `tasks.py`, `scripts/`, or CI). It downloads into the current working directory. The two release paths are byte-identical to `startup_config.py:44-45`.

**Why it's debt:** Leftover script scaffolding in a library module inside a GUI app, and a second copy of version pins that must be bumped in lockstep with the first. `pyproject.toml:195` explicitly excludes `if __name__ == "__main__":` from coverage, so it will never register as dead.

**Fix:** Delete the block. Hoist the release-path list into `config/` per the fix for SV-4, so there is one place to bump.

#### SV-16. `docs/BUILD.md` describes provisioning behavior the module no longer has — `Low` / `S`
**Where:** `docs/BUILD.md:24-25, 44-48` vs `src/voxkit/config/startup_config.py:114-132` and `src/voxkit/gui/workers/startup.py:121-141`

**What:** Two stale claims about this module:
- `BUILD.md:24-25`: *"On first launch, `config/startup_config.py`'s `startup_routine()` calls `voxkit.services.mfa_provision.provision_aligner_env()`."* It does not — `startup_routine` (`startup_config.py:28-111`) contains no provisioning call. It moved to `ensure_mfa_environment` (`:114`), invoked via `execute_mfa_provisioning` from `main.py:145`.
- `BUILD.md:44-47`: *"It also isn't retried automatically on next launch (unlike the app's other first-run downloads) -- retry it manually via the 'Repair/Reinstall MFA Environment' button."* The opposite is now true, and `ensure_mfa_environment`'s docstring (`startup_config.py:116-124`) says so explicitly: *"Deliberately not part of `startup_routine` and not gated on the first-launch flag… so running it on every launch costs nothing once setup has succeeded."*

**Why it's debt:** `BUILD.md` is the designated onboarding doc for this exact module (`mfa_provision.py:10-11` points readers at it). Its description of the retry semantics is inverted, which is precisely the detail someone debugging a failed provision would rely on.

**Fix:** Update both passages to describe the `main.py` → `execute_mfa_provisioning` → `ensure_mfa_environment` path and the every-launch retry.

### Cross-module notes

- **Missing `__init__.py` is not unique to services.** `src/voxkit/gui/frameworks/` and `src/voxkit/gui/pages/` (and their subpackages) also lack one and are likewise dropped by `find_packages`. Same root cause as SV-1, GUI module's to fix.
- **`startup_config.py` sits in `config/` but is orchestration, not configuration.** It downloads models, writes storage metadata, and drives provisioning (`startup_config.py:28-155`), which is why it ends up duplicating this module's readiness gate (SV-12). It is also the only non-services consumer of `describe_process_failure`. Placement question for the config/architecture owner.
- **`config/startup_config.py:43-46` hardcodes MFA acoustic-model release versions** (`v3.0.0`, `v3.3.0`) while `config/mfa-env/aligner-win-64.lock` pins `montreal-forced-aligner-3.4.1`. Two independently-drifting pin sets for the same toolchain, neither in `config/VERSION`-style single-source form. Belongs to whoever owns `config/`.
- **`StartupScriptWorker` (`gui/workers/startup.py:24-48`) offers no cancellation or progress channel** — only `finished`/`error` signals. SV-13's fix needs a progress signal from the worker layer, so that change lands in the GUI module.
- **The vendored lockfile uses md5 anchors, not sha256** (216 package URLs, all `conda.anaconda.org`, each with a `#<md5>` suffix). That is the standard conda explicit-lockfile format and micromamba verifies it, so provisioning integrity is *fine* — noting it only to record that it was checked and is not a finding, in contrast to SV-4's model downloads which have no integrity check at all.


---

## Module: `src/voxkit/config/`

**Health:** Two clean, well-documented loaders sitting next to one unmaintained god-function; the profile-resolution contract is stated three different ways and the frozen build uses the wrong one. | **Files:** 6 | **LOC:** 665 | **Findings:** 14 (3 High / 7 Medium / 4 Low)

This package resolves the `config/` directory (source vs PyInstaller `_MEIPASS`), picks the active profile from `config/profile.txt`, and parses `app_info.yaml` / `pipeline_definitions.yaml` into dataclasses; it also hosts logging setup and the first-launch startup routine. `app_config.py`, `pipeline_config.py`, and `logging_config.py` are tidy and reasonably tested. The debt clusters in three places: (1) `startup_config.py`, which is untyped, undocumented, `print()`-driven, swallows every failure, and drags `services` + `storage` into what should be the lowest layer; (2) three mutually inconsistent config-resolution paths (`resolve_config_file`, `get_profile_config_path`, and a hand-rolled copy in `voxkit/__init__.py`), with the frozen build on the wrong one; (3) zero validation of the YAML that the product explicitly markets as end-user-editable.

### Findings

#### CF-1. `startup_routine` swallows every failure, so a broken first launch is marked complete forever — `High` / `M`
**Where:** `src/voxkit/config/startup_config.py:28-111`, consumed at `src/voxkit/gui/workers/startup.py:95-99`
**What:** `startup_routine()` never raises. Model-metadata failures `print(...)` then `continue` (lines 53-60), download failures are caught by `except Exception as e: print(...)` (lines 77-78, 108-109), and the W2TG branch `return`s early on failure at lines 88 and 93 — a normal return, indistinguishable from success. `StartupScriptWorker.run` (`gui/workers/startup.py:41-48`) only emits `error` on an exception, so `on_finished` fires and calls `mark_first_launch_complete()` (`gui/workers/startup.py:99`) even when nothing downloaded. Additionally all 19 diagnostics use `print()`, which `main.py:16-19` redirects to `os.devnull` in a `--windowed` PyInstaller build.
**Why it's debt:** This is the exact failure mode that `ensure_mfa_environment`'s own docstring (`startup_config.py:117-128`) says was fixed for MFA provisioning — "a failure was swallowed, the flag was marked complete anyway, and the step then never ran again." The same bug is still live for acoustic-model and W2TG downloads, and in a shipped build there is no log line explaining it: the user gets an app with no models and no retry path. `on_error` (`gui/workers/startup.py:105-110`) deliberately does *not* mark first launch complete, so the retry mechanism exists — `startup_routine` just never triggers it.
**Fix:** Convert every `print` to `log.*` (the module already has `log = logging.getLogger(__name__)` at line 13, used only by `ensure_mfa_environment`). Collect per-asset failures and raise a summarizing exception at the end so `on_error` fires and first-launch stays unmarked, or make the flag per-asset. Replace the two blanket `except Exception` with narrow handlers plus `log.exception`.

#### CF-2. The frozen build bypasses `resolve_config_file`, giving PyInstaller different config-resolution semantics than source — `High` / `S`
**Where:** `main.py:152-155` vs `src/voxkit/config/app_config.py:72-104` and `:55-69`
**What:** There are two resolution functions with different fallback rules. `resolve_config_file(filename)` falls back **per file** to `config/profiles/default/<filename>` and raises `FileNotFoundError` if absent (lines 92-104). `get_profile_config_path()` falls back **per directory** to the legacy config root (lines 66-67). `AppConfig.load_default` / `PipelineConfig.load_default` use the first; `main.py`'s frozen branch uses the second and reads both YAMLs directly:
```python
profile_path = get_profile_config_path()
app_config = AppConfig.from_yaml(profile_path / "app_info.yaml")
pipeline_config = PipelineConfig.from_yaml(profile_path / "pipeline_definitions.yaml")
```
**Why it's debt:** The documented profile feature is "profiles only override the files they need to change" (`app_config.py:75-77`). That is true from source and false in the shipped build: a profile shipping only `app_info.yaml` works in dev and raises an uncaught `FileNotFoundError` inside `main()` in the installer, killing the app before the window appears (the call is not wrapped — contrast `main.py:121-128`, which does guard `get_app_config()`). Config bugs that only reproduce in a PyInstaller build are the most expensive kind to diagnose.
**Fix:** Delete the special-casing in `main.py:152-155` and call `get_app_config()` / `get_pipeline_config()` unconditionally — `get_config_root()` already handles `_MEIPASS` (lines 29-33), so the frozen branch is redundant. Then decide whether `get_profile_config_path`'s legacy-root fallback should exist at all (see CF-12).

#### CF-3. User-editable pipeline YAML is parsed with zero validation; a typo crashes the app at launch — `High` / `S`
**Where:** `src/voxkit/config/pipeline_config.py:122-131` and `:51-58`
**What:** `PipelineConfig.from_yaml` does `data = yaml.safe_load(f)` (line 123) with no `or {}` guard, unlike its sibling `app_config.py:140` which has one. Verified: an empty `pipeline_definitions.yaml` raises `AttributeError: 'NoneType' object has no attribute 'get'` at line 127. Separately `PipelineStep.from_dict` uses raw subscripts for required keys — `id=data["id"], label=data["label"], stacker_class=data["stacker_class"]` (lines 52-54) — so a missing or misspelled key raises a bare `KeyError: 'label'` with no file name, no step index, and no hint.
**Why it's debt:** `config/profiles/default/pipeline_definitions.yaml` ships a "NOTES FOR RESEARCHERS" block telling non-developers to hand-edit this file to reorder steps and add `collapsible_sections`. `VoxKitGUI.__init__` calls `get_pipeline_config()` unguarded (`src/voxkit/gui/__init__.py:225`), so any YAML mistake is a hard launch failure with a raw traceback — for exactly the audience least able to read one. `pydantic>=2.12.3` is already a declared dependency (`pyproject.toml`) and is used nowhere in `src/`.
**Fix:** Add `or {}` at line 123 to match `app_config.py:140`. Validate required step keys with a message naming the file and the offending step index, or model `PipelineStep`/`UIConfig`/`AppConfig` as pydantic models and surface `ValidationError` as a user-facing dialog.

#### CF-4. `AppConfig.from_yaml` has a hidden global dependency on `config/VERSION` — `Medium` / `S`
**Where:** `src/voxkit/config/app_config.py:143-146`
**What:** Inside a method whose entire contract is "load from `config_path`", the version is read from a completely different, globally-resolved file: `version_file = get_config_root() / "VERSION"; version = version_file.read_text(...)`. There is no `.exists()` check, in contrast to line 136 which guards `config_path`. The docstring's `Raises:` section (lines 132-134) mentions only the config file.
**Why it's debt:** `from_yaml(some_path)` is not a pure function of its argument — it silently reads repo/bundle state. The tests show the cost directly: `tests/config/test_app_config.py:83-91` builds a YAML in `tmp_path` but cannot assert anything about `config.version`, because the value comes from the real repo. A missing or unreadable `config/VERSION` in a bundle raises an unguarded `FileNotFoundError` that `src/voxkit/gui/__init__.py:224` does not catch.
**Fix:** Make the version an optional constructor parameter defaulting to a `get_version()` helper, so tests can inject it; guard the read and fall back to a sentinel like `"unknown"` rather than aborting startup.

#### CF-5. Log rotation defaults are written in three code locations plus three YAML files — `Medium` / `S`
**Where:** `src/voxkit/config/logging_config.py:14-15`, `src/voxkit/config/app_config.py:119-120`, `src/voxkit/config/app_config.py:157-158`
**What:** `DEFAULT_MAX_BYTES = 5 * 1024 * 1024` / `DEFAULT_BACKUP_COUNT = 3` in `logging_config.py`; then `log_max_bytes: int = 5 * 1024 * 1024` / `log_backup_count: int = 3` as dataclass defaults in `AppConfig`; then the *same literals again* as `.get()` fallbacks in `from_yaml`: `int(data.get("log_max_bytes", 5 * 1024 * 1024))`. `app_config.py` does not import the constants that `logging_config.py` already defines. The values are re-stated a fourth time as `log_max_bytes: 5242880` in `config/app_info.yaml`, `config/profiles/default/app_info.yaml`, and `config/profiles/explanatory/app_info.yaml`, and pinned a fifth time by `tests/config/test_logging_config.py:57-59`.
**Why it's debt:** Changing the rotation policy means finding five places; missing one produces a silent behavioral split between "config present" and "config absent" paths.
**Fix:** Import `DEFAULT_MAX_BYTES` / `DEFAULT_BACKUP_COUNT` from `logging_config` into `app_config` and use them for both the dataclass defaults and the `.get()` fallbacks.

#### CF-6. `voxkit/__init__.py` re-implements `get_config_root()` instead of calling it — `Medium` / `S`
**Where:** `src/voxkit/__init__.py:20-25` vs `src/voxkit/config/app_config.py:20-36` and `:145-146`
**What:** `_read_version()` hand-rolls the `_MEIPASS`-vs-source config-root branch (`Path(__file__).resolve().parents[2] / "config"`) and the VERSION read, duplicating `get_config_root()` (`Path(__file__).parent.parent.parent.parent / "config"`) and the read at `app_config.py:145-146`. Note the copies aren't even identical: `__init__.py` calls `.resolve()` first, `app_config.py` doesn't — so under a symlinked checkout the two can disagree.
**Why it's debt:** AGENTS.md names `config/VERSION` the single source of truth and enumerates its consumers; the *resolution logic* is what's duplicated, and it's the part that breaks when the bundle layout changes. `src/voxkit/__init__.py:17` already does `from . import ... config ...` before `_read_version()` is called, so the dependency is available with no new import cost.
**Fix:** Have `_read_version()` call `voxkit.config.app_config.get_config_root()`, or extract a single `get_version()` into `app_config.py` (see CF-4) and call it from both places.

#### CF-7. The `config` package depends on `services` and `storage`, inverting the layering — `Medium` / `M`
**Where:** `src/voxkit/config/startup_config.py:6-11`, re-exported by `src/voxkit/config/__init__.py:43-49`
**What:** `startup_config.py` imports `voxkit.services.mfa_provision`, `voxkit.services.mfa`, `voxkit.storage.models`, `voxkit.storage.constants`, and `voxkit.storage.utils` at module scope. Because `config/__init__.py:43` imports `startup_config` eagerly, `import voxkit.config` transitively initializes `voxkit.storage` and `voxkit.services`. Grepped to confirm the reverse edge does not exist — nothing under `storage/`, `analyzers/`, `engines/`, or `services/` imports `voxkit.config` — so this is a one-way inversion, not a cycle, but it means the lowest-level package is the one with the most dependencies.
**Why it's debt:** `config` is the dependency hub every other layer imports; making it pull in subprocess wrappers and CRUD code means you cannot import a config value without initializing half the app, and it blocks ever testing config in isolation. It also makes `config/__init__.py`'s own docstring claim (lines 10-12: "`startup_config` and `logging_config` are baked in at build time") misleading about what importing the package costs. The one consumer that actually needs this — `gui/workers/startup.py:137` — already imports it lazily inside the function.
**Fix:** `startup_config.py` is a *first-launch provisioning routine*, not configuration. Move it to `voxkit/services/` or `voxkit/gui/workers/`, drop it from `config/__init__.py`, and have `main.py:114` import it from its new home. If it must stay, move the five imports inside the two functions.

#### CF-8. `Defaults` is an untyped global dict of placeholder paths that reach the UI — `Medium` / `M`
**Where:** `src/voxkit/config/startup_config.py:17-23`, consumed at `src/voxkit/gui/pages/pipeline/pllr_stacker.py:343` and `src/voxkit/gui/pages/pipeline/training_stacker.py:45`
**What:**
```python
Defaults = {
    "mode": "W2TGENGINE",
    "output_path": "/path/to/output",
    "audio_path": "/path/to/audio",
    "textgrid_path": "/path/to/textgrids",
    "num_epochs": 10,
}
```
`pllr_stacker.py:343` does `QLineEdit(Defaults["output_path"])` and `training_stacker.py:45` does `self.train_textgrid_path = Defaults["textgrid_path"]` — so the literal string `/path/to/output` is the initial text a user sees in the PLLR output field, and `/path/to/textgrids` is the value submitted if training runs without a browse. It's a mutable module-level `dict` with inferred type `dict[str, object]`, accessed by raw string key with no accessor, so a typo is a runtime `KeyError` rather than a type error. Grepped: `"mode"`, `"audio_path"`, and `"num_epochs"` have zero consumers.
**Why it's debt:** Global mutable state any importer can silently mutate; `Defaults["ouput_path"]` type-checks fine and crashes at runtime; and shipping `/path/to/output` as a UI default is user-visible sloppiness that also means "unset" and "user typed a real path" are indistinguishable downstream.
**Fix:** Replace with a frozen dataclass or `Final` typed constants; delete the three unused keys; use `QLineEdit()` with `setPlaceholderText("Select an output directory…")` so empty means empty.

#### CF-9. `AppName`, `Dimensions`, and `Mode` are dead public exports — and `Mode` is the one abstraction the codebase actually needs — `Medium` / `S`
**Where:** `src/voxkit/config/startup_config.py:15`, `:16`, `:25`; exported at `src/voxkit/config/__init__.py:45-48` and listed in `__all__` at `:67-70`
**What:** Grepped `src/`, `tests/`, `main.py`, `scripts/`, `hooks/`: `AppName = "VoxKit"`, `Dimensions = {"min_width": 200, ...}`, and `Mode = Literal["MFAENGINE", "W2TGENGINE"]` have **zero** consumers outside their own definition and the `__init__.py` re-export. `AppName` also duplicates the `app_name` field that `AppConfig` loads from YAML (`app_config.py:149`).
**Why it's debt:** Dead code promoted to public API — `__all__` membership means removal now looks like a breaking change. Worse, `Mode` is the only place in the repo that types the engine-id domain, and it's unused: `"MFAENGINE"` / `"W2TGENGINE"` appear as bare magic strings in at least eight files (`engines/__init__.py:96-97`, `gui/pages/models/models_page.py:160,162,213,234`, `gui/pages/pipeline/prediction_stacker.py:222`, `gui/pages/models/import_dialog.py:34`, and `startup_config.py:51,85` itself).
**Fix:** Delete `AppName` and `Dimensions` and drop them from `__all__`. Promote `Mode` (or better, a `StrEnum`) into `engines/constants.py` where the engine layer can adopt it, and replace the magic strings.

#### CF-10. `resolve_config_file` — the core profile-fallback function — has no tests, and the tests that exist bind to live repo state — `Medium` / `M`
**Where:** `tests/config/test_app_config.py:5-11`, `:32-35`, `:145-156`
**What:** `resolve_config_file` is not imported by any test file — its per-file fallback to `profiles/default/` and its `FileNotFoundError` path (`app_config.py:92-104`) are entirely unexercised. Meanwhile `test_get_profile_config_path_is_inside_profiles` asserts `result.parent.name == "profiles"` against the *real* repo, so it silently exercises the happy path only and would break if `config/profiles/explanatory/` were removed rather than testing the fallback it triggers. `test_load_default_returns_config` and `test_get_app_config_returns_config` load whatever `config/profile.txt` happens to say (currently `explanatory`), so the assertions are necessarily vacuous (`assert config.app_name is not None`). `constants.py` and `startup_config.py` have no test file at all — the latter is also excluded from coverage in `pyproject.toml`.
**Why it's debt:** The profile system is the module's whole reason to exist, and its resolution rules are the thing CF-2 and CF-12 show are already inconsistent — precisely because nothing pins them. Tests reading live repo config also mean switching `profile.txt` changes what the suite tests.
**Fix:** Add tests that `monkeypatch` `get_config_root` to a `tmp_path` fixture with a synthetic `profiles/` tree, covering: file in active profile, file only in default, file in neither (expect `FileNotFoundError`), and active-profile-directory-missing.

#### CF-11. `UIConfig` defaults written twice — `Low` / `S`
**Where:** `src/voxkit/config/pipeline_config.py:65-67` and `:83-85`
**What:** The dataclass declares `menu_max_width: int = 500`, `animation_duration: int = 300`, `content_spacing: int = 20`; `from_dict` then repeats all three literals as `.get()` fallbacks (`data.get("menu_max_width", 500)`, etc.).
**Why it's debt:** Two sources of truth for the same three numbers; changing one and not the other splits behavior between `UIConfig()` and `UIConfig.from_dict({})`. `tests/config/test_pipeline_config.py:94-106` asserts both paths give the same answer, which is only true by hand-maintained coincidence.
**Fix:** `return cls(**{k: v for k, v in (data or {}).items() if k in {f.name for f in fields(cls)}})`, or drop the `.get()` defaults and let the dataclass supply them.

#### CF-12. The "legacy fallback" root YAML files are unreachable, and two docstrings claim a fallback that doesn't exist — `Low` / `S`
**Where:** `src/voxkit/config/app_config.py:167` and `src/voxkit/config/pipeline_config.py:141`
**What:** Both `load_default` docstrings say "Falls back to default profile **or config root** if not found." `resolve_config_file` (lines 88-104) checks only `profiles/<profile>/` then `profiles/default/`, then raises — it never looks at the config root. Since both `config/profiles/default/` and `config/profiles/explanatory/` exist, `config/app_info.yaml` and `config/pipeline_definitions.yaml` are dead files on every code path except `get_profile_config_path()`'s directory-level fallback, which only fires if the whole profile directory is missing. Verified they are stale duplicates: `config/pipeline_definitions.yaml` is byte-identical to `config/profiles/default/pipeline_definitions.yaml` (13 KB), and the two `app_info.yaml` copies have already drifted (root says "Goodness of Pronunciation (PLLR)", the profile copy says "(GOP)").
**Why it's debt:** AGENTS.md documents these as "Legacy fallback metadata," so a reader will edit the root file and see no effect. The drifted copy proves someone already has.
**Fix:** Correct both docstrings to describe the actual two-step fallback. Then either delete the root duplicates (ROOT agent's call — see cross-module notes) or make `resolve_config_file` genuinely fall back to the config root as documented; do not leave both.

#### CF-13. `reset_logging` closes handlers it did not install — `Low` / `S`
**Where:** `src/voxkit/config/logging_config.py:74-81`
**What:** The docstring says "Remove handlers installed by :func:`setup_logging`", but the body iterates *every* root handler and calls `removeHandler` + `handler.close()` unconditionally. In a real process the root logger also carries the `StreamHandler` from `logging.basicConfig` (`main.py:46`) and the Qt handler from `get_gui_log_handler()` (`main.py:131-132`).
**Why it's debt:** Docstring and behavior disagree on ownership. Today only tests call it (`tests/config/test_logging_config.py:10-15`), so impact is nil — but the name and docstring invite production use, and the first such call would close the GUI log handler and break the live log viewer with no error. Related: `_configured` is module-global mutable state (line 23) whose only reset path is this function.
**Fix:** Track the handler `setup_logging` installed in a module-level reference and remove only that one, or rename to `reset_all_logging` and state the real behavior.

#### CF-14. Small cleanups: missing module docstring, missing return annotation, stale mypy comment, dead coverage entry, mixed typing style — `Low` / `S`
**Where:** `src/voxkit/config/startup_config.py:1` and `:28`; `src/voxkit/config/app_config.py:31-33` and `:115-118`; `pyproject.toml` `[tool.coverage.run] omit`
**What:**
- `startup_config.py` is one of only 5 files out of 69 under `src/voxkit/` with no module docstring, and the only one in this module. Since `invoke generate-documentation` runs pdoc over the package, it renders as an untitled module.
- `def startup_routine():` (line 28) has no return annotation, and its one-line docstring still calls itself an "Example startup routine" even though `STARTUP_SCRIPT` (line 160) wires it as the real one.
- `app_config.py:32` carries the comment `# mypy: ignore attr-defined on _MEIPASS - it's dynamically added by PyInstaller`, but there is no `# type: ignore` on the line it precedes — the code uses `getattr(sys, "_MEIPASS")`, which needs no suppression. The comment documents a workaround that isn't there. Lines 30 and 33 also do the same `getattr` lookup twice.
- `pyproject.toml` omits `"src/voxkit/config.py"` from coverage — that path does not exist (the module became a package); the live path `src/voxkit/config/startup_config.py` is listed on the next line.
- `AppConfig` mixes typing styles within one dataclass body: `help_url: str | None = None` (line 115) next to `release_date: Optional[str] = None` (line 117). `pipeline_config.py` uses `Dict`/`List`/`Optional` throughout while `app_config.py` mostly uses PEP 604. Ruff's `select` list has no `UP` rules, so no linter catches this.
**Why it's debt:** Individually trivial; collectively they are the signals a reader uses to judge whether the rest of the file is maintained — and the stale mypy comment actively misinforms.
**Fix:** Add the module docstring and `-> None`; delete the stale comment and hoist `_MEIPASS` to a local; drop the dead coverage path; pick one `Optional` style per the PEP 604 majority (or add `UP` to ruff's `select` and let it enforce).

### Cross-module notes

- **`pydantic>=2.12.3` is a declared runtime dependency with zero usages** anywhere in `src/` or `tests/` (grepped for `pydantic` and `BaseModel`). Either adopt it for config schema validation (it would resolve CF-3 and CF-4 cleanly) or drop it from `pyproject.toml`.
- **`src/voxkit/services/` has no `__init__.py`** yet `startup_config.py:6` does `from voxkit.services import mfa_provision`. It works as an implicit namespace package from source and under PyInstaller, but `[tool.setuptools.packages.find]` uses `find` (not `find_namespace`), so `voxkit.services` would be silently omitted from a wheel/sdist install. Services module's call, but it's my module's import that would break first.
- **`config/app_info.yaml` and `config/pipeline_definitions.yaml` at the repo root are dead and drifting** — see CF-12 for the evidence. The loader-side docstring fix is mine; deciding whether to delete the files is the ROOT agent's.
- **`config/profiles/*/app_info.yaml` all define `research_context:` and `contact_info.github_issues` / `contact_info.documentation`, none of which `AppConfig` reads** (only `email_support` is consumed, at `app_config.py:154`). Unknown YAML keys are silently dropped with no warning — a researcher editing `research_context` gets no feedback that it does nothing. Whether those keys should exist is a ROOT/product question; that the loader discards them silently is CF-3's validation gap.
- **`import voxkit.config` takes ~7.7s and pulls in torch, transformers, datasets, PyQt6, speechbrain, librosa, and matplotlib.** Measured, not estimated. The bulk of this is `src/voxkit/__init__.py:17` eagerly importing `gui`/`engines`, which AGENTS.md documents as intentional for pdoc — not my finding. But CF-7 means `config` now adds `storage` and `services` to that chain too, so no lightweight path to a config value exists in either direction.


---

## Module: `src/voxkit/analyzers/`

**Health:** Small and readable, but two of three analyzers are wholly untested, the chart code is a copy-paste fork that has already drifted, and every failure path is `print`-and-continue. | **Files:** 5 | **LOC:** 655 | **Findings:** 13 (3 High / 5 Medium / 5 Low)

Four analyzers-worth of code (`DatasetAnalyzer` ABC + three implementations) scan a dataset's speaker subdirectories at registration time and emit row-dicts that `storage/datasets.py` writes to `{name}_summary.csv`; two of them also build a hand-painted Qt bar chart. The shape of the debt is *forking*: `AudioFormatProfileAnalyzer` and `ClipDurationStatisticsAnalyzer` were both created by copying `DefaultAnalyzer` and editing, so the scan loop, the error handling, and 87 lines of the chart renderer exist in duplicate — with visible drift between copies and no tests on either copy. Underneath that sits one design problem doing real damage: `analyze()` swallows every exception and returns partial results, which turns a torchaudio failure into a misleading `"Failed to create dataset metadata: No data to write to CSV."` for the user. The module is otherwise clean — no TODO/FIXME/HACK, no `type: ignore`, no `noqa`, no hardcoded filesystem paths, no commented-out code.

### Findings

#### AN-1. `analyze()` swallows all failures, and the result surfaces as a misleading storage error — `High` / `S`
**Where:** `src/voxkit/analyzers/default_analyzer.py:63-64`, `src/voxkit/analyzers/clip_duration_statistics.py:76-77`, `src/voxkit/analyzers/audio_format_profile.py:83-84`
**What:** All three analyzers wrap their *entire* per-speaker loop in one `try:` and end with the identical handler `except Exception as e: print(f"Error analyzing dataset: {e}")`, then `return results`. Because the `try` spans the whole loop rather than one directory, a failure on speaker 5 of 100 silently truncates the output to 4 rows and reports success. When it fails on speaker 1, `results` is `[]` — and `_save_analysis_csv` (`src/voxkit/storage/datasets.py:254-255`) raises `ValueError("No data to write to CSV.")`, which `create_dataset` catches at `:234`, `rmtree`s the half-built dataset directory, and returns `"Failed to create dataset metadata: No data to write to CSV."` to the GUI. The actual cause exists only as a `print` on stdout, which is invisible in a packaged PyInstaller build.
**Why it's debt:** A permission error, a bad path, or a torchaudio import failure all present to the user as an unrelated CSV message, and the dataset registration is rolled back with no recoverable diagnostic. Partial-scan truncation is worse: it produces plausible-looking but silently incomplete analysis data that is never re-derived (analysis runs once, at registration).
**Fix:** Move the `try` inside the per-directory loop so one bad speaker directory doesn't abort the scan (the per-*file* loops already do this correctly — `clip_duration_statistics.py:61-62`, `audio_format_profile.py:64-65`). Let genuinely fatal errors (nonexistent root, permission denied) propagate to `DatasetRegistrationWorker.run` so the worker can emit a real message, and replace the `print` with `logger.exception`.

#### AN-2. `visualize` is duplicated across two analyzers — 87 of ~115 lines byte-identical, already drifting — `High` / `M`
**Where:** `src/voxkit/analyzers/default_analyzer.py:68-180` vs `src/voxkit/analyzers/clip_duration_statistics.py:81-199`
**What:** A line-by-line diff of the two methods shows 87 identical lines. Both define the same nested `_Canvas(QWidget)` inside the method body, the same layout constants (`BAR_HEIGHT = 28`, `BAR_SPACING = 6`, `LABEL_WIDTH = 140`, `PADDING = 16`), the same `total_h = PADDING + len(entries) * (BAR_HEIGHT + BAR_SPACING) + PADDING`, the same elided-label drawing, the same HSL lightening formula `new_l = int(lightness + (220 - lightness) * (1 - ratio))` / `color.setHsl(h, s, min(new_l, 240), a)`, the same `QScrollArea` + stats-`QLabel` scaffolding, and the same stylesheet strings. Only the value column width, the bar color, and the label formatting genuinely differ. The copies have already diverged: `default_analyzer.py:130-132` asserts `h is not None and s is not None and lightness is not None and a is not None`, while `clip_duration_statistics.py:145` dropped the `a is not None` clause.
**Why it's debt:** Any visual change — theme support, a different bar metric, DPI handling — must be made twice and is being made twice inconsistently. It is also ~200 of the module's 655 lines, so it dominates the module's size while carrying almost no unique logic. The nested `_Canvas` closes over `entries`, `max_total`, and `total_h`, so a fresh class object is built per call and the widget can never be re-fed data without being rebuilt; it is also unreachable from a test except through the whole `visualize` call.
**Fix:** Extract one `_horizontal_bar_chart(entries, bar_color, value_formatter, value_width, footer_text)` helper (module-level, or a mixin on `DatasetAnalyzer`) and have both analyzers call it with their three differences as arguments. While there, hoist the two `QFont()` constructions out of `paintEvent` (`default_analyzer.py:110-111, 141-144`) — they are currently rebuilt per row per repaint.

#### AN-3. Two of the three analyzers have zero tests, against an explicit project standard — `High` / `M`
**Where:** `tests/analyzers/` contains only `test_default_analyzer.py` and `test_analyzer_manager.py`
**What:** `ClipDurationStatisticsAnalyzer` (199 LOC) and `AudioFormatProfileAnalyzer` (86 LOC) — 285 LOC, 44% of the module — are not imported by any test. `AGENTS.md:84` states: "Write tests for new business logic in `storage/`, `config/`, `analyzers/`." `pyproject.toml`'s `[tool.coverage.run] omit` list (lines 140-172) deliberately does *not* exclude `src/voxkit/analyzers/`, so these files count against the coverage badge. `DefaultAnalyzer` by contrast has 20 tests covering extensions, casing, empty dirs, nonexistent paths, and all eight visualize edge cases (`tests/analyzers/test_default_analyzer.py:43-208`) — the pattern to copy exists and was simply not applied.
**Why it's debt:** Nothing exercises the `torchaudio.info` → `torchaudio.load` fallback branches (`clip_duration_statistics.py:55-60`, `audio_format_profile.py:57-63`), the `Counter(...).most_common(1)[0][0]` dominant-format logic (`audio_format_profile.py:70-72`), the `inconsistent_files` count, or the duration chart. This directly blocks AN-2: the duplication cannot be refactored safely because half of the duplicated code has no regression net.
**Fix:** Mirror `test_default_analyzer.py` for both. Generating real short WAVs with `torchaudio.save` in a `tmp_path` fixture covers the metadata path without mocking; a monkeypatched `torchaudio.info` returning `num_frames = 0` covers the decode fallback.

#### AN-4. Analyzer `name` is simultaneously display string, registry key, and CSV filename — `Medium` / `M`
**Where:** `src/voxkit/analyzers/base.py:46-53`, `src/voxkit/analyzers/__init__.py:88-92`, and the round trip through `src/voxkit/storage/datasets.py:221` → `src/voxkit/gui/pages/datasets/datasets_page.py:952-960`
**What:** `base.py:49` documents `name` as "Display name for this analysis method" and it is rendered as such in a tooltip (`datasets_page.py:656`). But `__init__.py:88-92` also uses it as the registry key (`_duration.name: _duration`), `storage/datasets.py:221` bakes it into a path — `csv_path = dataset_dir / f"{analysis_method.lower()}_summary.csv"` — and `datasets_page.py:952-958` reverses that by string surgery: `file_name = csv_files[0].stem.replace("_summary", "").lower()`, then linear-scans for `key.lower() == file_name`. So `"Clip Duration Statistics"` produces the on-disk file `clip duration statistics_summary.csv`, with spaces.
**Why it's debt:** Renaming an analyzer for UI reasons orphans every previously written CSV; the reverse lookup then raises, and `datasets_page.py:964-965` swallows it with `print(f"Visualization failed ...")`, so the user just silently loses their chart with no message. A future analyzer named with `/`, `:`, or `*` produces an invalid filename on at least one supported platform. The sibling module already solved this — `EngineManager` keys off a separate `id` (`engines/__init__.py:94-97`, e.g. `"MFAENGINE"`), not the display name.
**Fix:** Add an `id` (or `slug`) abstract property to `DatasetAnalyzer`, key the registry and the CSV filename off it, and keep `name` purely for display.

#### AN-5. Hidden directories are counted as speakers, contradicting `validate_dataset` — `Medium` / `S`
**Where:** `src/voxkit/analyzers/default_analyzer.py:51-52`, `src/voxkit/analyzers/clip_duration_statistics.py:45-47`, `src/voxkit/analyzers/audio_format_profile.py:46-48`
**What:** All three iterate `os.scandir(dataset_path)` and accept anything where `entry.is_dir()` is true. `storage/datasets.py:607-609`, which validates the exact same directory immediately before (`datasets_thread.py:55` then `:67`), explicitly skips them: `if subdir.startswith("."): continue  # Skip hidden files/directories`.
**Why it's debt:** `.ipynb_checkpoints`, `.git`, `.Trashes`, and macOS `.fseventsd` become phantom speaker rows. `test_default_analyzer.py:71-78` confirms the behavior — any empty directory yields `{"speaker_id": ..., "audio_file_count": 0}` — so the CSV, the speaker count in the chart footer (`default_analyzer.py:169`), and the `avg files/speaker` figure are all wrong for any dataset carrying a dotfile directory. Two modules holding different definitions of "speaker directory" over the same path is the kind of divergence that only shows up as a confusing number in a research report.
**Fix:** Skip `entry.name.startswith(".")` in all three, ideally via one shared `_iter_speaker_dirs(dataset_path)` helper that both this module and `validate_dataset` agree on.

#### AN-6. Three different error channels inside one module, including a `print` in a pure getter — `Medium` / `S`
**Where:** `src/voxkit/analyzers/__init__.py:67`; `src/voxkit/analyzers/audio_format_profile.py:65` and `:84`
**What:** `AnalyzerManager.list_analyzers` — a query with no side effects — executes `print(f"[AnalyzerManager] Registered analyzers: {keys}")` on every call, and it is called during page construction at `datasets_page.py:97`. Meanwhile `audio_format_profile.analyze` uses *both* mechanisms in one method: `logger.warning("Skipping %s: %s", f.path, e)` at `:65` and `print(f"Error analyzing dataset: {e}")` at `:84`. `clip_duration_statistics.py:62/:77` does the same. `default_analyzer.py` declares no logger at all and only prints.
**Why it's debt:** Half the module's diagnostics are unroutable, unfilterable, and invisible in a packaged build; the other half go through `logging`. Anyone debugging a failed registration has to know which analyzer wrote which kind of output. The getter's `print` also makes `list_analyzers` unusable in any tight loop or non-interactive context.
**Fix:** Add `logger = logging.getLogger(__name__)` to `default_analyzer.py` and `__init__.py`, convert all four `print` calls to `logger.warning`/`logger.debug`, and drop the one in `list_analyzers` entirely.

#### AN-7. `get_analyzer()` has no production callers; both real call sites bypass it and reach into the live dict — `Medium` / `S`
**Where:** `src/voxkit/analyzers/__init__.py:70-79`
**What:** `get_analyzer(analyzer_id)` converts a `KeyError` into `ValueError(f"No analyzer with id: {analyzer_id}")`. Grepping all of `src/` finds no caller — the only references are `tests/analyzers/test_analyzer_manager.py:39, 45, 58, 88`. Production instead does `ManageAnalyzers.get_analyzers()[self.analysis_method]` (`gui/workers/datasets_thread.py:67`) and iterates `ManageAnalyzers.get_analyzers().items()` (`datasets_page.py:955`). Separately, `get_analyzers()` at `:70-72` returns `self._analyzers` itself, not a copy.
**Why it's debt:** The defensive error path exists, is tested, and never runs — so on a stale or renamed `analysis_method` the worker thread dies with a bare `KeyError` inside `QThread.run()` (no `finished` signal is emitted, leaving the registration dialog hanging) rather than raising the readable `ValueError` the module was built to produce. Handing out the internal dict also means any caller can mutate the process-wide singleton registry.
**Fix:** Route `datasets_thread.py:67` through `get_analyzer()`, return `MappingProxyType(self._analyzers)` from `get_analyzers()`, and add `from e` to the re-raise at `:79` so the original `KeyError` context survives.

#### AN-8. `DefaultAnalyzer.visualize` is unannotated, so mypy skips its entire body — `Medium` / `S`
**Where:** `src/voxkit/analyzers/default_analyzer.py:68`
**What:** `def visualize(self, data):` — no parameter type, no return type — overrides `base.py:79`, which declares `def visualize(self, data: List[Dict[str, Any]]) -> QWidget | None`. `pyproject.toml:124` sets `check_untyped_defs = false`, so an entirely unannotated function body is not analyzed at all: lines 69-180, including all the Qt painting arithmetic and the `assert` at `:130-132`, are invisible to `invoke mypy-check`. The sibling `clip_duration_statistics.py:81` annotates its parameter (so its body *is* checked) but omits the return annotation, so the two overrides of the same abstract method are typed three different ways across the module.
**Why it's debt:** The largest and most fiddly block in the file is the one the type checker never sees, and nothing enforces that either override actually returns a `QWidget | None` as `datasets_page.py:963` assumes.
**Fix:** Annotate both as `def visualize(self, data: List[Dict[str, Any]]) -> QWidget | None:` (both files will need the `TYPE_CHECKING` import that `base.py:34-35` already models).

#### AN-9. Unreachable full-decode fallback in the format analyzer — a guard copied from the duration analyzer and pointed at the wrong field — `Low` / `S`
**Where:** `src/voxkit/analyzers/audio_format_profile.py:57-63`
**What:** The code reads `info = torchaudio.info(f.path)`, then `if info.sample_rate > 0:` records the metadata, `else:` calls `torchaudio.load(f.path)` and derives sample rate and channels from the decoded waveform. The comment justifying this pattern lives in the file it was copied from — `clip_duration_statistics.py:58`, "num_frames is unreliable for some formats (MP3, M4A, OGG)" — and applies to `num_frames`, not `sample_rate`. `torchaudio.info` raises on unreadable headers rather than returning a zero sample rate, and the formats with unreliable frame counts still report a valid sample rate, so the `else` branch is effectively unreachable.
**Why it's debt:** Ballast that looks load-bearing, and misleading if it ever *does* fire: it performs a full in-memory decode to recover two values `info` already supplied. A reader trying to understand the fallback's purpose is sent to the wrong conclusion.
**Fix:** Delete the `else` branch (the per-file `except Exception` at `:64-65` already covers unreadable files), or keep the guard and correct it to the field it was meant to test.

#### AN-10. Dead `avg` value threaded through the duration chart — `Low` / `S`
**Where:** `src/voxkit/analyzers/clip_duration_statistics.py:91`, `:95`, `:123`
**What:** `visualize` parses `avg = float(row.get("avg_duration_s", 0))` at `:91`, packs it into the tuple at `:95` (`entries.append((speaker, total, avg, file_count))`), and unpacks it in the paint loop at `:123` (`for speaker, total, avg, file_count in entries:`) — but `avg` never appears in the loop body (`:124-168`); the value label at `:160` uses only `total` and `file_count`. The chart's own footer recomputes a different average from scratch at `:187`.
**Why it's debt:** Ruff's `F841` does not flag unused loop-unpacking targets, so no tooling catches this; it survives as a false signal that the chart uses per-speaker averages. It also forces the `except (TypeError, ValueError)` at `:93` to guard a conversion whose result is discarded.
**Fix:** Drop `avg` from the parse, the tuple, and the unpack.

#### AN-11. Chart colors re-declare the app palette as literals instead of importing it — `Low` / `S`
**Where:** `src/voxkit/analyzers/default_analyzer.py:109, 128, 145, 166, 176` and `src/voxkit/analyzers/clip_duration_statistics.py:124, 143, 158, 181, 195`
**What:** The two charts hardcode `#2c3e50`, `#3498db`, `#27ae60`, and `#7f8c8d` — the exact values of `Colors.TEXT_PRIMARY`, `Colors.PRIMARY`, `Colors.SUCCESS`, and `Colors.TEXT_SECONDARY` defined in `src/voxkit/gui/styles/__init__.py:24-38`, whose own docstring states "All styles use f-strings referencing Colors for consistency." The scroll areas additionally pin `background: white` (`default_analyzer.py:166`, `clip_duration_statistics.py:181`) rather than using `Colors.WHITE`, and the stats labels inline `font-size: 12px; font-style: italic` instead of a `Labels` preset.
**Why it's debt:** A palette change in `styles/` silently leaves these two charts on the old colors — they are the only place in `src/` outside `gui/` (and `gui/components/grip_splitter.py`) that duplicates palette hexes. The literal `background: white` also blocks any future dark theme.
**Fix:** `from voxkit.gui.styles import Colors` inside the existing lazy-import block and reference the constants. Note this makes the `analyzers` → `gui` dependency explicit rather than implicit-by-copy; if that direction is unwanted, the palette belongs somewhere neutral (see cross-module notes).

#### AN-12. `__all__` hides the API the module docstring advertises; the singleton is named like a class — `Low` / `S`
**Where:** `src/voxkit/analyzers/__init__.py:95-97` and `:82-93`
**What:** `__all__ = ["ManageAnalyzers"]`, but the module docstring at `:5-9` documents `AnalyzerManager.list_analyzers`, `AnalyzerManager.get_analyzer`, and `AnalyzerManager.get_analyzers` as the module's API section, and `tests/analyzers/test_analyzer_manager.py:52, 61, 80` imports `AnalyzerManager` directly while `:4` imports `DatasetAnalyzer`. `invoke generate-documentation` runs pdoc, which honors `__all__`, so the documented names are excluded from the generated HTML. Separately, the singleton is `ManageAnalyzers` — a verb phrase in PascalCase for an *instance*; the sibling module names its equivalent `engines` (`engines/__init__.py:97`), and `base.py:12` instructs contributors to "Register the instance in `voxkit.analyzers.__init__`" without naming it.
**Why it's debt:** Generated docs don't match the hand-written API list in the same file, and `ManageAnalyzers` reads as a class at every call site (`ManageAnalyzers.get_analyzers()` looks like a classmethod), which is why callers reach for dict indexing instead of the instance methods (see AN-7).
**Fix:** Add `AnalyzerManager` and `DatasetAnalyzer` to `__all__`. Renaming the singleton to `analyzers` for symmetry with `engines` touches three call sites (`datasets_thread.py:13/67`, `datasets_page.py:32/97/656/955`) — worth doing alongside AN-7.

#### AN-13. Missing docstrings on the two newer analyzers' overrides — `Low` / `S`
**Where:** `src/voxkit/analyzers/audio_format_profile.py:31-39`, `src/voxkit/analyzers/clip_duration_statistics.py:30-38` and `:81`
**What:** `name`, `description`, and `analyze` in both newer analyzers carry no docstring, while `base.py:46-93` documents all four members in full Google style with `Args:`/`Returns:`, and `DefaultAnalyzer.analyze` (`default_analyzer.py:37-46`) follows that. Both files do have thorough module-level docstrings listing their output columns, so the information exists — it just isn't attached to the callables pdoc renders.
**Why it's debt:** `invoke generate-documentation` emits bare signatures for these methods, and the inconsistency within a five-file module (documented base, documented `DefaultAnalyzer`, undocumented siblings) means there's no pattern for the next contributor to follow. The project ships a `python-docstring-enforcer` agent, so the standard is intended even if not written down in `docs/CONTRIBUTING.md`.
**Fix:** Add one-line docstrings to `name`/`description` and an `Args:`/`Returns:` docstring to `analyze` in both files, matching `default_analyzer.py:37-46`.

### Cross-module notes

- **`AnalyzerManager` is a near-verbatim clone of `EngineManager`.** `analyzers/__init__.py:52-79` and `engines/__init__.py:57-88` share the same constructor shape, the same `list_*` method that `print`s its own result before returning it, and the same `except KeyError: raise ValueError(f"No {kind} with id: {id}")` without `from e`. A shared generic `Registry[T]` would collapse both and fix AN-6/AN-7 in one place. Belongs to whoever owns `engines/`.
- **`validate_dataset` matches extensions case-sensitively; the analyzers don't.** `storage/datasets.py:630` uses `f.endswith(tuple(SUPERSET_AUDIO_EXTENSIONS))` while all three analyzers use `Path(f.name).suffix.lower() in SUPERSET_AUDIO_EXTENSIONS`. A dataset of `.WAV` files fails validation outright but would have analyzed cleanly — the two consumers of the same constant disagree.
- **The visualization error path in the GUI is silent.** `gui/pages/datasets/datasets_page.py:964-965` catches every exception from analyzer lookup, CSV parsing, and `visualize()` and only `print`s it, then falls through to a plain table with no user-facing indication that a chart was expected. Combined with AN-4, a renamed analyzer degrades invisibly.
- **`analyze()` runs unbounded and uncancellable on the worker thread.** `gui/workers/datasets_thread.py:64-69` emits `"Analyzing dataset..."` once and then blocks in `analyze()`. The two metadata analyzers make one `torchaudio.info` call per audio file with no progress callback, so a large corpus freezes the dialog on a static string. The `DatasetAnalyzer` interface has no hook for progress or cancellation — an interface gap, not an implementation bug.
- **Docs overstate the registration mechanism.** `AGENTS.md:42` and `docs/ARCHITECTURE.md:57` both say analyzers have a "singleton manager for discovery," but there is no discovery — `analyzers/__init__.py:82-93` is a hand-maintained list requiring three coordinated edits per new analyzer, exactly as `base.py:5-12` instructs. Either the docs should say "manual registry" or the module should scan its own package.
- **Palette constants live in `gui/styles/`, which non-GUI modules can't import cleanly.** AN-11's fix requires `analyzers` to depend on `gui`, which inverts the intended layering in `docs/ARCHITECTURE.md:21-57`. The real answer is probably a neutral home for `Colors` — an architecture-level call, not an analyzers one.


---

## Module: `src/voxkit/gui/pages/pipeline/`

**Health:** Debt-heavy — a 208-line base class carrying ~6.5k lines of siblings that mostly ignore it; the three timeline stackers are 27–52% literal copies of each other. | **Files:** 10 | **LOC:** 6736 | **Findings:** 11 (5 High / 5 Medium / 1 Low)

This module hosts the pipeline step UIs ("stackers") plus the `PipelineFormStack` container that instantiates them from `config/profiles/<name>/pipeline_definitions.yaml` via `STACKER_REGISTRY`. **The duplication verdict is: it is not "the same code eight times" — it is the same code *three* times, but those three files are 4577 of the 6736 lines.** A mechanical identical-block scan (runs of ≥6 identical stripped lines) shows `correct_alignments_stacker.py` is 623/1206 lines (52%) verbatim copy of a sibling, `comparison_stacker.py` 383/1279 (30%), and `viewer_stacker.py` 570/2092 (27%) — ~30 methods (audio player, zoom/pan/scroll, play-selection, temp-file cleanup, speaker/file browsing, dropdown population, Tab event filter) exist in triplicate, and the code comments openly acknowledge it ("see ViewerStacker's identical mechanism", "identical method", "identical event filter"). The second axis of debt is that `BaseStacker` under-abstracts everything past the header/status label: it provides no dataset-dropdown helper, no worker-launch helper, no error-display helper, and no validation helper, so all eight siblings hand-roll those — and one stacker (`PLLRStacker`) doesn't even inherit from it. Layered on top: 82 `print()` calls as the only diagnostics, several genuinely dead code paths (including a cross-page model refresh that has never once fired), and worker-thread bodies that read Qt widget state off the GUI thread.

### Stacker comparison

| Stacker | LOC | Base class | Form building | Validation | Worker launch | Error display | Result handling | Reload |
|---|---|---|---|---|---|---|---|---|
| `MarkdownStacker` | 75 | inherits | reimplements (trivial) | n/a | n/a | n/a | n/a | n/a |
| `TranscriptionStacker` | 221 | inherits | reimplements | reimplements (`QMessageBox`, 3 guards) | reimplements | reimplements (`QMessageBox` ×5) | reimplements | reimplements |
| `PredictionStacker` | 256 | inherits | reimplements | reimplements (`QMessageBox`, 3 guards) | reimplements ×2 | reimplements (`QMessageBox` ×9) | reimplements ×2 | reimplements |
| `TrainingStacker` | 373 | inherits | reimplements | reimplements (94-line `on_train_model`) | reimplements | reimplements (`QMessageBox` ×10) | reimplements | reimplements |
| `PLLRStacker` | 693 | **does NOT inherit** | reimplements + reimplements header/status/progress | reimplements (136-line `on_extract_pllr`) | reimplements | reimplements (`QMessageBox` ×9 + inline hex) | reimplements | reimplements |
| `ViewerStacker` | 2092 | inherits | reimplements (274-line `build_ui`) | n/a (browse-only) | reimplements (in panels) | reimplements (`set_status`) | reimplements | reimplements |
| `ComparisonStacker` | 1279 | inherits | **copies Viewer** (160 + 166-line builders) | reimplements | **copies Viewer** | reimplements (`set_status`) | reimplements | **copies Viewer** |
| `CorrectAlignmentsStacker` | 1206 | inherits | **copies Viewer** (273-line `build_ui`) | reimplements | **copies Viewer** | reimplements (`set_status`) | reimplements | **copies Viewer** |

Only `get_title()` / `has_settings()` / `has_status_label()` / `set_status()` are genuinely inherited anywhere.

### Findings

#### PL-1. Three timeline stackers are 27–52% verbatim copies of one another — `High` / `L`
**Where:** `src/voxkit/gui/pages/pipeline/viewer_stacker.py`, `comparison_stacker.py`, `correct_alignments_stacker.py`. Measured identical-block pairs (≥6 identical stripped lines, `dup.py` scan):
- `viewer_stacker.py:1273-1323` == `correct_alignments_stacker.py:367-417` (51 lines, speaker/file selection row)
- `viewer_stacker.py:1568-1616` == `correct_alignments_stacker.py:669-717` (49 lines, `_on_dataset_changed` alignment-dropdown block)
- `viewer_stacker.py:1524-1566` == `correct_alignments_stacker.py:619-661` (43 lines, `reload_datasets`)
- `comparison_stacker.py:1195-1249` == `correct_alignments_stacker.py:1011-1065` (55 lines, `_play_selection` + `_on_selection_*` + `_cleanup_stale_selection_temp_files`)
- `viewer_stacker.py:1325-1356` == `comparison_stacker.py:422-450` == `correct_alignments_stacker.py:418-449` (29–32 lines, audio controls row)
- `viewer_stacker.py:1788-1820` == `correct_alignments_stacker.py:870-902` (33 lines, `_toggle_playback`/`_stop_playback`/`_seek_to_ms`/`_seek_to_seconds`/`_on_playback_state_changed`/`_on_position_changed`)
- `viewer_stacker.py:1919-1938` == `comparison_stacker.py:1074-1093` (20 lines, `_zoom_by`/`_set_shared_view`/`_set_shared_selection`)
- `viewer_stacker.py:1499-1513` == `comparison_stacker.py:340-354` == `correct_alignments_stacker.py:595-609` (15–25 lines, multimedia player init + `eventFilter`)

Full method triplicates (Viewer / Comparison / Correct line numbers): `_toggle_playback` (1788/1119/870), `_stop_playback` (1797/1128/879), `_seek_to_ms` (1802/1133/884), `_seek_to_seconds` (1807/1138/889), `_on_playback_state_changed` (1812/1143/894), `_on_position_changed` (1820/1151/902), `_on_duration_changed` (1854/1166/917), `_fmt_ms` (2073/1180/926), `_set_shared_duration` (1873/1024/931), `_on_zoom_requested` (1894/1049/946), `_on_pan_requested` (1905/1060/956), `_zoom_by` (1914/1069/964), `_set_shared_view` (1924/1079/972), `_set_shared_selection` (1930/1085/977), `_update_scrollbar` (1938/1093/984), `_on_scrollbar_changed` (1960/1109/1000), `_play_selection` (1968/1186/1010), `_on_selection_position_changed` (2011/1225/1041), `_on_selection_media_status_changed` (2021/1234/1050), `_stop_selection_playback` (2029/1241/1057), `_cleanup_stale_selection_temp_files` (2037/1249/1065), `eventFilter` (1509/350/605), `_make_section_label` (2078/1272/1194), `_populate_speakers` (1630/687/744), `_on_speaker_changed` (1641/908/755), `_filter_file_list` (1662/929/776), `_on_file_selected` (1674/939/786), `_on_spectrogram_toggled` (1694/958/808).

**What:** `TimeAxisMixin` (`viewer_stacker.py:175`) was correctly extracted for the *panel-side* time↔pixel math, but nothing was extracted for the *coordinator* side. Every stacker that owns a set of synced panels re-implements the identical `_synced_panels` broadcast loop, the identical dual-`QMediaPlayer` setup, the identical `tempfile.mkstemp` → `sf.write` → play-clip selection playback, and the identical best-effort temp-file reaper. The three `_update_scrollbar` bodies share the same undocumented magic `resolution = 10000` (`viewer_stacker.py:1952`, `comparison_stacker.py:1101`, `correct_alignments_stacker.py:992`) and matching `value / 10000` at `viewer_stacker.py:1965`, `comparison_stacker.py:1114`, `correct_alignments_stacker.py:1005`.

**Why it's debt:** Every fix has to be applied three times or it silently regresses in the other two. The code proves this already happened: `ViewerStacker._on_position_changed` calls `self._update_active_segment_label(secs)` (line 1837) and `_on_selection_media_status_changed` calls it too (line 2027); the copies in `comparison_stacker.py:1151` and `correct_alignments_stacker.py:902` dropped it, so the two copies diverged. `ComparisonStacker._on_duration_changed:1166` carries a comment pointing at "the identical fix in ViewerStacker" — a fix that had to be made twice. `CorrectAlignmentsStacker._on_duration_changed:917` silently lost the explanatory comment entirely.

**Fix:** Extract a `SyncedTimelinePanel` composite `QWidget` (waveform + spectrogram + N timelines + audio row + zoom row + scrollbar) exposing `load(audio_path, tiers_by_label)`, `set_selection()`, and a `boundary_edited` passthrough. All three stackers become "instantiate it, wire the dropdowns, hand it a file". Realistically ~1000 lines deleted. Do the shared audio-player/selection-playback half first (`_play_selection` + the 6 `_on_*` slots + `_cleanup_stale_selection_temp_files`) — that block is already byte-identical, so it lifts with zero behavior risk.

#### PL-2. `PLLRStacker` is registered as a stacker but doesn't inherit `BaseStacker` — `High` / `M`
**Where:** `src/voxkit/gui/pages/pipeline/pllr_stacker.py:177` (`class PLLRStacker(QWidget)`), registered alongside the real stackers at `__init__.py:113`.
**What:** It hand-rolls everything `BaseStacker` provides: `init_ui()` at :275 duplicates `BaseStacker.init_ui`'s `setMinimumWidth(600)` / spacing 15 / margins `(30,30,30,30)`; :283-299 duplicates `_create_header()` including the identical `QPushButton("⚙️")` + `setFixedSize(65, 40)` + `Buttons.ICON`; :362-374 duplicates `_create_status_label()` including the verbatim "Indeterminate (busy) bar: range (0, 0)…" comment from `base_stacker.py:109-110`. Because it has no `set_status()`, it hardcodes status colors inline: `"color: #f39c12; …"` (:512), `"color: #27ae60; …"` (:687), `"color: #e74c3c; …"` (:692) — which are exactly `Colors.WARNING`, `Colors.SUCCESS`, `Colors.ERROR` from `src/voxkit/gui/styles/__init__.py:35-37`. `init_ui()` also pointlessly `return self` (:377). Separately, `get_pllr_settings_config()` at :102 does `fields = FIELDS.copy()` (a *shallow* list copy) then mutates `field.default_value` at :104 — permanently mutating the module-level `FieldConfig` objects declared at :51.
**Why it's debt:** `PipelineFormStack` treats it as a peer of the other stackers, so any change to the base contract (a new lifecycle hook, a restyle of the status label, a shared progress mechanism) silently skips this page. It also means the file is exempt from `tests/gui/test_base_stacker.py`'s guarantees. The three hardcoded hex colors are already drifting from the palette they were copied from.
**Fix:** Make it `class PLLRStacker(BaseStacker)`, delete `init_ui()` in favour of `build_ui()`, delete `extract_status`/`extract_progress` in favour of the inherited `status_label`/`progress_bar` + `set_status()`. Replace `FIELDS.copy()` with `copy.deepcopy(FIELDS)` or build the field list inside the function.

#### PL-3. Worker-thread bodies read Qt widget state off the GUI thread; completion handlers re-read stale widget state — `High` / `M`
**Where:**
- `training_stacker.py:223-235` — `train_model_logic` runs on a `WorkerThread` but calls `self.model_panel.get_selected_engine()` (:227) and `self.model_panel.get_selected_model_id()` (:228) *from that thread*.
- `prediction_stacker.py:191-207` — `predict_alignments_logic` likewise reads `self.model_panel.get_selected_model_id()` (:194) and `get_selected_engine()` (:195) from the worker thread.
- `comparison_stacker.py:753-770` — `_compute()` runs on the worker and writes `self._pending_comparison_data` (:763), read back on the GUI thread at :794.
- `correct_alignments_stacker.py:1122-1126` — `_create()` writes `self._pending_create_result` from the worker thread; read at :1137.
- `viewer_stacker.py:711-720` / `:990-993` — worker writes `self._pending_peaks`/`_pending_Sxx_db`/`_pending_token` as undeclared instance attributes, read via `getattr(self, "_pending_token", None)` (:730, :1003).
- `transcription_stacker.py:211` — the *failure* branch of `on_transcribe_finished` re-reads `self.dataset_dropdown.current_id()` instead of the `selected_dataset_id` captured at :155.
**What:** Two distinct problems. (a) Reading `QComboBox`/panel state from a non-GUI thread is not thread-safe in Qt; it happens to work today because the button is disabled during the run, but it is an unguarded invariant. (b) The `transcription` case is a live bug: transcription can take minutes, the dropdown stays enabled, and if the user changes selection mid-run, the failure path marks *the wrong dataset* `transcribed: False`. Both `datasets.update_dataset_metadata(...)` calls (:192, :213) also discard the `(bool, str)` return — a failed metadata write is silently invisible.
**Why it's debt:** These are exactly the failures that reproduce once in production and never in dev. The `_pending_*` handoff pattern also defeats mypy (undeclared attributes reached via `getattr` with a default).
**Fix:** Capture every value the worker needs into the closure at launch time (as `transcription_stacker.py:182` and `pllr_stacker.py:519` already do correctly). Replace the `self._pending_*` handoff with a `WorkerThread` variant whose `finished` signal carries the result object. Check the `update_dataset_metadata` return and surface failures via `set_status(..., "error")`.

#### PL-4. Five distinct dead / never-firing code paths — `High` / `M`
**Where:**
1. `training_stacker.py:259-260` — `if hasattr(self.parent, "pipeline_container"): self.parent.pipeline_container.reload()`. `self.parent` is `QWidget.parent`, a *bound method*, not the parent widget (`BaseStacker.__init__` stores it as `self._parent_widget`, `base_stacker.py:48`). `hasattr(<bound method>, "pipeline_container")` is always `False`. `pipeline_container` really does exist, on the main window (`src/voxkit/gui/__init__.py:436`). **A newly trained model has therefore never refreshed the Prediction page's model list**, which is precisely what the docstring at :242-244 promises.
2. `base_stacker.py:198-205` — `BaseStacker.reload()` has no callers anywhere in `src/` (verified by grep; the only `.reload()` calls are `gui/__init__.py:382,393` on the container and the dead call above). `PipelineFormStack.reload()` (`__init__.py:267-304`) instead hand-dispatches a 7-branch `if/elif` on the stacker *class-name string*, where all seven branches do a subset of exactly what `BaseStacker.reload()` already does.
3. `zoom_requested` is declared as a `pyqtSignal` three times (`viewer_stacker.py:381,655,833`) and connected three times (`viewer_stacker.py:1445`, `comparison_stacker.py:521`, `correct_alignments_stacker.py:519`) but **is never emitted anywhere in the repo** — the comment at `viewer_stacker.py:323-328` explains wheel-zoom was deliberately removed, but the signal plumbing was left behind. It's also missing from `TimeAxisMixin`'s `TYPE_CHECKING` signal declarations (:204-206) while the docstring at :192 still claims subclasses must define it.
4. Dead placeholder-string comparisons: `training_stacker.py:133` (`== "Click to select a dataset"`), `:158` (`== "Click to select an alignment"`), `pllr_stacker.py:211` and `:400` (`!= / == "No datasets registered"`). `MultiColumnComboBox.set_data` (`src/voxkit/gui/components/column_dropdown.py:56-58`) stores the row's `id` in `UserRole` — for the empty case that `id` is `None`, and placeholders go through `setPlaceholderText`, never `UserRole`. None of these four comparisons can ever be true.
5. `training_stacker.py:223` — `train_model_logic(self, audio_path, textgrid_path, model_name, model)`: the `model` argument (passed as `mode` from :218) is never read; the body re-derives it at :227.

Also redundant: `has_status_label()` returning `True` is already the `BaseStacker` default (`base_stacker.py:175`), yet it is overridden to return `True` at `viewer_stacker.py:1231`, `comparison_stacker.py:186`, and `correct_alignments_stacker.py:328`.

**Why it's debt:** #1 is a user-visible broken feature masquerading as working code. #2 and #3 mean the "obvious" place to make a change is not the place that runs. #4 makes validation look more thorough than it is.
**Fix:** #1 → `self._parent_widget`, or better, have `TrainingStacker` emit a `models_changed` signal the container subscribes to. #2 → delete the `if/elif` chain, call `stacker_widget.reload()`. #3 → delete the signal and the three connections, or wire it to something. #4/#5 → delete.

#### PL-5. Dataset & alignment dropdown population is hand-written 12 times, including twice per file — `High` / `M`
**Where:** `datasets.list_datasets_metadata()` → build rows → `set_data(...)` / `setEnabled(...)` appears at:
`comparison_stacker.py:568-584`, `correct_alignments_stacker.py:623-639`, `pllr_stacker.py:253-267`, `prediction_stacker.py:72-92` **and** `:111-130`, `training_stacker.py:274-289` **and** `:318-335`, `transcription_stacker.py:70-86` **and** `:117-133`, `viewer_stacker.py:1528-1544`.
The `[{"id": None, "data": ("No datasets registered", "", "")}]` empty-state literal appears at 10 sites (`comparison:580`, `correct:635`, `prediction:88` and `:126`, `training:285` and `:331`, `transcription:82` and `:129`, `viewer:1540`, plus the string form at `pllr:266`).
`alignments.list_alignments()` → build rows → `set_data(...)` appears 5 times: `comparison_stacker.py:620-650`, `correct_alignments_stacker.py:684-711`, `pllr_stacker.py:213-248`, `training_stacker.py:84-114`, `viewer_stacker.py:1583-1610`.
The engine-settings dialog dance (`GenericDialog(...)` → `exec()` → check `QDialog.DialogCode.Accepted` → `save()` → `self.parent().setGraphicsEffect(None)`) is written 4 times: `transcription_stacker.py:50-65`, `prediction_stacker.py:51-62`, `training_stacker.py:60-77`, `pllr_stacker.py:191-201`.
**What:** In `prediction_stacker.py`, `transcription_stacker.py`, and `training_stacker.py` the *same file* contains the block twice — once inline in `build_ui()` and once in `reload_datasets()` — so the two copies must be kept in sync by hand. They are already inconsistent: `training_stacker.py:278` builds `(name, description, id)` under headers `["Name", "Description", "ID"]` while :322-326 builds `(name, registration_date, description)` under `["Name", "Date", "Description"]`. **The same dropdown shows different columns before and after a reload.**
**Why it's debt:** Adding a column (e.g. surfacing dataset size) is a 12-site edit. The `training` inconsistency is a shipped visual bug nobody noticed because the two code paths were never diffed.
**Fix:** Add to `BaseStacker` (or a `dropdowns.py` helper): `populate_dataset_dropdown(dd)` and `populate_alignment_dropdown(dd, dataset_id)`, and a `open_engine_settings(engine, tool)` helper. Then `build_ui()` calls the same helper `reload_datasets()` does — which is what `pllr_stacker.py:334` and `viewer_stacker.py:1507` already do correctly by calling `reload_datasets()` at the end of construction.

#### PL-6. 82 `print()` calls are the module's only diagnostics; `PLLRStacker` is 10% print statements — `Medium` / `M`
**Where:** `pllr_stacker.py` — 70 calls, densest at `:393-526` (`on_extract_pllr`, ~40 `[DEBUG]`/`[ERROR]`/`[INFO]` lines interleaved with logic) and `:533-672` (`extract_pllr_logic`, incl. `print(f"[DEBUG] Alignment data retrieved: {alignment_data}")` at :428 and `print(f"[DEBUG] Paths to validate: {paths}")` at :492). `training_stacker.py` — 8, at `:74` (inside `except Exception as e: print("Error syncing training settings:", e)` — a swallowed exception whose only trace is stdout), `:194`, `:206-210`, `:225` (`print("Training logic would be implemented here.")`, immediately above the code that actually does it). `prediction_stacker.py` — 4, at `:181-182`, `:197-198`.
**What:** No `logging` anywhere in the module. In a PyInstaller-frozen GUI build there is no console, so all 82 of these vanish — the diagnostics exist only in dev. Worse, `pllr_stacker.py:428` and `:492` print full dataset/alignment metadata and absolute filesystem paths to stdout; the repo runs `shredguard` in pre-commit specifically to keep patient IDs and phone numbers out of the tree (`pyproject.toml:191-198`), and these prints route participant-derived path components straight to the terminal.
**Why it's debt:** Debugging a frozen build has no data at all; the `pllr` prints make the two longest methods in the file unreadable and unmaintainable.
**Fix:** `logger = logging.getLogger(__name__)` per module; convert `[DEBUG]` → `logger.debug`, `[ERROR]` → `logger.exception`. Delete the ~40 narration prints in `on_extract_pllr` outright — they trace control flow that a single `logger.debug("extracting pllr", extra={...})` covers.

#### PL-7. God methods and god classes — `Medium` / `M`
**Where:** `viewer_stacker.py:1234-1507` `build_ui()` — **274 lines**; `correct_alignments_stacker.py:331-603` `build_ui()` — **273 lines**; `comparison_stacker.py:363-528` `_build_inspector_section()` — 166 lines; `viewer_stacker.py:453-617` `TextGridTimeline.paintEvent()` — 165 lines; `comparison_stacker.py:189-348` `build_ui()` — 160 lines; `pllr_stacker.py:528-673` `extract_pllr_logic()` — 146 lines; `pllr_stacker.py:391-526` `on_extract_pllr()` — 136 lines; `training_stacker.py:128-221` `on_train_model()` — 94 lines. Classes: `ComparisonStacker` 1184 lines / 47 methods, `CorrectAlignmentsStacker` 950 / 42, `ViewerStacker` 916 / 38, `PLLRStacker` 517 / 9, `SpectrogramPanel` 362 / 10.
**What:** The two 273-line `build_ui()`s are ~90% the same sequence of section-label / dropdown / audio-row / waveform / spectrogram / timeline / zoom-row construction (see PL-1). `on_train_model` interleaves six validation gates, two storage lookups, a name-collision check, five `print`s, and the worker launch in one flat function.
**Why it's debt:** Nothing at this size is unit-testable — the entire GUI folder is excluded from coverage (`pyproject.toml:139`), and only 1 of 8 stackers has any test at all (`tests/gui/test_prediction_stacker_validation.py`). Ruff's config selects only `E,F,I,S` (`pyproject.toml:88-93`), so no complexity rule catches these.
**Fix:** Split each `build_ui()` into `_build_selection_section()` / `_build_viewer_section()` / `_build_audio_controls()` (PL-1's extraction does most of this for free). Split `on_train_model` into a pure `_collect_training_inputs() -> TrainingInputs | None` (testable without Qt) plus a thin launcher — the shape `test_prediction_stacker_validation.py` already tests for.

#### PL-8. Three application-wide `QApplication` event filters that hijack Tab and are never removed — `Medium` / `S`
**Where:** `viewer_stacker.py:1485`, `comparison_stacker.py:330`, `correct_alignments_stacker.py:585` — all three do `QApplication.instance().installEventFilter(self)` inside `build_ui()`. Handlers at `viewer_stacker.py:1509`, `comparison_stacker.py:350`, `correct_alignments_stacker.py:605`. There is no `removeEventFilter`, `closeEvent`, or `deleteLater` anywhere in the module (verified by grep).
**What:** Every stacker install is global — the filter sees *every* key event in the whole application, on every page, forever. Each guards with `self.isVisible() and self._viewer_section.isVisible()` and returns `True` for Tab, meaning that whenever a viewer section is showing, Tab focus-navigation is dead application-wide, not just on that page. Three filters are chained, so every keystroke in the app runs three Python-level predicates.
**Why it's debt:** It silently breaks keyboard accessibility (Tab is the standard focus key), it's a per-keystroke cost on the whole app, and because filters are never uninstalled, a destroyed stacker leaves a dangling filter on the `QApplication`. Adding a fourth timeline stacker adds a fourth global filter.
**Fix:** Install the filter on the stacker widget itself, or use `QShortcut` with `Qt.ShortcutContext.WidgetWithChildrenShortcut` scoped to the viewer section (the "a plain QShortcut doesn't work" comment at `viewer_stacker.py:1479` is only true for the *default* application-context shortcut). At minimum, `removeEventFilter` in a `closeEvent`/`__del__`. Once PL-1 lands, this collapses to one site.

#### PL-9. Inline stylesheets and hardcoded colors bypass the style layer — `Medium` / `M`
**Where:**
- Exact duplicates of existing palette tokens: `pllr_stacker.py:512` `#f39c12` (= `Colors.WARNING`), `:687` `#27ae60` (= `Colors.SUCCESS`), `:692` `#e74c3c` (= `Colors.ERROR`); `comparison_stacker.py:235` and `:292` `color: #2c3e50` (= `Colors.TEXT_PRIMARY`); `comparison_stacker.py:253` `#d0d0d0` (= `Colors.GRAY`).
- Ad-hoc literals with no token at all: `comparison_stacker.py:89` `"QScrollArea { background: transparent; border: none; }"`; `comparison_stacker.py:252-256` a 4-line `QDoubleSpinBox` stylesheet incl. `selection-background-color: #cce5ff`.
- The same f-string repeated verbatim 12 times: `QLineEdit {{ border: 1px solid {Colors.BORDER}; … }} QLineEdit:focus {{ border-color: {Colors.PRIMARY}; }}` at `comparison_stacker.py:226-230` and `:398-402`, `viewer_stacker.py:1295-1299`, `correct_alignments_stacker.py:389-393` and `:542-547`; and `f"border: 1px solid {Colors.BORDER}; border-radius: 4px;"` at `comparison_stacker.py:463,477,485,492`, `correct_alignments_stacker.py:462,476,493`, `viewer_stacker.py:1382,1400,1414`.
- 28 raw hex literals in `viewer_stacker.py` paint code (`#f8f9fa` :459/:749/:1105 = `Colors.BG_SECONDARY`, `#2c3e50` :462 = `Colors.TEXT_PRIMARY`, `#e74c3c` :283/:288 = `Colors.ERROR`, `#3498db` :390/:772 = `Colors.PRIMARY`, `#27ae60` :391 = `Colors.SUCCESS`, `#7f8c8d` :758/:1108 = `Colors.TEXT_SECONDARY`, plus a 6-entry `_TIER_COLORS` fallback palette at :395-402).
**What:** `src/voxkit/gui/styles/__init__.py` defines `Colors`/`Buttons`/`Labels`/`Containers` as the intended single source of theming truth, and most of this module uses it — these are the leaks.
**Why it's debt:** A palette change (or any future dark-mode / high-contrast work for a clinical setting) silently misses ~45 sites, and `PLLRStacker`'s three status colors will visibly desync from the other seven stackers the moment `Colors.SUCCESS` changes.
**Fix:** Add `Labels.STATUS_*` usage to `PLLRStacker` (free once PL-2 lands). Add `Containers.PANEL_BORDER`, `Containers.SEARCH_FIELD`, `Containers.SPINBOX`, and a `Colors.TIER_PALETTE` to the styles module and point the 45 sites at them.

#### PL-10. 37% of functions have no return annotation (so mypy skips their bodies entirely) and 57% have no docstring — `Medium` / `M`
**Where:** Measured across the module: 261 functions, **97 without a return annotation**, **150 without a docstring**.

| file | funcs | no return annotation | no docstring |
|---|---|---|---|
| `base_stacker.py` | 13 | 9 | 0 |
| `viewer_stacker.py` | 85 | 24 | 58 |
| `correct_alignments_stacker.py` | 53 | 17 | 47 |
| `comparison_stacker.py` | 50 | 4 | 36 |
| `training_stacker.py` | 12 | 10 | 1 |
| `prediction_stacker.py` | 12 | 9 | 1 |
| `pllr_stacker.py` | 13 | 8 | 2 |
| `transcription_stacker.py` | 10 | 6 | 3 |
| `__init__.py` | 8 | 8 | 2 |

**What:** `pyproject.toml:128` sets `check_untyped_defs = false`. Under that setting mypy does not analyse the body of any function lacking annotations — so `invoke mypy-check` is effectively not looking at `TrainingStacker.on_train_model` (`:128`, no annotation, 94 lines), `PredictionStacker.on_predict_alignments` (`:151`), `PLLRStacker.on_extract_pllr` (`:391`), `extract_pllr_logic` (`:528`), `ViewerStacker.build_ui` (`:1234`), or `_load_viewer` (`:1709`). Untyped signals handlers are the norm: `def on_train_finished(self, success, message)` (`training_stacker.py:239`), `def on_predict_finished(self, success, message)` (`prediction_stacker.py:209`), `def on_transcribe_finished(self, success, message)` (`transcription_stacker.py:198`), `def on_extract_finished(self, success, message)` (`pllr_stacker.py:675`), `def _on_playback_state_changed(self, state)` (`viewer_stacker.py:1812`), `def _on_file_selected(self, item, _prev=None)` (`viewer_stacker.py:1674`). Docstring coverage is bimodal: `base_stacker.py` is 13/13, `markdown_stacker.py` 5/5, `transcription_stacker.py` 7/10 — while `viewer_stacker.py` is 27/85 and `correct_alignments_stacker.py` 6/53.
**Why it's debt:** Precisely the largest and most bug-prone functions are the ones mypy is blind to. PL-4 #1 (`self.parent` vs `self._parent_widget`) is exactly the class of bug a checked body catches.
**Fix:** Annotate the 97 signatures (mechanical — most are `-> None`), then flip `check_untyped_defs = true` and fix the fallout. Fix the file-by-file docstring gap with the project's own `python-docstring-enforcer` agent.

#### PL-11. Fragile construction-order and private-attribute coupling — `Low` / `S`
**Where:**
- `markdown_stacker.py:33-36` — reaches into the base class's layout by index to undo it: `last_item = self.main_layout.itemAt(self.main_layout.count() - 1)` then `removeItem` if it's a spacer. This depends on `BaseStacker.init_ui()` adding `addStretch()` *last* (`base_stacker.py:80`) — reordering two lines in the base class silently changes `MarkdownStacker`'s layout.
- `comparison_stacker.py:563` — `self._current_data_path` is first assigned inside `reload_datasets()`, and is never declared in `__init__` (:101-179) unlike its `ViewerStacker` counterpart (`viewer_stacker.py:1197`). It only exists because `build_ui()` happens to end with `self.reload_datasets()` (:348). Any early return added to `reload_datasets` makes `_populate_speakers` (:688) raise `AttributeError`.
- 39 reads of another widget's private attributes: `self._timeline._duration` / `._view_start` / `._view_end` / `._current_time` — 13 in `viewer_stacker.py` (`:1869,1896,1899,1907,1910,1911,1917,1918,1945,1946,1957,1961,1964`), 13 in `comparison_stacker.py` (`:1051,1054,1065,1066,1072,1073,1094,1095,1106,1110,1113,1173,1176`), 13 in `correct_alignments_stacker.py` (`:922,947,950,957,960,961,965,966,985,986,997,1001,1004`). `TimeAxisMixin` exposes no public `duration()`/`view()` accessors.
**Why it's debt:** Nothing warns when the base layout or `TimeAxisMixin`'s internals change; the failures are `AttributeError` or a silently wrong time axis at runtime.
**Fix:** Give `BaseStacker` an explicit `has_trailing_stretch()` hook instead of the layout surgery. Declare `_current_data_path` in `ComparisonStacker.__init__`. Add `duration`/`view_start`/`view_end` properties to `TimeAxisMixin` (PL-1's extraction removes 26 of the 39 sites anyway).

### Cross-module notes

- **`WorkerThread` throws away tracebacks** (`src/voxkit/gui/workers/worker_thread.py:33-34`): `except Exception as e: self.finished.emit(False, str(e))`. Every stacker's error dialog therefore shows only `str(e)` with no traceback and no logging — this is the mechanism behind the opaque `MFA alignment failed (exit 1)` symptom `AGENTS.md:96` documents. It also swallows the distinction between "engine failed" and "VoxKit bug". Emitting/logging `traceback.format_exc()` would improve every one of the eight stackers at once. Belongs to `gui/workers/`.
- **`PipelineFormStack` (`__init__.py:122-318`) is arguably not part of the stacker family** and is the shotgun-surgery hub: adding one stacker requires editing the import block (:99-107), `STACKER_REGISTRY` (:110-119), `__all__` (:321-333), the `reload()` if/elif chain (:272-304), the module docstring's "Available Stackers" section (:19-46), and three YAML files (`config/pipeline_definitions.yaml` + both `config/profiles/*/pipeline_definitions.yaml`) — 8 touchpoints. The `MarkdownStacker` special-case at :186-189 (`if step.stacker_class == "MarkdownStacker" and step.markdown_content`) hardcodes one stacker's constructor signature into the generic loader.
- **The module docstring is already stale**: `__init__.py:19-46` "Available Stackers" documents 6 stackers and omits `ViewerStacker` and `ComparisonStacker`, both of which are in `STACKER_REGISTRY` and both YAML profiles.
- **`pyproject.toml:112` has a per-file-ignore for `src/voxkit/gui/pages/pipeline/evaluation_stacker.py`, which does not exist.** Stale lint config referencing a deleted file.
- **`config/pipeline_definitions.yaml` and both profile copies ship "To be, or not to be…" Hamlet placeholder text** as the `collapsible_sections` help content for the Training, Prediction, and PLLR steps (`config/profiles/default/pipeline_definitions.yaml`, the `"Collapsible Section 1/2/3"` blocks). This is user-facing text in a clinical research tool. Belongs to `config/`.


---

## Module: `src/voxkit/gui/frameworks/`

**Health:** Two frameworks with opposite problems — the table is a one-caller "framework" hardcoded to its caller, the settings modal is genuinely reused but leaks its blur effect and carries ~150 lines of dead/unreachable machinery. | **Files:** 5 | **LOC:** 1436 | **Findings:** 20 (3 High / 13 Medium / 4 Low)

`categorical_table/` provides a paged table with category navigation and CRUD callbacks; `settings_modal/` provides a declarative field-config → Qt-widget dialog builder with JSON persistence. **`CategoricalTableWidget` has exactly one caller** (`ManageAlignersWidget`, `src/voxkit/gui/pages/models/models_page.py:29`) and hardcodes that caller's strings ("Model Management", "Models", "Browse Models") into the framework body, while the caller has to walk the framework's layout tree at runtime to inject a button it has no slot for. **`GenericDialog` has 7 production call sites and 9 `SettingsConfig` definitions** — that generality is earned — but the framework applies a `QGraphicsBlurEffect` to its grandparent and never removes it, so 5 call sites duplicate the same `parent().setGraphicsEffect(None)` cleanup line and 2 more set `apply_blur=False` with a workaround comment. Both files are also full of unreachable code that Python's truthiness and bound-method semantics quietly hide: a storage-root containment guard that can never fire, a dialog-centering block that never runs, a `_create_checkbox` factory nothing calls, and an overlay that is `deleteLater()`'d one line after `show()`.

### Findings

#### GF-1. `CategoricalTableWidget` is a "framework" with one caller, hardcoded to that caller — `High` / `M`
**Where:** `src/voxkit/gui/frameworks/categorical_table/categorical_table.py:91`, `:98`, `:151`; sole caller at `src/voxkit/gui/pages/models/models_page.py:29`
**What:** The generic widget hardcodes the models page's domain vocabulary in its own `init_ui`: `title = QLabel("Model Management")` (`:91`), `models_group = QGroupBox("Models")` (`:151`), `HuggingFaceButton(title="Browse Models")` (`:98`), plus the fixed button labels `"Import"` / `"Export Selected"` / `"Delete Selected"` (`:182-195`) and the literal `"Actions"` column (`:269`). Meanwhile the constructor advertises generality it does not have: a repo-wide grep for `CategoricalTableWidget` returns exactly one production instantiation — `class ManageAlignersWidget(CategoricalTableWidget)` — which passes neither `single_selection_flag` nor a custom title (there is no title parameter). The `huggingface_callback` hook (`:46`, `:96-100`) is wired to `on_huggingface_browse` (`models_page.py:147`), which is a `# TODO: Implement HuggingFace model browsing/import` stub that opens a "will be available soon!" `QMessageBox`.
**Why it's debt:** It is filed under `frameworks/` and documented in `gui/__init__.py:11` as a reusable "UI pattern framework", so the next developer with a categorised table will try to reuse it, discover it says "Model Management" at the top, and either fork it or add a second parameter for every hardcoded string. The `huggingface_callback` parameter is framework surface area that exists solely to reach a stub.
**Fix:** Either (a) accept that this is the models page's widget, move it to `gui/pages/models/`, and delete the unused parameters; or (b) commit to the framework and parameterise `title`, `group_title`, and the action-button labels via a small `TableConfig` dataclass mirroring `settings_modal.api.SettingsConfig`. Drop `huggingface_callback` until the HuggingFace browser actually exists.

#### GF-2. No extension point for extra actions, so the caller does runtime layout archaeology — `High` / `S`
**Where:** `src/voxkit/gui/pages/models/models_page.py:109-145` (`_add_register_button`), against `categorical_table.py:151-173`
**What:** The models page needs a "+ Register New Model" button inside the framework's group box. The framework offers no slot, so the caller searches for it by iterating `self.layout()`, then iterating each child widget's layout, comparing `item.widget() == self.table_widget` to identify which anonymous `QGroupBox` holds the table, then `models_group.layout().insertWidget(0, button_container)`. It also reaches in afterwards to re-tune the framework's own spacing: `self.layout().setSpacing(20)` / `setContentsMargins(0, 0, 0, 0)` (`models_page.py:81-82`), overriding the values `init_ui` just set at `categorical_table.py:85-86`.
**Why it's debt:** This is the clearest proof the abstraction is wrong. Any reordering or re-nesting inside `init_ui` silently breaks the button — `_add_register_button` fails by `return`ing early at `models_page.py:130`, so the button just disappears with no error. It is also untestable without a full widget tree.
**Fix:** Give `CategoricalTableWidget` a named, public insertion point — e.g. expose `self.table_container_layout` (already a local at `categorical_table.py:153`) as an attribute, or accept an `extra_actions: list[QWidget]` constructor argument — and delete the search loop.

#### GF-3. `GenericDialog` applies a blur effect it never removes; 7 call sites work around it — `High` / `S`
**Where:** `src/voxkit/gui/frameworks/settings_modal/generic.py:134-136` (applies), no corresponding removal anywhere in the class
**What:** `_setup_overlay` does `blur_effect = QGraphicsBlurEffect(); blur_effect.setBlurRadius(5); parent.parent().setGraphicsEffect(blur_effect)`. The class overrides no `closeEvent`, `reject`, `accept`, or `done`, so the effect outlives the dialog. Every caller has to undo it by hand, and they all wrote the same line independently:
- `src/voxkit/gui/pages/pipeline/training_stacker.py:77` — `self.parent().setGraphicsEffect(None)`
- `src/voxkit/gui/pages/pipeline/pllr_stacker.py:198` — same, with the comment `# Clean up blur applied by GenericDialog to self.parent()`
- `src/voxkit/gui/pages/pipeline/transcription_stacker.py:65` — same
- `src/voxkit/gui/pages/pipeline/prediction_stacker.py:62` — same
- `src/voxkit/gui/pages/models/models_page.py:182` — `self._parent_widget.setGraphicsEffect(None)`

Two more call sites opted out entirely rather than deal with it: `src/voxkit/gui/pages/datasets/datasets_page.py:667` — `apply_blur=False,  # Disable blur to avoid parent issues` — and `src/voxkit/gui/pages/models/models_page.py:190`.
**Why it's debt:** A caller that forgets the line leaves the whole application window permanently blurred. The framework asymmetrically owns "apply" but delegates "remove", and the note left at `datasets_page.py:667` shows a developer already hit and gave up on this.
**Fix:** Add `def closeEvent(self, event)` / override `done()` in `GenericDialog` to call `self._teardown_overlay()`, which clears the graphics effect it installed (store the target widget in `__init__`). Then delete all 5 caller cleanup lines and re-enable blur where it was disabled defensively.

#### GF-4. `_setup_overlay` is mostly a no-op, wrapped in a silent `except` — `Medium` / `S`
**Where:** `src/voxkit/gui/frameworks/settings_modal/generic.py:113-141`; `:83`
**What:** Three separate problems in 28 lines:
1. `overlay = OverlayWidget(main_window); overlay.resize(...); overlay.show()` (`:129-131`) is followed six lines later by `overlay.deleteLater()` (`:138`) — the overlay is queued for destruction the moment control returns to the event loop, i.e. before the dialog is ever shown. The "semi-transparent overlay on the main window" the docstring promises (`:116-118`) never appears. Only the blur (GF-3) survives.
2. `except (AttributeError, ImportError): pass` (`:139-141`) with the comment "Gracefully handle if overlay utils aren't available" — but the `try` block contains no import, so `ImportError` is unraisable, and the `AttributeError` catch silently absorbs any real bug in the parent-chain walk.
3. `self._apply_blur = config.apply_blur` (`:83`) is written and never read — grep across `src/` and `tests/` returns only the assignment itself.
**Why it's debt:** Dead visual machinery that reads as working. Anyone debugging "why is there no overlay?" has to reason about `deleteLater` semantics to discover the answer.
**Fix:** Decide whether the overlay is wanted. If yes, keep a reference on `self` and delete it in the teardown from GF-3. If no, delete lines `:129-131` and `:138`. Drop the `except` clause or narrow it to the specific call that can fail. Delete `self._apply_blur`.

#### GF-5. The storage-root containment guard can never fire, and doesn't check containment — `Medium` / `S`
**Where:** `src/voxkit/gui/frameworks/settings_modal/generic.py:77-79`, documented at `:49-50`
**What:**
```python
self.store_values_path = Path(get_storage_root() / Path(config.store_file))
if not self.store_values_path:
    raise ValueError("File path must be within the storage root directory.")
```
A `Path` is always truthy — even `Path("")` normalises to `PosixPath('.')`, which is truthy — so this branch is unreachable and the `Raises: ValueError: If store_file path is not within the storage root directory` in the class docstring (`:49-50`) documents behaviour that cannot occur. Worse, no containment check is performed at all: `Path("/root") / Path("/etc/passwd")` evaluates to `/etc/passwd`, so any absolute `store_file` silently escapes `~/.voxkit/`, and `save_json` (`src/voxkit/storage/utils.py:114`) will `mkdir(parents=True)` and write there.
**Why it's debt:** `store_file` is a plain `str` on `SettingsConfig` (`api.py:118`) set by 9 different config sites; the one guard that was meant to constrain it does nothing. Falsely reassuring dead validation is worse than none.
**Fix:** Replace with a real check: resolve the joined path and assert `get_storage_root().resolve() in resolved.parents`, raising `ValueError` otherwise. Add a unit test with an absolute `store_file`.

#### GF-6. The dialog-centering block is unreachable — dialogs are never centered — `Medium` / `S`
**Where:** `src/voxkit/gui/frameworks/settings_modal/generic.py:228-236`
**What:** `if self.parent is not None and hasattr(self.parent, "parent"):` — `self.parent` is `QWidget.parent`, a **bound method**, not the parent widget. It is never `None`, and `hasattr(<bound method>, "parent")` is `False`, so the condition is always false and the `self.move(...)` inside never executes. (The body would fail anyway: `main_window = self.parent.parent` then `main_window.x()` would call an attribute on a method object — which is why the `except AttributeError: pass` at `:235-236` was added.)
**Why it's debt:** Every settings dialog in the app opens wherever Qt happens to place it rather than centered on the main window, and the code reads as if this were handled. The `except AttributeError: pass` is the fossil of someone hitting the bug and suppressing the symptom.
**Fix:** Use the parent passed to `__init__` (or `self.parentWidget()`) and drop the `hasattr` probe entirely:
```python
main_window = self.parentWidget()
if main_window is not None:
    self.move(main_window.x() + (main_window.width() - self.width()) // 2, ...)
```

#### GF-7. ~90 lines of speculative and dead API in `settings_modal` — `Medium` / `M`
**Where:** `generic.py:393-408`, `:496`, `:507-534`, `:369-391`; `api.py:22`, `:74`, `:83`
**What:** Five verified-unused items, all reachable-looking:
- **`_create_checkbox()` (`generic.py:393-408`)** — never called. `FieldType.CHECKBOX` dispatches to `ToggleSwitch(checked=...)` at `:332`, not to this factory. `ToggleSwitch` is `class ToggleSwitch(QWidget)` (`src/voxkit/gui/components/toggle_switch.py:14`), not a `QCheckBox` subclass, so no `QCheckBox` instance is ever created by this framework.
- **Consequently the `elif isinstance(widget, QCheckBox)` branches at `generic.py:496` and `:525` are dead**, as is half the `isinstance(widget, (QCheckBox, ToggleSwitch))` tuple at `:167`.
- **`set_values()` (`generic.py:507-534`)** — 28 lines, zero callers in `src/` or `tests/`.
- **`FieldConfig.validator` (`api.py:83`)** — documented in the same file as "Optional callable for custom validation (not yet implemented)" (`api.py:49`). Never read by `generic.py`; no config site sets it. Every caller instead validates *after* the fact (e.g. `models_page.py:236-243`, `datasets_page.py:769-789` re-check emptiness with their own `QMessageBox.warning` calls).
- **`FieldType.DOUBLE_SPINBOX` + `decimals` + `_create_double_spinbox()` (`api.py:22`, `:74`; `generic.py:369-391`)** — no production caller. The only references outside the framework are the framework's own docstring example (`settings_modal/__init__.py:38`).
**Why it's debt:** Roughly a fifth of `generic.py` is machinery nothing exercises, and it is not obviously dead — `_create_checkbox` sits directly between two factories that *are* called, so a reader assumes CHECKBOX routes through it.
**Fix:** Delete `_create_checkbox`, `set_values`, the `QCheckBox` isinstance branches, and `FieldConfig.validator`. Keep `DOUBLE_SPINBOX` only if a float setting is imminent; otherwise delete it and `decimals` too — re-adding it is 20 lines.

#### GF-8. Three parallel `isinstance` → setter chains that must be kept in sync — `Medium` / `M`
**Where:** `generic.py:167-176` (`_load_saved_values`), `:494-503` (`get_values`), `:523-534` (`set_values`)
**What:** The same widget-type dispatch is written out three times with slightly different branch sets. `_load_saved_values` handles `(QCheckBox, ToggleSwitch)` as one tuple; `get_values` and `set_values` split them into two branches and put `ToggleSwitch` *last*, after `QCheckBox`; none of the three handles `DIRPATH` distinctly from `LINEEDIT` (fine today, fragile if `DIRPATH` ever grows a container widget). `_create_field_widget` (`:327-341`) is a fourth `if/elif` over `FieldType` for the same set of types.
**Why it's debt:** Adding a field type means editing four places. `_wrap_with_browse_button` (`:274-299`) already returns a *container* `QWidget` for DIRPATH, so `self.field_widgets[name]` and the widget actually in the form layout are different objects (`:265-266`) — a divergence held together only by the fact that all three chains read `field_widgets`, not the layout.
**Fix:** Introduce a per-`FieldType` adapter — a small dataclass or dict of `{create, read, write}` callables keyed by `FieldType` — and drive all four sites from it. Existing tests (`tests/gui/test_settings_modal_tooltips.py`) cover the tooltip path only, so add read/write round-trip tests per type first.

#### GF-9. JSON persistence has no schema and a too-narrow `except`; the constructor writes to disk — `Medium` / `M`
**Where:** `generic.py:89`, `:95-111` (`_save_defaults`), `:143-178` (`_load_saved_values`), `:536-550` (`save`)
**What:** `__init__` calls `self._save_defaults()` at `:89`, which writes a JSON file into `~/.voxkit/` as a side effect of *constructing a widget*. `_load_saved_values` then reads it back and pushes values straight into Qt setters with no validation, guarded by `except (FileNotFoundError, json.JSONDecodeError)` (`:177`) — which does **not** catch the `TypeError` that `QSpinBox.setValue(str)` or `QComboBox.findText(int)` raise. The stored JSON is the app's forward-compatibility contract: if a `FieldConfig` ever changes `field_type` (e.g. `SPINBOX` → `COMBOBOX`) between releases, every existing user's stale `~/.voxkit/**/settings.json` crashes the dialog on open with an unhandled `TypeError`. There is also no version/schema marker in the file. Separately, one-shot registration *forms* are persisted as if they were settings — `model_registration_settings.json` (`models_page.py:191`) and `dataset_registration_settings.json` (`datasets_page.py:666`) are written on every dialog open even though neither caller ever calls `save()`.
**Why it's debt:** This is a shipped desktop app with PyInstaller builds; a settings-schema change becomes a crash-on-upgrade with no migration path and no recovery UI.
**Fix:** Move `_save_defaults()` out of `__init__` into `save()`/an explicit call. Wrap each per-field restore in a type check against the `FieldConfig` (`isinstance(value, int)` for SPINBOX, etc.) and skip-with-log on mismatch instead of crashing. Add a `"_schema": <version>` key to the stored dict. Stop persisting the registration forms, or give them a distinct short-lived path.

#### GF-10. `print()` for all diagnostics, including every settings value, despite a configured logger — `Medium` / `S`
**Where:** `generic.py:111`, `:158`, `:164`, `:178`, `:550`
**What:** Five production `print()` calls: `print(f"Default settings saved to {self.store_values_path}")`, `print("Saved values json doesn't exist yet.")`, `print(f"Loading saved value for {name}: {value}")` — **inside the per-field loop, so it dumps every stored setting value on every dialog open** — `print("Error loading saved values.")` (which discards the exception object entirely), and `print(f"Settings saved to {self.store_values_path}")`. The project has a configured rotating file logger at `src/voxkit/config/logging_config.py` writing to `~/.voxkit/logs/voxkit.log`, used by 8 modules.
**Why it's debt:** In a windowed PyInstaller build stdout goes nowhere, so these are invisible exactly when a user reports a bug — and the one that matters (`:178`) throws away the exception. The value-dumping line is also a data-hygiene concern in a speech-pathology app that runs a `shredguard` pre-commit hook for patient IDs and phone numbers; settings values here include dataset paths (`dataset_path`, `hand_alignments_path` from `datasets_page.py:670-748`) that can carry participant identifiers.
**Fix:** `logger = logging.getLogger(__name__)`; convert the five calls to `logger.debug`/`logger.exception`; drop or redact the per-value line at `:164`. (`print` is repo-wide — 29 files — so this is worth a project-level ruff `T20` rule, see cross-module notes.)

#### GF-11. The CRUD callback contract is a stringly-typed three-state protocol documented as two — `Medium` / `S`
**Where:** `categorical_table.py:451-452`, `:504-505`, `:549-550`; contract documented at `:54-58`
**What:** The docstring specifies `export_function: Callable(category, items) -> (success: bool, message: str)`. The implementation adds an undocumented third state — an empty `message` means "do nothing, show no dialog":
```python
success, message = self.export_function(current_category, selected_items)
if not message:
    return
```
identically at `:504-505` (delete) and `:549-550` (import). The sole caller depends on this: `handle_import` returns `(False, "")` when the user cancels the directory picker (`src/voxkit/gui/pages/models/utils.py:39-40`), and `handle_export` returns `(False, "")` on the same cancel (`utils.py:88-89`), purely to suppress an "Import Failed" / "Export Failed" `QMessageBox`.
**Why it's debt:** The `bool` is misleading — `(False, "")` means "user cancelled", not "failed". A new caller reading the docstring will return `(True, "")` on success and get no confirmation dialog, or `(False, "no models found")` and get a scary error box for a benign case. Two of the three sites are also inconsistent about ordering: `on_export` (`:450-452`) checks `if not message` *before* branching on `success`, while `on_delete` (`:502-505`) does so after calling `delete_function` but before refreshing.
**Fix:** Replace the tuple with a small result type (`@dataclass class OpResult: status: Literal["ok","failed","cancelled"]; message: str = ""`) in a `categorical_table/api.py` mirroring `settings_modal/api.py`, and update the three handlers plus `models/utils.py`.

#### GF-12. Blocking storage I/O on the UI thread, in the constructor and on every tab switch — `Medium` / `M`
**Where:** `categorical_table.py:80-81` and `:200-216`; triggered by `models_page.py:96-107` (`showEvent`)
**What:** `CategoricalTableWidget.__init__` calls `self.refresh_data()` then `self.update_display()` synchronously (`:80-81`). `refresh_data` invokes the caller's `refresh_data_function`, which for the only caller is `refresh_models_function` (`models_page.py:41-52`) → `self.get_engines()` (a lazy `from voxkit.engines import engines` plus `has_tool` probes per engine) → `models.list_models(engine)` per engine, which does `models_root.iterdir()` and opens a `voxkit_model.json` for every subdirectory (`src/voxkit/storage/models.py:257-270`). `ManageAlignersWidget.showEvent` (`models_page.py:105-107`) repeats the whole scan every time the user switches to the Models tab. `reload_models` (`models_page.py:169-172`) calls `set_items` once per engine, and `set_items` calls `update_display()` (`categorical_table.py:432`) — so the entire table is torn down and rebuilt N times for N engines.
**Why it's debt:** Contradicts `AGENTS.md`'s stated pattern ("Async work runs in QThread workers"). With a large model store on a network volume the tab switch freezes the UI. It also means constructing the widget in a test performs real filesystem work.
**Fix:** Debounce `showEvent` (skip if data is fresh), and either move `list_models` into the existing worker pattern (`voxkit.gui.workers`) or batch `reload_models` so `update_display()` runs once. Remove `refresh_data()` from `__init__` and let the first `showEvent` populate.

#### GF-13. Auto-detected columns are cached permanently and leak across categories — `Medium` / `S`
**Where:** `categorical_table.py:260-266`
**What:**
```python
if not self.columns_shown:
    all_keys: set[str] = set()
    for item in category_data[:5]:      # only the first 5 items
        if isinstance(item, dict):
            all_keys.update(item.keys())
    self.columns_shown = sorted(list(all_keys))
```
`update_display` writes its detection result back onto the instance attribute, so it runs exactly once — for whichever category happens to be selected first — and every subsequent category renders with that category's column set. Items whose dicts lack those keys fall through to `item_data.get(column_name, "Unknown")` (`:279`) and display the literal string `"Unknown"`. The 5-item sample also means a key present only on item 6+ is dropped from the header.
**Why it's debt:** The whole point of a *categorical* table is that categories differ; auto-detection is the framework's advertised convenience (`:59` "Optional list of column names to display") and it is silently wrong for every category but the first. The one production caller passes `columns_shown` explicitly (`models_page.py:71`), which is why nobody has hit it — and also why it will stay broken until someone relies on it.
**Fix:** Compute columns into a local, not `self.columns_shown`, and recompute per category (or union the keys across all items in the category rather than sampling 5).

#### GF-15. Weak and missing type hints; `categorical_table.py` is entirely invisible to mypy — `Medium` / `M`
**Where:** `categorical_table.py:38-48` and every method in the file; `api.py:66`, `:70-71`, `:77`, `:83`; `generic.py:82`
**What:** `CategoricalTableWidget.__init__` takes four callables with no annotations at all (`refresh_data_function, export_function, import_function, delete_function, columns_shown=None, single_selection_flag=False, huggingface_callback=None, parent=None`), and no method in the 688-line file has a return annotation. Because `pyproject.toml` sets `check_untyped_defs = false` (`[tool.mypy]`), mypy **does not type-check the bodies of unannotated functions** — so the entire file is silently skipped by `invoke mypy-check`, including the `Unknown`-fallback and index-arithmetic logic. In `api.py`: `default_value: Any` (`:66`), `options: Optional[list]` (`:77`, unparameterised), `validator: Optional[Callable]` (`:83`, unparameterised), and `min_value: Optional[int]` / `max_value: Optional[int]` (`:70-71`) — annotated `int` while their own docstring says "Minimum value for spinbox types (int or float)" (`:44`) and `_create_double_spinbox` passes them to `QDoubleSpinBox.setMinimum(float)` (`generic.py:382`). `generic.py:82` declares `field_widgets: dict[str, Any]`, the untyped bag that the three isinstance chains in GF-8 exist to interrogate.
**Why it's debt:** The project runs mypy in pre-commit and via `invoke mypy-check`; this file gets none of that protection while appearing to be covered. The `Any`-typed widget dict is what forces runtime type dispatch instead of a static one.
**Fix:** Annotate `categorical_table.py`'s public signatures (`Callable[[], dict[str, list[dict[str, Any]]]]`, `Callable[[str, list[dict]], tuple[bool, str]]`, `-> None` on the handlers). Fix `min_value`/`max_value` to `Optional[float]` or split them per field type. Parameterise `options: Optional[list[str]]`. Consider flipping `check_untyped_defs = true` once the file is annotated.

#### GF-16. `FieldConfig` is a mutable dataclass used as shared module-level state — `Medium` / `S`
**Where:** `api.py:29-83` (not frozen); exploited at `src/voxkit/gui/pages/pipeline/pllr_stacker.py:98-105`
**What:** `FieldConfig` is a plain `@dataclass`, so instances are mutable. `pllr_stacker.py` defines `FIELDS: list[FieldConfig]` at module level (`:51`) and then does:
```python
fields = FIELDS.copy()          # shallow — same FieldConfig objects
for field in fields:
    if field.name == "likelihood_dct" and not field.default_value:
        field.default_value = str(get_storage_root() / ...)
```
`list.copy()` is shallow, so this mutates the shared module-level `FieldConfig` in place, permanently, for the lifetime of the process. The same pattern would corrupt the engine-level configs, which are also long-lived module/instance state (`mfa_engine.py:72-125`, `w2tg_engine.py:40-105`, `faster_whisper_engine.py:38-73`) and are handed to `GenericDialog` by reference at `training_stacker.py:62`, `prediction_stacker.py:55`, `transcription_stacker.py:58`.
**Why it's debt:** The framework hands callers mutable shared config objects with no copy-on-read and no immutability, and a caller has already written code that reads as "copy then modify" while actually modifying the original. It works today only because the mutation happens to be idempotent.
**Fix:** Make `FieldConfig` and `SettingsConfig` `@dataclass(frozen=True)`, forcing callers to use `dataclasses.replace()` — which would have turned the `pllr_stacker` bug into an immediate `FrozenInstanceError`. Alternatively have `GenericDialog.__init__` deep-copy the config it receives.

#### GF-17. The settings framework cannot be constructed without writing to the real `~/.voxkit/` — `Medium` / `S`
**Where:** `generic.py:77` + `:89`; demonstrated by `tests/gui/test_settings_modal_tooltips.py:17-29`
**What:** `store_values_path` is derived from the process-global `get_storage_root()` with no injection point, and `_save_defaults()` runs unconditionally in `__init__`. The only test of this framework, `test_settings_modal_tooltips.py`, therefore creates a real file at `~/.voxkit/test_tooltips_settings.json` every time `invoke run-tests` runs, and leaves it there. `tests/gui/conftest.py` has no storage-root isolation fixture (it only provides `AppConfig`/`PipelineConfig`/CSV fixtures).
**Why it's debt:** Tests mutate the developer's real application state, and any future test that exercises `save()`/`_load_saved_values()` will be order-dependent because it inherits whatever the previous test wrote. It also blocks testing the persistence logic — the highest-risk part of the framework (GF-9) — which is why it is currently untested.
**Fix:** Add a `storage_root` fixture in `tests/conftest.py` that monkeypatches `voxkit.storage.utils.STORAGE_ROOT` (or `get_storage_root`) to `tmp_path`, and use it in every GUI test that constructs a `GenericDialog`. Optionally let `SettingsConfig` accept an absolute-path override for tests.

#### GF-14. Dead code and unused public API in `categorical_table` — `Low` / `M`
**Where:** `categorical_table.py:218-225`, `:254-257`, `:396-401`, `:44-45`, `:578-688`
**What:** Verified-unused surface:
- **`set_data()` (`:218-225`)**, self-labelled `"legacy method for compatibility"` — no caller. (Every `.set_data(` hit in `src/` is `MultiColumnComboBox.set_data` or `timeline.set_data`, a different API.)
- **`single_selection_flag` (`:45`)** — never passed `True` by any caller; only the `__main__` demo passes it, as `False`. Its three consumers (`:144-146`, `:164-167`, `:398-399`) are therefore untested branches, and the guard `if self.single_selection_flag: return` inside `select_all` (`:398-399`) is doubly unreachable since the button is hidden at `:145`.
- **`if not category_data: ... pass` (`:254-257`)** — an empty conditional whose body is two comments and `pass`.
- **The 110-line `if __name__ == "__main__":` block (`:578-688`)**, containing a duplicate copy of the sample data schema and 6 `print()` calls, inside a library module that `voxkit/__init__.py` eagerly imports.
**Why it's debt:** ~140 of the file's 688 lines are unexecuted. The `__main__` block in particular is the framework's only "documentation" of intended use and it has already drifted from reality (it demonstrates `single_selection_flag`, which no real caller uses).
**Fix:** Delete `set_data`, the empty conditional, and the `__main__` block. Either delete `single_selection_flag` or add a test that exercises it.

#### GF-18. Modal-dialog construction is duplicated between the two frameworks — `Low` / `M`
**Where:** `categorical_table.py:326-382` (`show_detail_dialog`) vs `generic.py:180-254` (`_setup_ui` + `_create_header`)
**What:** `show_detail_dialog` hand-rolls a `QDialog` with a `QVBoxLayout`, a styled title `QLabel`, a `QScrollArea`, a `QFormLayout` of key/value label rows, and a bottom-right "Close" `QPushButton` wired to `dialog.close` — which is structurally the same dialog `GenericDialog._setup_ui` builds, minus the frameless chrome, the rounded `Containers.CONTAINER` styling, the fade-in, and the close-`✕` header. The two sit in sibling directories under `frameworks/` and share nothing.
**Why it's debt:** Detail dialogs and settings dialogs look different for no reason, and a styling change (e.g. `Containers.CONTAINER`) has to be applied twice. The duplication is small today but is exactly the kind that grows.
**Fix:** Either add a read-only mode to `GenericDialog` (all fields disabled, single Close button) and have `show_detail_dialog` build a `SettingsConfig` from the item's keys, or extract the shared frameless-container + header + fade-in scaffold into a small `frameworks/_dialog_base.py` both use.

#### GF-19. Missing module docstrings on `api.py` and `generic.py`, against project convention — `Low` / `S`
**Where:** `src/voxkit/gui/frameworks/settings_modal/api.py:1`, `src/voxkit/gui/frameworks/settings_modal/generic.py:1`
**What:** Both files begin directly with imports. Of every non-`__init__.py` module under `src/voxkit/`, only five lack a module docstring, and two of them are these. The sibling framework file `categorical_table/categorical_table.py:1-8` has the full `"""Title. / Description / API --- / - **Name**: ..."""` house style. The project ships pdoc docs via `invoke generate-documentation`, so these two render as untitled in the generated API reference.
**Why it's debt:** Inconsistent generated documentation for the two most-imported files in the module (`api.py` is imported by 3 engines and 4 pages).
**Fix:** Add the standard header block to both, matching `categorical_table/categorical_table.py:1-8`. Also add the missing method docstring on `categorical_table.py:83` (`init_ui`) — the only undocumented method in that file.

#### GF-20. Table row index is assumed to equal data index, in three places — `Low` / `S`
**Where:** `categorical_table.py:295`, `:314-324`, `:407-425`
**What:** The View button captures `idx=row_idx` at build time (`:295`) and `view_item_details` indexes `category_data[row_index]` (`:322-324`); `get_selected_items` does the same with `category_data[row]` from `selectionModel().selectedRows()` (`:421-423`). This holds only because `QTableWidget` sorting is never enabled. Separately, the "Actions" column position is recomputed as the magic expression `len(self.columns_shown)` at four independent sites (`:297`, `:311`, `:312`, and implicitly `:269`).
**Why it's debt:** Enabling `setSortingEnabled(True)` — a one-line, obviously-safe-looking UX improvement — would silently make Export and Delete operate on the *wrong models*, with no error. That is a destructive silent failure in a framework whose delete path is guarded only by a count-based confirmation ("delete 3 item(s)?", `:492`).
**Fix:** Store the item's identity on the row (`QTableWidgetItem.setData(Qt.ItemDataRole.UserRole, item_data)`) and resolve selections through that instead of positional indexing. Hoist the actions-column index into a single `actions_col = len(self.columns_shown)` local.

### Cross-module notes

- **Layering inversion: `engines/` imports from `gui/`.** `src/voxkit/engines/mfa_engine.py:30`, `w2tg_engine.py:27`, and `faster_whisper_engine.py:29` all `from voxkit.gui.frameworks.settings_modal import FieldConfig, FieldType, SettingsConfig`. The backend layer therefore depends on PyQt6-adjacent GUI code purely to describe its settings schema. `settings_modal/api.py` is pure data (dataclasses + an Enum, zero Qt imports) and would be a natural `voxkit/config/` or `voxkit/engines/` module. The visible cost: `src/voxkit/engines/base.py:271` declares `def get_settings_config(self, tool_type) -> Any:` with the docstring "Return the :class:`Any` for a tool type" — the type was erased to avoid the import, and the docstring was clearly written by find-and-replace over the erased name.
- **`ImportModelDialog` is unreachable production code.** `src/voxkit/gui/pages/models/import_dialog.py:24` defines a `GenericDialog` subclass whose only entry point is `ManageAlignersWidget.open_import_dialog` (`models_page.py:174`), which has no callers anywhere in `src/` or `tests/`. Its `main()` at `import_dialog.py:114-124` is also broken — it calls `ImportModelDialog(on_import=..., engines=[...])` with an `engines` kwarg the constructor does not accept (`:30-35`). Belongs to the models-page audit.
- **`print()` is repo-wide, not framework-specific.** 29 files under `src/voxkit/` use `print(`, versus 8 that use `logging.getLogger`. Worth a project-level decision: add `"T20"` (flake8-print) to `[tool.ruff.lint] select` in `pyproject.toml` and convert. Architecture-level, not this module's to fix.
- **`src/voxkit/gui/pages/models/utils.py` has its own dead demo scaffolding** — `handle_export_lambda` (`:141`) and `create_export_handler` (`:178`) both reference a `CategoricalListWidget` and an `export_requested` signal that no longer exist (the framework uses callbacks, not signals), and the file ends with a 40-line commented-out `__main__` block. Models-page audit.
- ~~`dist/` is committed to the repo~~ — **checked and false.** `dist/` and `build/` exist on disk from local builds but are untracked and correctly covered by `.gitignore:20-21`; `git ls-files dist build` returns nothing. They do pollute repo-wide greps run without `git ls-files`, which is what prompted this note.


---

## Module: `src/voxkit/gui/components/` + `gui/styles/` + `gui/utils.py`

**Health:** Functional but structurally half-finished — the "centralized style layer" is only half-adopted and one dialog leaks a live log subscriber on every close | **Files:** 16 | **LOC:** 2,667 | **Findings:** 14 (3 High / 7 Medium / 4 Low)

This module holds 12 reusable PyQt6 widget primitives, the 803-line global QSS constant bank (`styles/`), two path-validation helpers, and `VoxKitGUI` — the main window that wires pages into a `QStackedWidget`. The widgets themselves are mostly small and honest; the debt is concentrated in three places. First, `styles/` is presented as the single source of truth (`gui/__init__.py:20` — *"Styling is centralized in the styles module for consistency"*) but 27 of its 56 QSS constants never touch the `Colors` palette, four unrelated blue families coexist, and the app's *actual* global stylesheet lives as a 93-line string literal inside `gui/__init__.py` rather than in `styles/`. Second, several components skipped `styles/` entirely and hardcode colors into `paintEvent`. Third, `LogViewerDialog`'s disconnect hygiene is broken in a way that is empirically reproducible and unbounded.

Ruff here selects only `E,F,I,S`, and mypy runs with `check_untyped_defs = false` — so `print()`, blind `except Exception`, unused parameters, and the bodies of the 56 unannotated functions in this module are all invisible to CI. Findings below account for that.

### Findings

#### GC-1. `LogViewerDialog` leaks a permanently-subscribed dialog on every open/close — `High` / `S`
**Where:** `src/voxkit/gui/components/log_viewer_dialog.py:55`, `:61-62`, `:86-91`; consumer `src/voxkit/gui/__init__.py:505-512`
**What:** The dialog subscribes to the process-wide log handler in `__init__` (`self._handler.record_emitted.connect(self._append_line)`) and unsubscribes only in `closeEvent`. But the dialog's own "Close" button is wired to `self.accept` (`:55`), and `QDialog.accept()` does **not** deliver a close event — verified empirically against this repo's PyQt6:

```
PyQt6 accept() -> closeEvent fired? []
receivers before: 0
after open/close #1: receivers = 1
after open/close #2: receivers = 2
after open/close #3: receivers = 3
```

`VoxKitGUI._open_log_viewer` (`gui/__init__.py:507-509`) then constructs a *new* `LogViewerDialog(self)` whenever the previous one is not visible. The old dialog is parented to the main window, so Qt keeps it alive forever with its slot still attached.
**Why it's debt:** Every open/close cycle permanently adds one hidden `QPlainTextEdit` that receives, formats, and appends **every log record for the rest of the session**, plus a `_scroll_to_end()` layout pass per record per zombie. Memory and per-log-line cost grow linearly with how often the user peeks at the log — on a long alignment run that is a lot of records. The `except TypeError: pass` at `:89-90` also silently hides the case where the disconnect was already gone.
**Fix:** Connect the Close button to `self.close()` instead of `self.accept()`, and/or move the disconnect into `hideEvent`/`done()` — safest is to disconnect in an override of `done()` since it is the single funnel for `accept`/`reject`/`close`. Separately, reuse the existing dialog in `_open_log_viewer` rather than rebuilding it, and set `Qt.WA_DeleteOnClose` so hidden instances are not retained by the parent.

#### GC-2. `styles/` is a half-adopted design system: 27/56 constants bypass `Colors`, 4 rival blue palettes, 7 duplicate constant pairs, 6 dead constants — `High` / `L`
**Where:** `src/voxkit/gui/styles/__init__.py` throughout
**What:** Four separate problems in one file, all mechanically verified:

*(a) Palette bypass.* 27 of the 56 QSS constants are plain (non-f) strings that reference no `Colors` member, and 4 more are f-strings that still inline raw hex:
- `Buttons.BROWSE:93`, `BROWSE_ALTERNATE:112`, `DELETE_SMALL:270`, `TOGGLE:302`, `HUGGINGFACE:324`
- `Inputs.LINE_EDIT_SIMPLE:375`, `SPINBOX_WITH_ARROWS:398`, `CHECKBOX:431`, `COMBOBOX_SIMPLE:457`
- `Labels.HEADER_SIMPLE:486`, `SECTION_LABEL:577`, `PAGE_TITLE:581`, `STATS:585`, `CREDIT:594`, `INFO_SMALL:598`, `FILTER_LABEL:602`, `CONTENT_SECTION:606`
- `Containers.CONTAINER:623`, `GROUP_BOX:653`, `TABLE_WIDGET:677`, `HELPER_TEXT:704`, `EMPTY_STATE:716`, `COMBOBOX_STANDARD:726`, `COMBOBOX_FILTER:740`, `MARKDOWN_DISPLAY:785`
- f-strings that still hardcode: `Buttons.SUCCESS:171-174` (`#229954`/`#1e8449`), `DANGER:189-192`, `INFO_LARGE:229-232` (`#2980b9`/`#21618c` — these are literally `Colors.PRIMARY_HOVER`/`PRIMARY_PRESSED` retyped), `SUCCESS_SMALL:289` (`#d0d0d0` = `Colors.GRAY`)

`Labels.INFO_SMALL:598` hardcodes `#7f8c8d`, which *is* `Colors.TEXT_SECONDARY:31`. `Containers.GROUP_BOX:656` hardcodes `#3498db`, which *is* `Colors.PRIMARY:24`.

*(b) Four rival blue families.* `Colors.PRIMARY = #3498db` (Flat UI) vs `Containers.COMBOBOX_FILTER:751,754,774-775` (`#2196F3`/`#1565C0`/`#1976D2`/`#E3F2FD`, Material) vs `gui/__init__.py:103,136-137,155,159` (`#4a90e2`) vs `ToolBarStyle` at `gui/__init__.py:169-204` (`#2f3542`/`#3b4252`/`#4c566a`/`#2b6fa2`, Nord). `Buttons.TOGGLE:302` and `Buttons.HUGGINGFACE:324` add a fifth, Material grey/amber set.

*(c) Duplicate constant pairs.* Seven pairs express the same rule twice, once selector-scoped and once as a bare fragment: `Labels.TITLE:470`/`PAGE_TITLE:581`; `Labels.HEADER:478`/`HEADER_SIMPLE:486`; `Labels.INFO:497`/`INFO_SMALL:598`; `Labels.SECTION_HEADER:490`/`SECTION_LABEL:577`; `Inputs.LINE_EDIT:358`/`LINE_EDIT_SIMPLE:375`; `Inputs.SPINBOX:384`/`SPINBOX_WITH_ARROWS:398`; and four combobox styles spread across two classes — `Inputs.COMBOBOX:442`, `Inputs.COMBOBOX_SIMPLE:457`, `Containers.COMBOBOX_STANDARD:726`, `Containers.COMBOBOX_FILTER:740`.

*(d) Dead constants.* Six have zero references anywhere in `src/` or `tests/` (~82 lines of QSS): `Buttons.BROWSE_ALTERNATE:112`, `Inputs.DOUBLE_SPINBOX:417`, `Labels.SECTION_HEADER:490`, `Labels.CREDIT:594`, `Labels.FILTER_LABEL:602`, `Containers.COMBOBOX_FILTER:740`.

Also: `Colors` itself has four value collisions (`PRIMARY`==`INFO`==`#3498db`, `WHITE`==`BG_PRIMARY`, `LIGHT_GRAY`==`BG_HOVER`, `DARK_GRAY`==`BORDER`), and `DARK_GRAY = #e0e0e0` (`:44`) is *lighter* than `GRAY = #d0d0d0` (`:43`) — an actively misleading name.
**Why it's debt:** The stated purpose of the file — "All styles use f-strings referencing Colors for consistency" (`:15`) — is false for half of it. A theme change (or the accessibility/contrast pass this app will eventually need) requires editing ~90 hardcoded hex values scattered through QSS blobs rather than the palette. The bare-fragment constants also cascade to children when applied to a container, so they behave differently from their selector-scoped twins depending on where they land, with nothing in the name signalling that.
**Fix:** (1) Rewrite the 27 plain constants as f-strings over `Colors`, adding palette entries for the currently-unnamed values (`#333`, `#555`, `#b0b0b0`, the success/danger hover-pressed ramp) instead of inlining them. (2) Pick one blue and delete the other three families. (3) Collapse each duplicate pair into one selector-scoped constant. (4) Delete the six dead constants. (5) Rename `DARK_GRAY`, and collapse the four alias colors. (6) Move `Containers.COMBOBOX_*` into `Inputs` — a combobox is not a container.

#### GC-3. The app's real global stylesheet lives in `gui/__init__.py`, not in `styles/` — and its blanket `QWidget { border: none; }` forces every widget to re-declare borders — `High` / `M`
**Where:** `src/voxkit/gui/__init__.py:73-165` (`GlobalStyleSheet`), `:167-206` (`ToolBarStyle`), `:314-337` (inline `active_style`/`inactive_style`), `:466-475` (inline log-button QSS)
**What:** 93 lines of `GlobalStyleSheet` + 40 lines of `ToolBarStyle` + 24 lines of inline tab styles sit as module-level string literals in the GUI package root, containing **34 raw hex values** — more than any other file in the repo outside `styles/__init__.py` itself. The module docstring at `:20` claims "Styling is centralized in the styles module for consistency" 53 lines before `GlobalStyleSheet` is defined. Worse, `:77-82` applies

```
QWidget {
    background-color: #f5f5f5;
    color: #333;
    font-size: 13px;
    border: none;
}
```

which in Qt cascades to *every* `QWidget` subclass in the app — `QGroupBox`, `QTableWidget`, `QComboBox`, `QFrame`, everything.
**Why it's debt:** The blanket `border: none` plus a global background is why `styles/` carries so many constants whose whole job is to put the border back (`Containers.CONTAINER:623`, `GROUP_BOX:653`, `TABLE_WIDGET:677`, `SCROLL_AREA:669`, `Inputs.LINE_EDIT:358`, `COMBOBOX_STANDARD:726`, …) and why there are 38 inline `setStyleSheet` literals scattered across the pages. It is the structural cause of the styling sprawl the rest of this report describes. Additionally, `update_active_tab_style:311-365` writes inline stylesheets *onto* toolbar buttons that `ToolBarStyle` already styles, so two style systems fight over the same three widgets — and the method is a 3-branch `if/elif` with 9 near-identical `setStyleSheet` calls that must be edited in triplicate whenever a fourth tab is added.
**Fix:** Move `GlobalStyleSheet` and `ToolBarStyle` into `styles/` as `Global.APP` / `Global.TOOLBAR`, expressed over `Colors`. Replace the `QWidget` universal selector with targeted rules (`QMainWindow`, `QWidget#centralWidget`) so components stop having to undo it. Replace `update_active_tab_style` with a loop over `{"datasets": self.datasets_action, ...}` applying `Global.TAB_ACTIVE`/`TAB_INACTIVE`.

#### GC-4. `ModelSelectionPanel` duplicates its own model-load block, reaches into `storage`, and hardcodes the caller's step numbering — `Medium` / `M`
**Where:** `src/voxkit/gui/components/model_selection_panel.py:112-133` vs `:203-225`; `:15`; `:41-42`; `:13`
**What:** Four problems in one 236-line "reusable" component:
- **Duplication.** `_init_ui` lines 112-133 and `reload_models` lines 203-225 are the same 22-line block character-for-character apart from `dropdown.clear()`: same `models.list_models(engine_id)`, same `isinstance(m, dict)` / `raise ValueError("Model list item is not a dict")`, same `["Name", "Download Date", "ID"]` header list, same empty-state row.
- **Storage coupling.** `:15` imports `from voxkit.storage import models` and calls `models.list_models()` directly inside a widget constructor. A widget primitive cannot be constructed or tested without a populated `~/.voxkit` store — which is why it has no test file.
- **False configurability.** Both production callers use bare defaults: `training_stacker.py:306` and `prediction_stacker.py:99` are both exactly `ModelSelectionPanel(engines_dict)`. The `title`, `info_text`, and `placeholder` parameters have never been passed by anyone.
- **Caller-order coupling via those defaults.** `info_text` defaults to `"① Choose an alignment method"` and `placeholder` to `"➁ Click to select a model"` (`:41-42`), so the panel owns steps ① and ➁ — and both callers then add `"③ Choose a Training Dataset"` (`training_stacker.py:310`) / `"③ Choose a Speech Dataset"` (`prediction_stacker.py:104`). The numbering only works because both callers happen to place the panel first. The training page also displays "Choose an **alignment** method" while training a model. (The glyphs are three different Unicode families too: `①` U+2460, `➁` U+2782, `③` U+2462.)
**Why it's debt:** The panel is not reusable in the way its docstring claims ("Reusable panel…"); it is two pages' shared copy-paste with a constructor. Adding a third caller in a different position silently produces wrong step numbers, and any change to the model-row schema has to be made in two identical places 90 lines apart.
**Fix:** Extract the duplicated block into `_populate_dropdown(engine_id, dropdown)` and call it from both sites. Inject the model list (`model_provider: Callable[[str], list[dict]] = models.list_models`) instead of importing storage. Delete the numeral prefixes from the defaults and let callers supply their own step labels, or make the step index an explicit constructor argument.

#### GC-5. Debug `print()` and a full config dump on every launch — `Medium` / `S`
**Where:** `src/voxkit/gui/components/csv_viewer_dialog.py:133,135,142`; `src/voxkit/gui/__init__.py:233-237`
**What:** `CSVViewerDialog.closeEvent` opens with `print("Dialog closed, removing blur effect from parent")` and prints `"Removing blur effect from parent"` in two more places. `VoxKitGUI.__init__` has a block literally commented `# DEBUG` that `rprint`s the entire `AppConfig` and `PipelineConfig` objects to stdout on every startup. Neither is caught by lint — ruff selects `E,F,I,S`, not `T20`.
**Why it's debt:** In a PyInstaller-frozen desktop build stdout usually goes nowhere, so these are pure noise that pollutes dev output and — for the config dump — prints potentially machine-specific paths on every run. The project already has a `logging` setup (`voxkit.config.logging_config`) and the log viewer from GC-1 to surface it properly.
**Fix:** Delete the three `print()` calls. Convert the config dump to `logger.debug("app config: %s", ...)` (the file already has `logger` at `:47`) or remove it. Optionally add `T20` to `[tool.ruff.lint] select` so this cannot recur.

#### GC-6. Painted widgets hardcode colors and sizes, bypassing `styles/` entirely — `Medium` / `S`
**Where:** `src/voxkit/gui/components/grip_splitter.py:24,26,30,32,43,45,51,52`; `toggle_switch.py:31,70`; `dna_strand.py:21,38,43,44`; `overlay_effects.py:21`; `loading_dialog.py:31,206,213`
**What:** Every widget that paints itself with `QPainter` sidesteps the style layer:
- `grip_splitter.py` hardcodes six hex colors in `paintEvent` — `#ecf0f1`, `#d5dbdb`, `#bdc3c7`, `#3498db` (twice), `#95a5a6`. `#3498db` **is** `Colors.PRIMARY`; `#95a5a6` **is** `Colors.TEXT_TERTIARY`. Plus magic geometry: `dot_radius = 2`, `dot_spacing = 8`, `range(-2, 3)`.
- `toggle_switch.py:70` hardcodes `#4cd964` / `#d0d0d0` (the latter is `Colors.GRAY`), and `:31` hardcodes `setFixedSize(40, 22)`.
- `dna_strand.py:43-44` uses `QColor(100, 149, 237, 120)` and `QColor(150, 150, 150, 60)` — RGBA tuples with no name at all — plus `setMinimumWidth(100)` and `int(width / 8)`.
- `overlay_effects.py:21` uses `QColor(0, 0, 0, 120)`.
- `loading_dialog.py:206` hardcodes `#dbeef9` inside the card gradient (the only hex in an otherwise `Colors`-driven file), `:213` hardcodes `setFixedSize(420, 260)`.

`loading_dialog.py` is the counter-example that proves the pattern is achievable — it does use `Colors.PRIMARY`/`TEXT_PRIMARY`/`TEXT_SECONDARY`/`WHITE`.
**Why it's debt:** These are exactly the widgets a theme change cannot reach, because QSS does not apply to custom `paintEvent` painting. Anyone retheming the app will fix `styles/` and then discover the splitter grip and toggle switch are still the old colors.
**Fix:** Add a `Colors.TOGGLE_ON`, `Colors.SPLITTER_*`, `Colors.OVERLAY_SCRIM`, `Colors.WAVEFORM` set to `styles/`, and have these `paintEvent`s read `QColor(Colors.X)` (as `loading_dialog.py:53` already does). Promote the magic sizes to named module constants.

#### GC-7. The waveform renderer is implemented twice — `Medium` / `S`
**Where:** `src/voxkit/gui/components/dna_strand.py:29-77` vs `src/voxkit/gui/components/loading_dialog.py:20-73`
**What:** `_WaveformStrip.paintEvent` is a copy of `DNAStrandWidget.paintEvent` with a scrolling `self._phase` added. The comment at `loading_dialog.py:160` says so outright (`# Animated waveform (copied from the toolbar's decorative strip)`), and `:21` repeats it in the class docstring. The shared math is identical line-for-line: `num_bars = max(40, int(width / 8))`, `bar_spacing = width / num_bars`, `max_amplitude = height * 0.4`, the three sine phases `4π/7π+0.5/11π+1.2`, the `0.5/0.3/0.2` weights, `0.8 + 0.4 * math.sin(i * 0.7)`, and `QPen(color, max(1.5, bar_spacing * 0.6))` with `RoundCap`.
**Why it's debt:** Two divergent copies of a nontrivial visual signature already differ — `dna_strand.py:43` paints `QColor(100, 149, 237, 120)` (cornflower blue) while `loading_dialog.py:53-54` paints `Colors.PRIMARY` at alpha 200. The toolbar strip and the splash strip are supposed to be the same brand mark and are not. Any tuning of the envelope has to be replicated by hand.
**Fix:** Extract one `WaveformPainter`/`_paint_waveform(painter, rect, phase=0.0)` helper (or make `DNAStrandWidget` accept an optional phase and have `_WaveformStrip` subclass it) and have both widgets call it with a shared `Colors.WAVEFORM`.

#### GC-8. `AnimatedStackedWidget` drops animations, lies about `currentIndex()`, and carries a dead attribute — `Medium` / `M`
**Where:** `src/voxkit/gui/components/animate_stack.py:15,44-69`
**What:**
- `self._current_index = 0` (`:15`) is assigned and never read — grep across all of `src/` and `tests/` returns exactly this one line. Dead.
- `self._animation = (old_animation, new_animation)` (`:69`) is a single slot. A second `slideToIndex` during the 350 ms window replaces the tuple, dropping the only Python reference to the in-flight pair; the comment on `:68` (`# Store reference to prevent garbage collection`) is exactly the protection being defeated. The animations are also never `stop()`ed, so two overlapping transitions fight over the same widget geometry.
- `setCurrentIndex(index)` runs only in `on_animation_finished` (`:58`), so for 350 ms `self.currentIndex()` still returns the *old* index. The caller `pages/pipeline/__init__.py:309` calls `slideToIndex` from `menu_list.currentRowChanged`, and `gui/__init__.py:371,395` read back `pipeline_container.get_current_page_index()` on tab switch — a fast switch reads a stale index.
- `on_animation_finished` (`:57`) is never disconnected and closes over `old_widget`/`new_widget`, keeping both alive until the animation object dies.
**Why it's debt:** Rapid menu clicking (or an automated tab switch during a transition) produces mis-positioned pages and a wrong remembered page index. Because the widget is animation-timed, this reproduces only under fast interaction and is painful to diagnose later.
**Fix:** Delete `_current_index`. Guard re-entry: if `self._animation` is live, `stop()` both members and snap to the final geometry before starting the new pair. Call `setCurrentIndex(index)` up front (or track a `_target_index` that `get_current_page_index` consults) so the index is never stale.

#### GC-9. 56 of 69 functions in this module are unannotated, and mypy is configured not to check unannotated bodies — `Medium` / `L`
**Where:** all 12 component files, `gui/utils.py:16,21`, `gui/__init__.py:210-503`; config at `pyproject.toml` `[tool.mypy] check_untyped_defs = false`
**What:** An AST count over the scope: **56 of 69** function definitions lack full parameter + return annotations. Entire files are annotation-free — `animate_stack.py` (3/3), `column_dropdown.py` (3/3), `grip_splitter.py` (3/3), `overlay_effects.py` (2/2), `dna_strand.py` (2/2), `toggle_switch.py` (7/7), `huggingface_button.py` (2/2), `csv_viewer_dialog.py` (5/5), `gui/utils.py` (2/2), `gui/__init__.py` (11/11). Because `check_untyped_defs = false`, mypy does not analyze the *bodies* of these functions either — so `invoke mypy-check` is effectively a no-op across ~80% of this module.
**Why it's debt:** The GUI layer is also excluded from coverage (`pyproject.toml [tool.coverage.run] omit` lists `gui/components/**`, `gui/styles/**`, `gui/__init__.py`, `gui/utils.py`), so these files have neither type checking nor coverage enforcement — the two safety nets the project does have are both switched off here simultaneously. Signature drift like `set_data(rows, headers=None, placeholder=None)` (`column_dropdown.py:33`, no types, `rows` is an undeclared `list[dict]` with required `"id"`/`"data"` keys) is caught only at runtime, in a dropdown, in front of a user.
**Fix:** Annotate incrementally, starting with the public APIs actually crossing module boundaries — `MultiColumnComboBox.set_data`/`current_id`, `AnimatedStackedWidget.slideToIndex`, `ToggleSwitch.isChecked`/`setChecked`, `validate_path`/`validate_paths` — then flip `check_untyped_defs = true` once the noise is manageable. A `TypedDict` for the `{"id": ..., "data": (...)}` row shape would document the contract that `model_selection_panel.py:119` and eight page call sites all construct by hand.

#### GC-10. `CSVViewerDialog`: blur effect can outlive the dialog, `except Exception` swallows real errors, and an undocumented flag changes which attributes exist — `Medium` / `M`
**Where:** `src/voxkit/gui/components/csv_viewer_dialog.py:31,40-45,62-74,83,128-129,131-144`
**What:**
- **Effect leak.** `__init__:41-43` installs a `QGraphicsBlurEffect` on the *parent* widget. It is removed in `closeEvent:136` and `reject:143` — but not in `accept()`, nor if the dialog is destroyed without either. As established in GC-1, `QDialog.accept()` does not fire `closeEvent`. Today the only button calls `reject` (`:80`), so this is latent rather than active; adding any OK/Save path leaves the entire main window permanently blurred.
- **Swallowed failure.** `:128-129` catches bare `except Exception as e` around the whole CSV read and writes the message into a label. Encoding errors, permission errors, and genuine bugs all become an emoji in a `QLabel` with nothing in the log — `voxkit.config.logging_config` exists and is not used here.
- **Attribute existence depends on a flag.** `self.table` and `self.stats_label` are created **only** when `visualization` is falsy (`:62-74`). When a visualization is supplied, `self.stats_label` does not exist, so any future code path touching it raises `AttributeError`. `_load_csv:86` writes to it and is correctly guarded by `:47`, but nothing enforces that.
- **Undocumented parameter.** The class docstring (`:23-29`) documents only `csv_path` and `parent`; `visualization` (`:31`) is undocumented — yet it is the parameter the sole production caller always passes (`pages/datasets/datasets_page.py:968`: `CSVViewerDialog(csv_path, parent=self.parent_window, visualization=visualization)`). The table-rendering path that the docstring describes as the dialog's purpose is the *fallback*, exercised in production only when the analyzer visualization fails.
**Why it's debt:** A "CSV viewer" whose primary mode is "render an arbitrary widget someone handed me" is misnamed and mis-documented, and the two modes share a class with divergent attribute sets. The silent exception handler means a corrupt analysis CSV shows a user-facing ❌ with no diagnostic trail.
**Fix:** Always construct `stats_label` (hide it in visualization mode) so attribute existence is unconditional. Move the blur install/remove into a single `done()` override. Narrow the catch to `(OSError, UnicodeDecodeError, csv.Error)` and add `logger.exception(...)`. Document `visualization`, or split into `CSVTableDialog` + a generic `AnalysisDialog(widget)`.

#### GC-11. Dead `__main__` demo blocks inside library modules — `Low` / `S`
**Where:** `src/voxkit/gui/components/column_dropdown.py:84-105`, `src/voxkit/gui/components/huggingface_button.py:40-66`
**What:** Both files end with a standalone demo app. `column_dropdown.py` imports `sys` (`:3`) and `QApplication`, `QVBoxLayout`, `QWidget` (`:7`) at module scope *solely* for that block — real import cost on every `voxkit.gui.components` import, which `voxkit/__init__.py` triggers eagerly. `huggingface_button.py:54,59` contains `lambda: print(...)` handlers, and `:44` re-imports `QWidget` which is already imported at `:4`. Neither block has been exercised since these files were written; the corresponding `if __name__ == "__main__":` line is in `pyproject.toml`'s `exclude_lines`, so coverage does not report them as uncovered.
**Why it's debt:** 48 lines of unmaintained code inside shipped library modules, plus module-scope imports that exist only for it. Fake sample data (`"Alice", 30, "New York"`) sitting in a production package.
**Fix:** Delete both blocks and the imports that become unused (`sys`, `QApplication`, `QVBoxLayout`, `QWidget` in `column_dropdown.py`; the nested import in `huggingface_button.py`). If the demos are wanted, move them to `examples/` — already in ruff's exclude list.

#### GC-12. `ToggleSwitch` is not a `QAbstractButton`, so every consumer needs a parallel branch and nothing can react to a toggle — `Low` / `M`
**Where:** `src/voxkit/gui/components/toggle_switch.py:14,47-63`; consumers `src/voxkit/gui/frameworks/settings_modal/generic.py:167,326,332,502,533`
**What:** `ToggleSwitch(QWidget)` reimplements checkbox semantics by hand but emits **no signal** — `mousePressEvent:47-55` flips `self._checked` and animates, and that is all. It is the only component in the module besides `QObjectLogHandler` with any state and the only one with no `pyqtSignal` (grep for `pyqtSignal` across `components/` returns two hits, both in `log_handler.py`). Consequences visible in the settings modal:
- `generic.py:326` types the widget union as `Union[QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, ToggleSwitch]` — `ToggleSwitch` cannot ride along with `QCheckBox` because it shares no base class.
- Three separate `isinstance` ladders (`:167`, `:502`, `:533`) each need a dedicated `elif isinstance(widget, ToggleSwitch)` branch immediately after their `QCheckBox` branch, doing the identical thing (`.isChecked()` / `.setChecked(value)`).
- Values can only be *polled* at save time (`:502`), never observed — no live validation, no dependent-field enabling.

Separately, `setChecked:60-63` sets `_thumb_pos` directly without calling `self._animation.stop()`. If it is invoked while `mousePressEvent`'s 150 ms animation is running, the animation continues writing `thumb_pos` and overwrites the programmatic position, leaving the thumb visually contradicting `_checked`. There is no keyboard handling and no focus policy, so the control is unreachable without a mouse.
**Why it's debt:** Every new consumer must remember the extra `isinstance` arm; forgetting one silently drops the field from saved settings. The polling-only design blocks any reactive settings UI.
**Fix:** Subclass `QAbstractButton` (which supplies `toggled`, `clicked`, `setChecked`, keyboard/space activation, and makes the existing `isinstance(widget, QCheckBox)` branches unnecessary if `QCheckBox` is used as the base), keeping only `paintEvent` and the thumb animation. At minimum: add `toggled = pyqtSignal(bool)`, emit it from `mousePressEvent` and `setChecked`, call `self._animation.stop()` in `setChecked`, and set a focus policy.

#### GC-13. `VoxKitGUI` no-ops, magic stack indices, and unguarded lazily-created attributes — `Low` / `M`
**Where:** `src/voxkit/gui/__init__.py:266,292-296,372-373,383-386,396-398,456-482,496,505-512`
**What:**
- **Two documented no-ops.** `:266` `widget.setCursor(widget.cursor())` with the comment "ensure widget exists; can set more props here" — sets the cursor to itself. `:293-295` `spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())` — sets the policy to itself; the comment claims it "push[es] the DNA widget to fill remaining space", but the default `Preferred` policy pushes nothing (the DNA widget's own `Expanding` policy at `dna_strand.py:25` is what actually does it).
- **Magic stack indices.** `setCurrentIndex(1)` / `(0)` / `(2)` at `:373`, `:384`, `:448`, `:398` each carry a comment naming the page. They are positionally coupled to the `addWidget` order at `:437`, `:441`, `:445`. Reordering those three lines silently breaks navigation with no error.
- **Law of Demeter.** The main window reaches two levels into a child page's internals: `self.pipeline_container.menu_list.setVisible(False)` at `:372`, `:396` and `.setVisible(True)` at `:383`. `menu_list` is a private `QListWidget` created at `pages/pipeline/__init__.py:161`.
- **Unguarded lazy attributes.** `_init_log_status_entry:456` returns early at `:459-460` if `centralWidget()` is `None`, leaving `self._log_button` and `self._log_viewer` undefined. `_reposition_log_button:486` guards with `hasattr`, but `_open_log_viewer:507` reads `self._log_viewer` unguarded — an `AttributeError` on that path.
- **Per-event import.** `eventFilter:496` executes `from PyQt6.QtCore import QEvent` on *every* event delivered to the central widget (resize, paint, mouse), taking the import lock each time. Same pattern at `dna_strand.py:23` and `loading_dialog.py:217`.
**Why it's debt:** Individually small, collectively the file is fragile to reorder and hostile to reading — the no-ops actively mislead about intent, and the magic indices are the kind of coupling that survives until someone adds a fourth page.
**Fix:** Delete the two no-op lines. Replace the indices with named constants or `self.content_stack.setCurrentWidget(self.datasets_page)`. Give `PipelineFormStack` a `set_menu_visible(bool)` method instead of exposing `menu_list`. Initialize `self._log_viewer = None` in `__init__` before the early return. Hoist `QEvent` to module scope.

#### GC-14. Sibling inconsistencies: an unused parameter, three docstring dialects, mixed typing styles, a macOS-only font, a duplicated line, and a typo — `Low` / `S`
**Where:** listed below
**What:** Small deviations that make the twelve components read as twelve different authors:
- **Unused parameter shipped in the public API.** `gui/utils.py:16` `def validate_path(parent, path): return Path(path).exists()` — `parent` is never used. Both callers pass `self` (`pages/pipeline/training_stacker.py:125`, `pllr_stacker.py:388`) and `validate_paths:25` passes it through. Ruff's `ARG` rules are not selected, so nothing flags it. The test at `tests/gui/test_utils.py:8` documents the confusion by passing `None`.
- **Duplicated line.** `overlay_effects.py:16-17` calls `self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)` twice, identically.
- **Three docstring dialects.** Google-style `Args:`/`Returns:` (`model_selection_panel.py:31-35`, `loading_dialog.py:84-88`), reST `:param:` (`column_dropdown.py:34-42`), and Sphinx `:class:` cross-refs (`log_viewer_dialog.py:1-4`, `log_handler.py:1-2`) — in sibling files. `MultiColumnComboBox` (`column_dropdown.py:10`) has no class docstring at all, and `paintEvent` is undocumented in `dna_strand.py:29`, `overlay_effects.py:19`, `toggle_switch.py:65` but documented in `grip_splitter.py:19`.
- **Mixed typing styles.** `Optional[Path]` (`log_viewer_dialog.py:31`, `gui/__init__.py:212-213,479`) alongside `str | None` (`model_selection_panel.py:48,180,188`) and `QObjectLogHandler | None` (`log_handler.py:33`) — same codebase, `requires-python >=3.11`.
- **macOS-only font.** `log_viewer_dialog.py:46` `QFont("Menlo")` — Menlo does not exist on Windows or Linux. `:47` sets `StyleHint.Monospace` so it degrades rather than breaks, but the app ships Windows and Linux builds (`invoke windows-build`/`linux-build`) and this is the one hardcoded font family in the module. It also belongs in `styles/`, which defines no font families at all.
- **Docstring typo.** `components/__init__.py:1` — "taiored" (tailored). The same docstring at `:22` claims "Most components follow PyQt6 signal/slot patterns", but only one of the twelve (`QObjectLogHandler`) defines a signal.
- **Test coverage gap.** 7 of the 12 components have no test file: `dna_strand`, `grip_splitter`, `huggingface_button`, `log_handler`, `log_viewer_dialog`, `model_selection_panel`, `overlay_effects`. `model_selection_panel` and `log_viewer_dialog` are the two with real logic (GC-1, GC-4) and are the two hardest to test because of the coupling described there.
**Why it's debt:** No single item bites, but together they mean there is no house style for a new component to copy — the next widget will pick whichever neighbour it happens to open.
**Fix:** Drop the unused `parent` parameter (3 call sites). Delete the duplicated `setAttribute`. Standardize on Google-style docstrings and PEP 604 unions across the module. Add a `Fonts.MONOSPACE` to `styles/` resolving per platform. Fix the typo and the inaccurate signal claim. Add smoke tests (`pytest-qt`) for the seven untested widgets — the five existing component tests in `tests/gui/` show the pattern works.

### Cross-module notes

- **The 38 inline `setStyleSheet` literals are mostly outside my lane.** Repo-wide there are 203 `setStyleSheet` calls: 151 pass a `styles.*` constant (good), 38 pass an inline string literal, 14 pass a variable. The inline literals concentrate in `pages/pipeline/` — `comparison_stacker.py` (10), `correct_alignments_stacker.py` (6), `viewer_stacker.py` (6), `pllr_stacker.py` (3), `pages/datasets/datasets_page.py` (3) — plus 4 in my scope (`loading_dialog.py:147,168,184,199`, which at least interpolate `Colors`) and 1 in `gui/__init__.py:466`. `viewer_stacker.py` alone carries 28 raw hex values. Whoever audits `pages/pipeline/` should own that; the palette work in GC-2/GC-3 is the prerequisite.
- **Two analyzers set Qt stylesheets.** `src/voxkit/analyzers/default_analyzer.py` and `clip_duration_statistics.py` each contain 2 `setStyleSheet` calls and 4 raw hex values. Per `AGENTS.md`, `analyzers/` is "Dataset metadata extractors (CSV summaries)" — a non-GUI layer building styled Qt widgets is a layering violation for the analyzers audit.
- **`ruff target-version = "py310"`** in `pyproject.toml` while `requires-python = ">=3.11"` and `[tool.mypy] python_version = "3.11"`. Minor config drift, belongs to whoever owns build/tooling.
- **Qt binding confirmed as PyQt6**, consistently: `pyproject.toml` pins `pyqt6>=6.9.1`, `AGENTS.md` says PyQt6, and all 64 Qt imports in `src/` are PyQt6. No `PySide` import exists anywhere and no migration is in flight. Recorded because the audit brief for the GUI modules mis-stated the binding as PySide6; the finding above and all others in this section were written against the actual code.
- **`workers/startup.py:85-93`** drives `LoadingDialog` with a manual `for _ in range(3): app.processEvents()` plus a `QTimer.singleShot(100, lambda: None)` — a render-timing workaround around the dialog. It uses my component but lives in `workers/`; flagging for that module's auditor since the fix may belong on either side.


---

## Module: `src/voxkit/gui/pages/{datasets,models}/` + `gui/workers/`

**Health:** Functional but structurally fragile — the threading layer is unsupervised and the two pages are diverging copies of each other | **Files:** 12 | **LOC:** 2121 | **Findings:** 18 (5 High / 12 Medium / 1 Low)

These three packages are the CRUD surface for datasets and models plus the shared QThread layer that both pages (and, heavily, the pipeline page) depend on. The debt clusters in three places: (1) the threading layer is a thin, unpoliced wrapper — workers have no owner, no cancellation, no shutdown path, and the two registration workers don't even guard `run()`, so a documented-raising storage call silently kills the thread and hangs the UI with zero feedback; (2) the two pages were written by copy-paste and have since drifted, with an entire dead-and-broken duplicate module (`datasets/utils.py`) left behind; (3) the pages narrate themselves with 31 `print()` calls while the app ships a rotating file logger and an in-app log viewer, so none of that diagnostic output reaches anyone. Notably, the heavy filesystem operations that most need a worker (import/export, which `shutil.copytree` whole corpora) run synchronously on the UI thread, while the operations that got a worker report nothing back to the user.

### Findings

#### PW-1. Registration workers run unguarded — a raising storage call silently hangs the UI forever — `High` / `S`
**Where:** `src/voxkit/gui/workers/datasets_thread.py:51-91`, `src/voxkit/gui/workers/models_thread.py:42-68`
**What:** Neither `DatasetRegistrationWorker.run()` nor `ModelRegistrationWorker.run()` has a `try`/`except`, unlike their siblings `WorkerThread.run()` (`worker_thread.py:31-36`) and `StartupScriptWorker.run()` (`startup.py:39-48`), which both wrap everything. The unguarded calls are documented as raising: `storage/datasets.py:168-170` (`create_dataset`) states `Raises: FileExistsError ... Exception: If directory creation, metadata writing, or caching fails`, and `storage/models.py:118-120` (`create_model`) states `Raises: Exception: If directory creation or metadata writing fails`. `datasets_thread.py:67` also does a raw dict subscript `ManageAnalyzers.get_analyzers()[self.analysis_method]` (KeyError) instead of the guarded `ManageAnalyzers.get_analyzer(id)` helper that exists at `analyzers/__init__.py:74-79`.
**Why it's debt:** An exception propagates out of `run()`, the thread dies, and the custom `finished` signal is never emitted. `registration_complete` never fires, so the page shows nothing at all — no error dialog, no state change. Because `show_progress` only calls `print()` (PW-7), the user gets a UI that looks like it's still working, indefinitely. This is precisely the path that consumes a user-chosen directory, i.e. the most likely thing to fail in the field.
**Fix:** Wrap both `run()` bodies in `try/except Exception as e: self.finished.emit(False, str(e))`, matching `WorkerThread.run()`. Better: delete both classes and express them as `WorkerThread(callable)` (see PW-6), which already has this guard and is already tested.

#### PW-2. Workers have no owner, no cancellation, and no shutdown path — a QThread can outlive its widget — `High` / `M`
**Where:** `src/voxkit/gui/pages/datasets/datasets_page.py:806-821`, `src/voxkit/gui/pages/models/models_page.py:250-257`
**What:** Both pages do `self.registration_worker = <Worker>(...)` then `.start()`. Three gaps, all verified by grep across `src/voxkit/gui`:
- Re-entrancy: clicking "Register" twice rebinds `self.registration_worker`, dropping the only Python reference to a still-running `QThread`. PyQt will collect the wrapper → `QThread: Destroyed while thread is still running` / abort. Nothing guards on `isRunning()` (zero hits repo-wide) and the button is never disabled.
- Cancellation: `requestInterruption` / `isInterruptionRequested` have zero hits anywhere in `src/voxkit/gui`. `DatasetRegistrationWorker` with `cache=True` copies an entire corpus via `shutil.copytree`; there is no way to stop it.
- Shutdown: neither `DatasetsPage` nor `ManageAlignersWidget` defines `closeEvent`, and there is no `aboutToQuit` hook (zero hits outside `components/`). Quitting mid-registration leaves a live thread with a dangling reference to a destroyed widget.
`startup.py:116-118` shows the team knows the correct shape (`worker.start()` … `worker.wait()`); the pages just don't do it.
**Why it's debt:** Intermittent, hard-to-reproduce crashes on quit and on double-click, and a long operation users cannot escape. Every future long-running feature copied from these two call sites inherits the same hole.
**Fix:** Guard entry on `worker is not None and worker.isRunning()` and disable the trigger button until `finished`; add a `closeEvent` that calls `requestInterruption()` then `wait(<timeout>)`; give workers an interruption check between phases. Centralize this in one owner (a small `WorkerHost` mixin) rather than repeating it per page.

#### PW-3. All four workers redefine `finished`, shadowing `QThread.finished` — `High` / `M`
**Where:** `src/voxkit/gui/workers/worker_thread.py:25`, `datasets_thread.py:27`, `models_thread.py:28`, `startup.py:32`
**What:** Each class declares `finished = pyqtSignal(...)` — `QThread` already has a built-in `finished()` signal. The subclass declaration shadows it in the Python namespace, so `worker.finished` no longer refers to actual thread termination. `startup.py:32` is the worst case: `finished = pyqtSignal()` has the *identical* zero-arg signature as the real one, so the substitution is invisible at the call site (`startup.py:112`).
**Why it's debt:** The standard Qt cleanup idiom `worker.finished.connect(worker.deleteLater)` is now actively unsafe here — the custom signal is emitted from *inside* `run()`, while the thread is still executing, so `deleteLater` would be scheduled on a live thread. It also means no consumer can observe real thread exit. This is not hypothetical coupling: `WorkerThread` is instantiated at 8 sites in `gui/pages/pipeline/` (`training_stacker.py:217`, `pllr_stacker.py:519`, `viewer_stacker.py:723,996`, `comparison_stacker.py:781`, `transcription_stacker.py:182`, `correct_alignments_stacker.py:1128`, `prediction_stacker.py:187,243`), so the trap is repo-wide.
**Fix:** Rename the custom signals (`completed = pyqtSignal(bool, str)`, `succeeded = pyqtSignal()`), leaving `QThread.finished` intact for lifetime management. Mechanical rename across the 8 pipeline call sites.

#### PW-4. Heavy filesystem I/O runs synchronously on the UI thread — while a worker layer sits unused — `High` / `M`
**Where:** `src/voxkit/gui/pages/datasets/datasets_page.py:188` and `:214`; `src/voxkit/gui/pages/models/utils.py:42` and `:123`; `src/voxkit/gui/pages/models/models_page.py:96-107`
**What:**
- `datasets_page.on_import` calls `datasets.import_dataset(Path(dir_path))` directly; `on_export` calls `datasets.export_dataset(...)` directly. `storage/datasets.py:412` documents export as "Copies the entire dataset directory (including metadata, alignments, and cache)".
- `models/utils.handle_export:123` calls `shutil.copytree(source_path, dest_path, dirs_exist_ok=True)` per selected model, inline; `handle_import:42` calls `models.import_models(...)`.
- `ManageAlignersWidget.showEvent` calls `refresh_data()` + `update_display()`, which run `models.list_models(engine)` for every engine on *every* tab switch.
- `DatasetsPage.__init__:56` calls `refresh_datasets()` → `datasets.list_datasets_metadata()` during widget construction.
**Why it's debt:** Multi-gigabyte corpus copies freeze the window with no progress and no beachball-free repaint; on macOS/Windows the OS marks the app "Not Responding". The module already owns the fix (`WorkerThread`) and uses it for the *lighter* registration path, so this is an inconsistency, not a missing capability.
**Fix:** Route import/export through `WorkerThread` with the same `finished(bool, str)` → `QMessageBox` handler the registration path already uses, and show the existing `LoadingDialog` while it runs.

#### PW-5. `datasets/utils.py` is a dead module containing a broken, divergent copy of two page methods — `High` / `S`
**Where:** `src/voxkit/gui/pages/datasets/utils.py:18-54` vs `src/voxkit/gui/pages/datasets/datasets_page.py:197-242`
**What:** `utils.on_export` / `utils.on_delete` are free functions whose first parameter is literally named `self` — fake methods duplicating `DatasetsPage.on_export` / `DatasetsPage.on_delete`. Grep confirms nothing imports this module: the only `from .utils` hits in the repo are `storage/alignments.py:47` and `models/models_page.py:26`, and `datasets/__init__.py:16` exports only `DatasetsPage`. The copies have also drifted into being *wrong*: `utils.py:35` does `datasets.export_dataset(self.selected_dataset["id"], ...)` and `utils.py:48` does `datasets.delete_dataset(self.selected_dataset["id"])`, but `DatasetsPage.selected_dataset` is a plain string ID (set from `item.data(Qt.ItemDataRole.UserRole)` at `datasets_page.py:442`, asserted as `"ds-1"` in `tests/gui/test_datasets_page.py:175`). Subscripting a `str` with `"id"` raises `TypeError`. The dead copy also omits the deletion confirmation dialog that the live version has at `datasets_page.py:226-233`.
**Why it's debt:** A future reader wiring these up gets a crash plus a silently missing "are you sure you want to delete" prompt on a destructive action. The module also misleads: its docstring advertises an API (`on_export`, `on_delete`) that no caller uses.
**Fix:** Delete `src/voxkit/gui/pages/datasets/utils.py`.

#### PW-6. Six duplicated blocks between `datasets_page.py` and `models_page.py` — `Medium` / `M`
**Where:** paired sites, datasets ↔ models:
| Duplicate | datasets_page.py | models_page.py |
|---|---|---|
| `get_engines()` | `58-68` | `84-94` |
| `on_huggingface_browse()` (TODO + identical QMessageBox) | `165-173` | `147-155` |
| "+ Register New …" button container | `252-263` | `132-145` |
| `open_registration_dialog()` `SettingsConfig` → `exec()` → `get_values()` → `process_registration()` | `644-766` | `184-228` |
| worker-wiring tail of `process_registration()` | `806-821` | `250-257` |
| `show_progress()` + `registration_complete()` | `823-834` | `259-271` |
**What:** `get_engines` differs only in the tool predicate (`has_tool("align")` vs `has_tool("align") or has_tool("train")`) and both use the same deferred `from voxkit.engines import engines` import inside the function body. `show_progress` is byte-identical (`print(message)`). Both copies of the worker tail also carry the same dead guard — `if self.registration_worker is None: return` (`datasets_page.py:816-817`, `models_page.py:252-253`) — immediately after assigning a freshly constructed object, so it can never be true. `startup.py` has its own instance of this: `execute_startup_script:74-118` and `execute_mfa_provisioning:145-171` repeat the same dialog → worker → `exec()` → `wait()` scaffolding.
**Why it's debt:** Every fix to worker lifetime (PW-2), progress reporting (PW-7), or the register-button styling has to be made in two-to-three places, and PW-5 is direct evidence this module already fails that discipline.
**Fix:** Extract a `RegistrationMixin` (or a small `register_via_worker(worker, on_success)` helper) holding the worker-wiring + progress + completion handlers, and an `engines_with_tools(*tools)` helper in `voxkit.engines`. Fold the two `startup.py` functions into one parameterized `_run_with_loading_dialog(script, message, subtitle, app)`.

#### PW-7. 31 `print()` calls bypass the app's logger and its in-app log viewer — `Medium` / `S`
**Where:** `datasets_page.py` ×11 (e.g. `:434`, `:437`, `:465`, `:489-490`, `:502`, `:825`, `:965`), `models_page.py` ×12 (`:51`, `:55`, `:59`, `:63`, `:166`, `:175`, `:179`, `:227`, `:246`, `:261`), `import_dialog.py` ×5, `models/utils.py:245`, `datasets_thread.py:86`, `models_thread.py:62`. Only `workers/startup.py:12,21` uses `logging.getLogger(__name__)`.
**What:** The app configures a `RotatingFileHandler` (`config/logging_config.py:26-57`, called from `main.py:123`) and ships a user-facing `LogViewerDialog` (`gui/components/log_viewer_dialog.py`, opened from `gui/__init__.py:508`). None of the 31 `print()` calls reach either. Several are raw debug leftovers — `datasets_page.py:437` is a bare `print(item)` of a `QTableWidgetItem`, `:490` dumps the entire alignment list, `:502` dumps each alignment dict per row.
**Why it's debt:** In a PyInstaller-bundled GUI there is no attached stdout, so this output is discarded entirely. When a user reports "registration did nothing" (PW-1), the log file a maintainer asks for contains none of the surrounding context. The per-row prints in `_display_alignments` also make the table render O(n) stdout writes.
**Fix:** Replace with `logger.debug/info/exception`; delete the bare dump prints at `:437`, `:490`, `:502`. Route `show_progress` (`datasets_page.py:823`, `models_page.py:259`) into a real status label or the existing `LoadingDialog` so the `progress` signal earns its existence.

#### PW-8. Dead and unreachable code across the module — `Medium` / `S`
**Where:** verified by repo-wide grep (`src`, `tests`, `main.py`, `scripts`) — each has zero callers:
- `datasets_page.py:593-596` `convert_alignments()` — docstring even says "Generate mock alignment data (to be replaced with actual data loading)"; body just forwards to `alignments.list_alignments`.
- `datasets_page.py:610-617` `_export_alignment()` — TODO stub; also indexes `alignment['model']`, a key that does not exist on `AlignmentMetadata` (the real key is `model_metadata`, per `:508`).
- `models_page.py:157-167` `scrub_training_runs()` — no docstring, and rebinds its own loop-invariant parameter `mode` inside the `for` loop, so iteration 2 tests the already-rewritten value.
- `models_page.py:174-182` `open_import_dialog()` — the *only* production caller of `reload_models()`; `:182` would `AttributeError` if `self._parent_widget` is `None`.
- `models_page.py:274-305` — 32 lines of commented-out `__main__` example.
- `models/utils.py:146-199` `handle_export_lambda()` and `create_export_handler()` — referenced only from their own docstrings and the commented block above; both are advertised in the module's `API` docstring header (`utils.py:10-11`).
- `models/utils.py:203-245` — an `if __name__ == "__main__":` demo in a library module, which constructs a `QApplication` and prints.
- `import_dialog.py:114-124` `main()` — dead *and* broken: `:121` calls `ImportModelDialog(on_import=..., engines=[...])` but the constructor (`:30-35`) has no `engines` parameter → `TypeError`.
- `datasets_page.py:77-78` sets `main_layout.setSpacing(20)` / `setContentsMargins(20,20,20,20)`, then `:123-124` overwrites both with `setSpacing(20)` / `setContentsMargins(0,0,0,0)`. The first margin call is a no-op.
- `startup.py:89-92`: `QTimer.singleShot(100, lambda: None)` followed immediately by `app.processEvents()`, under the comment "Give the dialog time to render before starting work". Scheduling a no-op callback waits for nothing; the comment describes behavior the code does not have.
**Why it's debt:** Grep results and the `API` docstring headers both lie about what this module offers, and two of these stubs (`_export_alignment`, `import_dialog.main`) would crash on first use by anyone who trusts them.
**Fix:** Delete all of the above. Where a stub marks intent, replace with a tracked issue rather than a broken body.

#### PW-9. Swallowed exceptions turn failures into empty or silently-wrong UI — `Medium` / `S`
**Where:** `models_page.py:50-52`, `datasets_page.py:964-965`, `models/utils.py:63-64` and `:142-143`, `import_dialog.py:83-85` and `:102-105`, `datasets_page.py:553-557`
**What:**
- `models_page.py:50-52`: `refresh_models_function` wraps the whole engine loop in `except Exception as e: print(...); return {}`. A storage read failure renders as "you have no models" — indistinguishable from an empty install, and destructive follow-on actions proceed against that empty view.
- `import_dialog.py:83-85`: `accept()` returns silently when `model_path` is empty, with the comment `# Could add a QMessageBox warning here`. Clicking OK does nothing and the dialog stays open with no explanation.
- `import_dialog.py:102-105`: after `models.create_model` succeeds, if `message` isn't a `dict` the method just `return`s — leaving a created-but-empty model entry in storage and no download, with no message to anyone.
- `datasets_page.py:964-965`: `except Exception` around analyzer lookup + CSV read + `visualize()`, `print`-only; the dialog then silently falls back to a raw table with no indication the visualization failed.
- `datasets_page.py:553-557`: `except TypeError: pass` on `cellClicked.disconnect()` (see PW-14).
**Why it's debt:** Silent degradation is the hardest failure class to diagnose, and here it is combined with PW-7 (the diagnostic goes to a discarded stdout).
**Fix:** Log with `logger.exception` and surface a user-visible error state (an error row/banner) rather than returning an empty collection. Add the missing `QMessageBox.warning` in `accept()`.

#### PW-10. `_add_register_button` index-walks another module's private layout and silently no-ops on miss — `Medium` / `S`
**Where:** `src/voxkit/gui/pages/models/models_page.py:109-145`
**What:** To place one button, the method does a two-level scan of `CategoricalTableWidget`'s layout: `for i in range(self.layout().count())` → `for j in range(widget.layout().count())` → `if item.widget() == self.table_widget`, then `models_group.layout().insertWidget(0, button_container)`. If the scan finds nothing, `:129-130` does `if not models_group: return` — no log, no raise. This works today only because `categorical_table.py:151-173` happens to put `self.table_widget` directly inside `models_group`'s layout, which is directly inside `main_layout`.
**Why it's debt:** Any reordering or extra nesting in `categorical_table.py` (a framework this module does not own) makes the "+ Register New Model" button vanish with no error anywhere. It is also untestable — there is no assertion anywhere that the button exists.
**Fix:** Have `CategoricalTableWidget` expose a named insertion point (e.g. `add_header_widget(w)` or a `header_layout` attribute) and call that; at minimum, `logger.warning` instead of the bare `return`.

#### PW-11. 40 of 74 functions carry no annotations at all, so mypy skips their bodies entirely — `Medium` / `M`
**Where:** counted with `ast` over the module. Fully-unannotated functions per file: `datasets_page.py` 16/31 (`init_ui:74`, `_on_dataset_selected:421`, `refresh_datasets:836`, `on_import:175`, `on_export:197`, `on_delete:220`, `registration_complete:827`, …), `models_page.py` 9/16 (`__init__:36`, `showEvent:96`, `_add_register_button:109`, `open_registration_dialog:184`, …), `datasets_thread.py` 2/2, `models_thread.py` 2/2, `worker_thread.py` 2/2, `startup.py` 3/8, `models/utils.py` 2/6, `import_dialog.py` 2/5, `datasets/utils.py` 2/2.
**What:** `pyproject.toml:124` sets `check_untyped_defs = false`, so mypy does not type-check the *body* of any function lacking annotations. `DatasetRegistrationWorker.__init__` (`datasets_thread.py:30-40`) takes 8 untyped parameters; `WorkerThread.__init__(self, operation_func)` (`worker_thread.py:27`) is untyped; no `run()` has `-> None`. Weak annotations elsewhere: `get_engines(self) -> list` in both pages (element type erased), `handle_import(parent_widget, ...)` / `handle_export(parent_widget, ...)` (`models/utils.py:23,67`) with untyped widget params, and `import_dialog.py:32` declares `on_import: Optional[Callable[[str, str], None]]` (two args) while both the call site `:88` and the default implementation `_placeholder_import:91` take exactly one. Also `datasets_page.py:485` annotates `alignments: list[alignments.AlignmentMetadata]` — the parameter name shadows the imported `alignments` module inside the body, and the file mixes `alignments.AlignmentMetadata` (`:485`, `:572`) with the directly-imported `AlignmentMetadata` (`:598`, `:619`) for the same type.
**Why it's debt:** More than half the module is invisible to `invoke mypy-check`, which is exactly where the real bugs are (PW-13's `UnboundLocalError`, PW-8's `alignment['model']`, PW-5's `str["id"]` would all be caught by a checked body). The wrong `Callable` arity means any caller who trusts the annotation and passes a two-arg callback gets a `TypeError`.
**Fix:** Annotate the workers and page methods (`-> None` is enough for most), fix the `Callable[[str], None]` arity, rename the shadowing parameter, then flip `check_untyped_defs = true` and burn down the resulting list.

#### PW-12. Inline stylesheets and raw hex colors bypass the style layer — inconsistently, within one file — `Medium` / `S`
**Where:** `src/voxkit/gui/pages/datasets/datasets_page.py:84`, `:253`, `:312-339`; `src/voxkit/gui/pages/models/models_page.py:134`
**What:** `datasets_page.py:312-339` sets a 27-line inline stylesheet on `self.dataset_table` with seven raw hex colors (`#ecf0f1`, `#f5f8fa`, `#bdc3c7`, `#e8f4f8`, `#3498db`, `#34495e`) — while `:411`, in the *same class*, styles the sibling `self.alignments_table` with `Containers.TABLE_WIDGET`. `:84` sets the page title with `"font-size: 24px; font-weight: bold; color: #2c3e50;"` inline rather than a `Labels.*` constant. `"background-color: transparent;"` is inlined identically at `datasets_page.py:253` and `models_page.py:134`. Everything else in both files correctly uses `voxkit.gui.styles` (`Buttons.*`, `Containers.*`, `Labels.*`), so the style layer clearly exists and is otherwise honored.
**Why it's debt:** The two tables on the same page are now guaranteed to drift apart on any theme change, and the hardcoded `#2c3e50` / `#34495e` will not follow a palette update. This is a deviation from the module's own dominant convention, not a missing one.
**Fix:** Move the block at `:312-339` to `Containers.TABLE_WIDGET` (or a `TABLE_WIDGET_SELECTABLE` variant if the hover/selected states genuinely differ), add a `Labels.PAGE_TITLE`, and a `Containers.TRANSPARENT` for the button container.

#### PW-13. `_on_dataset_selected` reads a variable defined inside a conditional — `Medium` / `S`
**Where:** `src/voxkit/gui/pages/datasets/datasets_page.py:421-445`
**What:**
```python
item = self.dataset_table.item(row, 0)
if item:
    dataset_id = item.data(Qt.ItemDataRole.UserRole)
    self.selected_dataset = dataset_id
    self._set_alignments_blur(False)

self._load_alignments(dataset_id)   # :445 — outside the guard
```
If `item` is `None`, `dataset_id` is unbound → `UnboundLocalError`. Even when `item` exists, `data(UserRole)` returns `None` for any row whose column-0 item was created without `setData` — `_load_alignments(None)` then queries storage with a `None` id and repopulates the filter combo against an empty result. `Qt.ItemDataRole.UserRole` being set is an implicit contract held only by `refresh_datasets:855`, with no assertion anywhere.
**Why it's debt:** A silent invariant between two methods 400 lines apart, in the hottest interaction path on the page, in a function body mypy does not check (PW-11). Any future code that adds a row without `setData` breaks selection.
**Fix:** Move `self._load_alignments(...)` inside the `if item:` block and early-return on a falsy `dataset_id`; consider a typed `_dataset_id_for_row(row) -> str | None` accessor so the `UserRole` convention has exactly one reader and one writer.

#### PW-14. `cellClicked` is disconnected and reconnected on every table render — `Medium` / `S`
**Where:** `src/voxkit/gui/pages/datasets/datasets_page.py:552-558`
**What:** At the end of `_display_alignments`, every render does `self.alignments_table.cellClicked.disconnect()` inside `try: … except TypeError: pass`, then reconnects `self._on_alignment_cell_clicked`. The bare `disconnect()` drops *all* slots on that signal, not just this one.
**Why it's debt:** Signal wiring belongs in construction, not in a render loop. As written, any other subscriber to `cellClicked` added later is silently unhooked the next time the table refreshes — a bug that manifests as "the feature works until you change the engine filter". `_filter_alignments:479-483` calls back into `_load_alignments` → `_display_alignments`, so this churn runs on every filter change.
**Fix:** Connect once in `_create_alignments_panel` (`:358-419`) alongside the other table configuration and delete the disconnect block.

#### PW-15. Views reach into private storage internals — `Medium` / `S`
**Where:** `src/voxkit/gui/pages/datasets/datasets_page.py:925` (`datasets._get_dataset_root(dataset_id)`), `src/voxkit/gui/pages/models/utils.py:110` (`models._get_model_root(current_category, item["id"])`)
**What:** Both call underscore-prefixed functions from `voxkit.storage`. `datasets_page.py:936` then globs the returned directory directly (`dataset_dir.glob("*_summary.csv")`) and `:953` reverse-engineers the analyzer name from the filename via `csv_files[0].stem.replace("_summary", "").lower()` — reconstructing a naming convention that `storage/datasets.py` owns (its docstring at `:177` documents `{analysis_method}_summary.csv`).
**Why it's debt:** AGENTS.md designates `storage/` as the model layer that views access directly, but that contract is about the *public* surface. Renaming the summary-CSV convention or the private root helpers silently breaks the Details dialog and model export with no compile-time signal, and the filename-parsing round-trip is lossy (`.lower()` vs the analyzer's real `name`, e.g. `"Clip Duration Statistics"`).
**Fix:** Add public `datasets.get_summary_csv(dataset_id) -> Path | None` and `models.get_model_path(engine_id, model_id) -> Path | None` to storage, and have storage record `analysis_method` in the dataset metadata so the analyzer lookup is a dict read, not a filename parse.

#### PW-16. `ImportModelDialog` collects a field it discards, and never surfaces its failures — `Medium` / `S`
**Where:** `src/voxkit/gui/pages/models/import_dialog.py:55-61`, `:77-89`, `:91-111`
**What:** The dialog defines a second field `local_model_path` ("Local Model Path:", `:55-61`), but `accept()` (`:79-88`) reads only `values.get("model_path")` and `_placeholder_import` (`:91-111`) never receives or uses it. The field is presented, validated by nothing, persisted to `store_file` (`:69`), and dropped. Meanwhile the download outcome is reported only via `print` (`:109`, `:111`) — a failed HuggingFace download shows the user nothing at all, even though the same method already knows how to raise a `QMessageBox.critical` (`:100`). The module docstring (`:3`) says "importing alignment models from HuggingFace Hub", not "or from a local path", so the field's intent is undocumented as well.
**Why it's debt:** A user who fills in the local path gets no model and no error. Reachable in production only through `models_page.open_import_dialog`, which is itself dead (PW-8) — so this is currently unreachable *and* broken, which is the worst state to leave a half-built feature in.
**Fix:** Either implement the local-path branch or delete the field; replace the `print`s at `:109/:111` with a `QMessageBox` on failure; fix the `Callable[[str, str], None]` arity (PW-11).

#### PW-18. Test coverage in this module tests the wrong things — `Medium` / `M`
**Where:** `tests/gui/test_datasets_page.py`, `tests/gui/test_models_page.py`, `tests/gui/test_worker_thread.py`
**What:** Coverage of my scope is: `datasets_page` — `refresh_datasets`, `_display_alignments`, `on_delete` confirmation only; `models_page` — three tests, all of `reload_models`, all against a `MagicMock` stand-in (`test_models_page.py:9-13`) rather than a real widget; `worker_thread` — four solid tests. Nothing at all exercises `workers/datasets_thread.py`, `workers/models_thread.py`, `workers/startup.py`, `pages/models/import_dialog.py`, `pages/models/utils.py`, or `pages/datasets/utils.py`. Two specific mismatches: (a) `test_models_page.py` is the only coverage of `models_page`, and the method it tests, `reload_models`, is reachable in production *only* from the dead `open_import_dialog` (PW-8) — the tests keep dead code alive; (b) nothing covers `process_registration`, the worker wiring, or `_on_dataset_selected`, i.e. every path implicated in PW-1, PW-2 and PW-13.
**Why it's debt:** `pyproject.toml:149-151` omits `gui/pages/**` and `gui/workers/**` from coverage metrics, so this gap is invisible in CI, yet the workers are pure logic (no widgets) and are trivially testable with `qtbot.waitSignal` — `test_worker_thread.py` already proves the pattern.
**Fix:** Port the `test_worker_thread.py` pattern to `DatasetRegistrationWorker` / `ModelRegistrationWorker` (mock `voxkit.storage.datasets.create_dataset` to raise and assert `finished(False, …)` — this test fails today, which is PW-1). Add a `process_registration` validation test per page. Replace the `MagicMock` in `test_models_page.py` with a real widget once `reload_models` has a live caller.

#### PW-17. Engine IDs and analyzer names are hardcoded string literals — `Low` / `S`
**Where:** `src/voxkit/gui/pages/models/models_page.py:159-164`, `:213`, `:234`; `src/voxkit/gui/pages/models/import_dialog.py:34`; `src/voxkit/gui/pages/datasets/datasets_page.py:706`, `:773`
**What:** `scrub_training_runs` branches on `"MFA" in mode` / `"W2TG" in mode` and assigns the literals `"MFAENGINE"` / `"W2TGENGINE"` (`:159-164`); `open_registration_dialog` falls back to `"MFAENGINE"` (`:213`) and `process_registration` defaults to `"MFAENGINE"` (`:234`); `ImportModelDialog.__init__` defaults `engine_id: str = "W2TGENGINE"` (`:34`). On the datasets side, `"Default"` is hardcoded twice (`:706`, `:773`) as the analyzer fallback — it duplicates `DefaultAnalyzer.name` (`analyzers/default_analyzer.py:30`), which is the registry key at `analyzers/__init__.py:86`.
**Why it's debt:** AGENTS.md describes engines as a registry with "an abstract base class and a singleton manager for discovery"; these literals defeat that. Renaming an engine or the default analyzer breaks the models page at runtime with a `KeyError`/silent-wrong-engine rather than at import.
**Fix:** Take defaults from `engines.list_engines()[0]` / `ManageAnalyzers.list_analyzers()[0]` (or named constants exported by those registries) instead of string literals. `scrub_training_runs` is dead (PW-8) and should just be deleted.

### Cross-module notes

- **`WorkerThread` is genuinely shared, but only by the pipeline page.** It has 8 instantiation sites in `gui/pages/pipeline/` (`training_stacker.py:217`, `pllr_stacker.py:519`, `viewer_stacker.py:723,996`, `comparison_stacker.py:781`, `transcription_stacker.py:182`, `correct_alignments_stacker.py:1128`, `prediction_stacker.py:187,243`) and zero in my two pages — my pages hand-rolled `DatasetRegistrationWorker` / `ModelRegistrationWorker` instead. So `worker_thread.py` is a real base for the pipeline and a bypassed one for datasets/models. The `finished`-shadowing fix (PW-3) is a repo-wide rename that touches the pipeline page; flagging for whoever owns it, not auditing it.
- **`gui/frameworks/categorical_table/categorical_table.py`** exposes no insertion point for page-level chrome, which is what forces the layout-index walk in PW-10. The fix belongs in the framework, not in `models_page.py`.
- **Qt binding:** no drift here — `AGENTS.md`, `pyproject.toml`, and the code all agree on PyQt6, and nothing in this scope imports PySide6. (The audit brief mis-stated the binding; the code is authoritative and was what these findings were written against.)
- **`analyzers/__init__.py:67`** has a `print()` inside `list_analyzers()`, which my pages call on every registration dialog open (`datasets_page.py:97`). Same logging problem as PW-7, different module.
- **`storage/datasets.py` and `storage/models.py` document `Raises: Exception`** on their create functions while returning `(bool, message)` tuples for expected failures — a mixed error contract that is the root enabler of PW-1. A consistent convention (either always-tuple or always-raise) would let the worker layer be written once, correctly.


---

## Module: `tests/`

**Health:** Red on 2 of 3 CI platforms for 8 days, with a coverage badge that overstates a metric already scoped to 7% of the codebase | **Files:** 33 (26 test modules, 1 conftest, 1 mislabelled helper, 7 `__init__.py`) | **LOC:** 5,281 | **Findings:** 11 (4 High / 5 Medium / 2 Low)

The suite is fast (10s for 324 tests), has no sleeps, no `xfail`, no network, and exactly one `pytest.skip` that does not actually fire in CI — so it is not a suite full of phantom tests. Its debt is elsewhere: it is **currently failing** on macOS and Ubuntu and has been since 2026-08-11, with two PRs merged to `main` on top of the red, which means the CI signal has already stopped functioning as a gate. Underneath that, the coverage story is doubly misleading — `assets/coverage.svg` advertises 82.98% when the real number is 70.94%, and that 70.94% is measured over 1,294 of ~17,959 statements because `[tool.coverage.run] omit` excises the entire GUI layer, all of `services/`, and every engine implementation. The tests that exist are mostly good (`tests/services/`, `tests/engines/test_base.py`, `tests/storage/` behaviour tests are genuine), but they are wired together by a hand-rolled, CWD-relative storage fixture that is copy-pasted 85 times and has no `conftest.py` anywhere outside `tests/gui/`.

### Coverage map

| Production module | LOC | Test files | Tested? | Notes |
|---|---:|---|---|---|
| `storage/` | 1,967 | `test_datasets.py`, `test_alignments.py`, `test_models.py`, `test_utils.py` (+`test_setup.py` helper) | **Yes — best-covered area** | 2,793 test LOC, 114 tests. Real filesystem round-trips, not mocks. Measured: `datasets.py` 76.9%, `models.py` 70.9%, `alignments.py` 68.8%, `utils.py` 95.7%. All of it hangs off the fragile shared root in TS-4. |
| `config/` | 665 | `test_app_config.py`, `test_pipeline_config.py`, `test_logging_config.py` | **Partial** | `pipeline_config.py` and `logging_config.py` at 100%; `app_config.py` 88.5%. **`startup_config.py` (160 LOC) has zero tests** — verified: zero test files mention `startup_config`. It is also on the coverage `omit` list, so its absence is invisible. |
| `analyzers/` | 655 | `test_analyzer_manager.py`, `test_default_analyzer.py` | **Partial — 2 of 4 analyzers untested** | `default_analyzer.py` 67.9%. **`clip_duration_statistics.py` (199 LOC) at 11.7% and `audio_format_profile.py` (86 LOC) at 31.9%** — only import lines execute; zero test files mention either. AGENTS.md:84 explicitly names `analyzers/` as a place tests are expected. |
| `engines/` | 1,164 | `test_base.py`, `test_engine_manager.py` | **ABC only** | `base.py` 98.4%, `__init__.py` 100%. All three implementations — `mfa_engine.py` (292), `w2tg_engine.py` (281), `faster_whisper_engine.py` (183) — have zero tests and are `omit`ed. Documented as deliberate (AGENTS.md:90). |
| `services/` | 508 | `test_mfa.py`, `test_mfa_provision.py` | **Yes — but invisible** | 27 tests, genuinely good (regression guards with explanatory docstrings). Contradicts `pyproject.toml:156` `omit = "src/voxkit/services/**/*.py"`, so none of this work registers in the coverage number. 2 of these tests are the ones failing CI (TS-1). |
| `gui/` **total** | 12,960 | 13 files in `tests/gui/` | **~7% reached; 0% measured** | Entire layer `omit`ed (`pyproject.toml:147-154`), so no per-file numbers exist. |
| ├─ `gui/components/` | 1,314 | `test_animated_stack`, `test_column_dropdown`, `test_csv_viewer_dialog`, `test_loading_dialog`, `test_toggle_switch` | Partial | Real `qtbot` widget tests. Untested: `dna_strand`, `grip_splitter`, `huggingface_button`, `log_handler`, `log_viewer_dialog`, `model_selection_panel` (236), `overlay_effects`. |
| ├─ `gui/frameworks/` | 1,436 | `test_settings_modal_tooltips.py` (51 LOC, 2 tests) | Barely | `settings_modal/generic.py` is 550 LOC; two tooltip assertions touch it. **`categorical_table.py` (688 LOC) has zero tests.** |
| ├─ `gui/pages/datasets/` | 1,041 | `test_datasets_page.py` | Partial | 11 tests over table rendering + delete confirmation. `datasets/utils.py` (54) untested. |
| ├─ `gui/pages/models/` | 692 | `test_models_page.py` | Nominal only | 3 tests, all mock-on-mock (TS-7). `import_dialog.py` (124) and `models/utils.py` (245) untested. |
| ├─ **`gui/pages/pipeline/`** | **6,736** | `test_base_stacker.py`, `test_prediction_stacker_validation.py` | **~7% — the biggest gap** | Only `base_stacker.py` (208) and one guard clause in `prediction_stacker.py` (256) are reached. **Zero tests reference** `viewer_stacker.py` (2,092), `comparison_stacker.py` (1,279), `correct_alignments_stacker.py` (1,206), `pllr_stacker.py` (693), `training_stacker.py` (373), `pipeline/__init__.py` (333), `transcription_stacker.py` (221), `markdown_stacker.py` (75) — 6,272 LOC. |
| ├─ `gui/workers/` | 388 | `test_worker_thread.py` | Generic only | `worker_thread.py` (36) is well tested via `qtbot.waitSignal`. **`startup.py` (171), `datasets_thread.py` (91), `models_thread.py` (68) have zero tests** — the app's actual async surface. |
| ├─ `gui/styles/` | 803 | — | No | Stylesheet strings; low risk. |
| ├─ `gui/__init__.py` | 515 | `test_feedback.py` | Sliver | 3 tests over `build_feedback_mailto_url` / `open_feedback` only. |
| └─ `gui/utils.py` | 35 | `test_utils.py` | Yes | 3 tests, complete. |

Measured total across non-omitted code: **1,294 statements, 70.94%**. Badge claims 82.98%.

### Findings

#### TS-1. The suite is red on macOS and Ubuntu CI, and has been merged over twice — CI is no longer a gate — `High` / `S`
**Where:** `tests/services/test_mfa.py:128` (`monkeypatch.setattr(mfa.sys, "platform", "win32")` inside `TestEnsureMfaServerRunning._calls`), failing at `src/voxkit/services/mfa.py:13`
**What:** `_calls()` fakes `sys.platform = "win32"` to exercise `_ensure_mfa_server_running`, but the production `_no_window()` helper then does `return {"creationflags": subprocess.CREATE_NO_WINDOW}` — an attribute that only exists on the real Windows `subprocess` module. On macOS/Linux both `test_output_is_discarded_not_captured` and `test_enables_postgres_before_starting_the_server` die with `AttributeError: module 'subprocess' has no attribute 'CREATE_NO_WINDOW'`. Verified locally: `2 failed, 322 passed`. Verified in CI: `gh run view 32286788510` shows the **`Run tests` step** (not dependency install) failing on `main`. `Tests (macOS)` and `Tests (Ubuntu)` on `main` are `failure` for `ee37272` (2026-08-11), `#167`, and `#168`; the last green `main` run was `#132` on 2026-05-08. `Tests (Windows)` passes, because there `CREATE_NO_WINDOW` exists.
**Why it's debt:** Two PRs (#167, #168) were merged into `main` while two of three required-looking test workflows were red. Once a workflow is habitually red, nobody reads it, and the next real regression lands silently. The failure is also *in the test*, not the product — so the red is pure noise that trains the team to ignore the signal.
**Fix:** Stop faking the platform through the global `sys` module. Patch the seam instead — `monkeypatch.setattr(mfa, "_no_window", lambda: {"creationflags": 0x08000000})` alongside the platform patch — or have `_no_window()` read `getattr(subprocess, "CREATE_NO_WINDOW", 0)`. Then enable branch protection requiring all three `Tests (*)` workflows before merge to `main`.

#### TS-2. The coverage badge overstates a number that already measures 7% of the codebase, and nothing regenerates or gates it — `High` / `M`
**Where:** `assets/coverage.svg` (`coverage: 82.98%`), `pyproject.toml:138-172` (`[tool.coverage.run] omit`), `tasks.py:255-261` (`generate-coverage-badge`), `.github/workflows/tests-*.yml`
**What:** Three compounding problems. (a) The badge says **82.98%**; running `pytest --cov=voxkit tests/` today gives **TOTAL 70.94%** — 12 points stale, because `invoke generate-coverage-badge` is a manual task no workflow ever calls. (b) The `omit` list removes `gui/**` (12,960 LOC), `services/**` (508), `engines/*_engine.py` (756), and `config/startup_config.py` (160), leaving a denominator of **1,294 statements out of ~17,959** — so "82.98%" (or 70.94%) describes ~7% of the application while reading as a whole-app figure. (c) The `omit` list is now factually wrong about `services/`: `pyproject.toml:156` declares it untestable, yet `tests/services/` holds 27 passing behaviour tests. (d) There is no `fail_under` anywhere in `pyproject.toml`, `tasks.py`, or CI — grep for `fail_under` returns nothing — so coverage can regress to zero without any check firing.
**Why it's debt:** The badge is the only coverage signal anyone sees, and it is both stale and scoped in a way that makes an untested 6,736-LOC pipeline package look irrelevant. Contributors optimising for the badge are steered away from exactly the code that needs tests.
**Fix:** Add a `coverage` step to `tests-ubuntu.yml` (the job that already has Qt/xvfb) running `--cov=voxkit --cov-fail-under=<current>`, and regenerate the badge from that run rather than by hand. Drop `src/voxkit/services/**` from `omit` since it is now tested. Label the badge for what it measures (e.g. "core coverage") or widen the denominator to include `gui/pages/` so the pipeline gap is visible in the number.

#### TS-3. The 6,736-LOC pipeline package — the app's core workflow — is ~93% untested, as is the whole async worker layer — `High` / `L`
**Where:** `src/voxkit/gui/pages/pipeline/` vs `tests/gui/test_base_stacker.py:3` and `tests/gui/test_prediction_stacker_validation.py:11-12`
**What:** Only two of ten pipeline modules are imported by any test. Verified by grep: zero test files mention `viewer_stacker`, `comparison_stacker`, `correct_alignments_stacker`, `pllr_stacker`, `training_stacker`, `transcription_stacker`, or `markdown_stacker` — 5,939 LOC including the three largest files in the entire repository. `tests/gui/test_prediction_stacker_validation.py` covers only the three early-return guards in `on_predict_alignments` (it builds the stacker via `PredictionStacker.__new__` at line 32 and sets `stacker.worker = None` at line 42 precisely so the real work never runs). The same holds for `gui/workers/`: `worker_thread.py` (36 LOC) is properly tested with `qtbot.waitSignal`, but `startup.py` (171), `datasets_thread.py` (91) and `models_thread.py` (68) — the threads that actually drive alignment, training and first-launch model downloads — have zero tests. `config/startup_config.py` (160) likewise.
**Why it's debt:** This is where alignment correction, TextGrid viewing and comparison plotting live — the features clinicians actually use, and the ones with the most state (`correct_alignments_stacker.py` mutates alignment data on disk). A regression here is invisible until a researcher hits it. The `omit` list means it does not even register as missing coverage.
**Fix:** Do not chase line coverage on 6.7k LOC of Qt. Pick the non-widget seams and test those: the TextGrid tier-ordering and boundary-edit logic in `viewer_stacker.py` / `correct_alignments_stacker.py`, the comparison metric computation in `comparison_stacker.py`, and the signal contracts of `datasets_thread.py` / `models_thread.py` via `qtbot.waitSignal` (the pattern `test_worker_thread.py` already demonstrates works well). Extracting those into pure functions first will make them testable and is worth doing regardless.

#### TS-4. Test isolation hinges on a CWD-relative directory that is not gitignored; one leftover copy errors out all 114 storage tests — `High` / `M`
**Where:** `tests/storage/test_setup.py:9-23`
**What:**
```python
def activate_test_environment(storage_root, engine_ids=ENGINE_IDS) -> None:
    for engine_id in engine_ids:
        (storage_root / engine_id / MODELS_ROOT).mkdir(parents=True, exist_ok=False)

def deactivate_test_environment(storage_root) -> None:
    if storage_root.exists():
        shutil.rmtree(storage_root)

def mock_get_storage_root():
    return Path("./temp_test_storage_models")
```
Three problems in 15 lines. (a) The root is a **relative** path resolved against the pytest process CWD, and all four storage test modules share the same name — so `pytest-xdist` or any parallel run has them `rmtree` each other's data mid-test. (b) `exist_ok=False` means a single leftover directory poisons every subsequent run. Verified: creating `temp_test_storage_models/ENGINE_A/train` and re-running `tests/storage/test_utils.py` produces `FileExistsError: [Errno 17] File exists` on every test. Any hard interrupt, OOM, or crash between the `activate` and the fixture teardown leaves exactly that state. (c) `temp_test_storage_models` is absent from `.gitignore` (which covers `.coverage`, `htmlcov/`, `coverage.xml` but not this), so the residue also shows up as untracked files in `git status`. Compounding it, `tests/storage/test_datasets.py:71-74` computes `valid_dataset_path` and friends as **module-level constants at import time**, binding collection itself to the CWD.
**Why it's debt:** Recovery requires knowing to `rm -rf temp_test_storage_models` from whatever directory pytest was last run in — a folklore step. It also permanently forecloses parallelising the suite.
**Fix:** Replace `mock_get_storage_root()` with pytest's own `tmp_path` (function-scoped, absolute, unique, auto-cleaned) exposed through a `tests/storage/conftest.py` fixture — which also resolves TS-8. Move the module-level path constants into that fixture.

#### TS-5. A GUI test writes into the developer's real `~/.voxkit` and never cleans up — `Medium` / `S`
**Where:** `tests/gui/test_settings_modal_tooltips.py:18` (`store_file="test_tooltips_settings.json"`), landing via `src/voxkit/gui/frameworks/settings_modal/generic.py:77` and `:105-109`
**What:** `_build_dialog` constructs a real `GenericDialog`, whose `__init__` sets `self.store_values_path = Path(get_storage_root() / config.store_file)` and then calls `_save_defaults()`, which does `save_json(self.store_values_path, defaults)` and prints `Default settings saved to …`. The test never patches `get_storage_root`, so the path is the real `~/.voxkit`. Verified empirically: diffing `ls ~/.voxkit` before and after a full run shows a new `test_tooltips_settings.json`, and nothing removes it. Every other test in the repo that touches storage patches the root; this one is the outlier.
**Why it's debt:** Test runs mutate real user state — mild here, but the same `GenericDialog` path is how engine settings are persisted, so the pattern one copy-paste away writes into live `MFAENGINE`/`W2TGENGINE` config. It also makes the test non-hermetic: a pre-existing file with different contents changes the `_save_defaults` branch taken.
**Fix:** `monkeypatch.setattr("voxkit.gui.frameworks.settings_modal.generic.get_storage_root", lambda: tmp_path)` in `_build_dialog`. Better, add a session-wide autouse fixture in a root `conftest.py` (TS-6) that redirects `voxkit.storage.utils.get_storage_root` to a tmp dir so no test can reach real `~/.voxkit` by accident.

#### TS-6. There is no pytest configuration and no root `conftest.py` at all — `Medium` / `S`
**Where:** `pyproject.toml` (no `[tool.pytest.ini_options]` section exists — verified by grep, and there is no `pytest.ini`, `setup.cfg`, or `tox.ini`); the only `conftest.py` in the repo is `tests/gui/conftest.py`
**What:** No `testpaths`, no `addopts`, no `--strict-markers`, no `filterwarnings`, no `asyncio_mode`. Consequences: (a) `pytest-asyncio>=1.3.0` is declared in `pyproject.toml:41` and AGENTS.md:83 states async tests use it, but the suite contains **zero** `async def` tests and zero `asyncio` references — it is a dead dependency backing a documented-but-nonexistent capability. (b) No markers are defined and none are used (`grep '@pytest.mark' tests/` returns nothing), so there is no way to run a fast subset or to quarantine platform-specific tests — which is precisely what TS-1 needs. (c) With no root `conftest.py`, cross-cutting concerns (storage-root redirection, `~/.voxkit` protection, Qt offscreen platform) have nowhere to live, which is why they are hand-rolled per directory or omitted entirely.
**Why it's debt:** Every future test author re-decides these questions. It is also why TS-4 and TS-5 exist as separate problems rather than being solved once.
**Fix:** Add `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, `addopts = "--strict-markers -ra"`, and markers for `windows_only`/`slow`. Add a root `tests/conftest.py` holding the storage-root redirection fixture. Drop `pytest-asyncio` or write the async tests AGENTS.md promises.

#### TS-7. `test_models_page.py` asserts entirely on a `MagicMock` passed as `self` — it cannot detect a broken widget — `Medium` / `M`
**Where:** `tests/gui/test_models_page.py:9-13` and `:31`
**What:**
```python
def _make_widget(self, engines):
    widget = MagicMock()
    widget.get_engines.return_value = engines
    return widget
...
ManageAlignersWidget.reload_models(widget)   # unbound method, MagicMock as self
widget.set_items.assert_has_calls([...])
```
`ManageAlignersWidget` is never constructed; no Qt object exists. All three tests call the unbound method with a mock standing in for `self`, then assert on `set_items` call records. There is exactly one real `assert` in the whole 65-line file (`assert widget.set_items.call_count == len(engines)`); the rest are `assert_has_calls` / `assert_not_called` / `assert_called_once_with` on the mock. If `set_items` were renamed, given a different signature, or made to throw on real data, all three tests still pass.
**Why it's debt:** It reads as coverage of the models page (and is the *only* test file for a 692-LOC package) while verifying nothing about the widget. Contrast `tests/gui/test_datasets_page.py`, which builds a real `DatasetsPage` under `qtbot` and asserts on actual `QTableWidgetItem` text — that file would catch a regression; this one would not.
**Fix:** Build a real `ManageAlignersWidget` under `qtbot` with `models.list_models` patched (the pattern `tests/gui/test_datasets_page.py:12-17` already uses), then assert on the resulting table/list contents rather than on call records.

#### TS-8. The same storage setup is copy-pasted 85 times, with duplicated fixture bodies, 12 dead parameters, and 3 unused conftest fixtures — `Medium` / `M`
**Where:** `tests/storage/*.py` (all four), `tests/gui/conftest.py:9-37`
**What:** Four separate smells, one root cause — no `tests/storage/conftest.py`.
- `monkeypatch.setattr(<module>, "get_storage_root", mock_get_storage_root)` appears **85 times**: 31× in `test_models.py`, 27× in `test_datasets.py`, 20× in `test_alignments.py`, 7× in `test_utils.py`. It is the first line of nearly every test body.
- `generate_fake_datasets()` is defined twice with near-identical bodies — `tests/storage/test_datasets.py:16-56` and `tests/storage/test_alignments.py:13-30` — differing only in participant/sample counts.
- Which module gets patched is inconsistent and partly cargo-cult: `tests/storage/test_alignments.py:94` patches `models.get_storage_root`, `:142` patches `datasets.get_storage_root`, and `test_delete_alignment_success` at `:567` patches nothing at all, silently relying on the patches its `sample_dataset`/`sample_model` fixtures happened to apply to the shared function-scoped `monkeypatch`. (`src/voxkit/storage/alignments.py` never imports `get_storage_root` — verified — so patching it there would be a no-op anyway.) The result is that no reader can tell which tests are actually isolated.
- 12 tests declare `monkeypatch` and never touch it: `tests/storage/test_datasets.py:801,810,822,830,843,856,870,878,896,913` and `tests/storage/test_alignments.py:475,557`.
- Three of the six fixtures in `tests/gui/conftest.py` are consumed by **zero** tests — `app_config` (:9), `pipeline_config` (:21), `pipeline_config_with_steps` (:27). (The two `app_config` grep hits in `test_feedback.py:21,37` are attribute assignments on a `SimpleNamespace`, not fixture requests.) That is 30 of 67 conftest lines, including the only reference anywhere to `MarkdownStacker`.
**Why it's debt:** Changing how storage is rooted means editing 85 call sites. The inconsistency actively hides which tests are hermetic. The dead fixtures mislead the next author into thinking a config-driven GUI test harness exists.
**Fix:** One `tests/storage/conftest.py` with an autouse fixture that redirects the storage root (per TS-4, onto `tmp_path`) and a shared `fake_dataset_tree` fixture. Delete the 12 dead `monkeypatch` params and the 3 unused GUI fixtures.

#### TS-11. A cluster of tests assert only that a call did not raise — `Medium` / `M`
**Where:** `tests/analyzers/test_default_analyzer.py:147-197`, `tests/gui/test_base_stacker.py:73-78` and `:90-96`, `tests/config/test_app_config.py:145-157`, `tests/config/test_app_config.py:93-111`
**What:**
- `TestDefaultAnalyzerVisualize` has **seven consecutive tests** whose entire assertion is `assert widget is not None` (`:150, 159, 165, 174, 183, 191, 197`) — including the interesting ones, `test_visualize_handles_missing_keys` and `test_visualize_handles_invalid_count`, which set up malformed input and then verify only that a widget object came back. `visualize()` cannot return `None`, so these are tautologies wrapped around smoke tests. Only the eighth (`test_visualize_widget_has_scroll_area`, `:199`) checks anything structural.
- `tests/gui/test_base_stacker.py:73` `test_no_title_skips_header` is named for header suppression but asserts `stacker.status_label is not None` — it never checks that the header is absent. `:90` `test_reload_calls_both` is named for two calls but its body is `stacker.reload()` with a comment saying "just verify reload() doesn't raise" and no assertion at all.
- `tests/config/test_app_config.py:145-157` asserts `config.app_name is not None` / `config.version is not None` against the real project config — true for any non-crashing load.
- `test_from_yaml_with_defaults` (`:93`) merges two unrelated tests: default-value checks and a `FileNotFoundError` case bolted on at `:106-111`, so a failure in the first half masks the second. `test_dataclass_fields` (`:39`) similarly constructs two different `AppConfig`s in one test.
**Why it's debt:** These are the tests most likely to be cited as "the analyzer visualiser is tested" while being incapable of catching a rendering regression — the exact false-confidence failure mode. They also cost real time: the `TestDefaultAnalyzerVisualize` setup is the second-slowest item in the suite at 0.51s.
**Fix:** For `visualize`, assert on rendered content the way `tests/gui/test_column_dropdown.py:56-64` does (row counts, label text, bar counts) rather than on non-`None`. Make `test_no_title_skips_header` assert the header widget is absent, and either give `test_reload_calls_both` its two spies or delete it. Split the two merged `app_config` tests.

#### TS-9. `tests/storage/test_setup.py` is a helper module named as a test module — `Low` / `S`
**Where:** `tests/storage/test_setup.py` (23 LOC, **0 test functions, 0 asserts**)
**What:** It contains only `ENGINE_IDS`, `activate_test_environment`, `deactivate_test_environment`, `mock_get_storage_root`, and is imported by the other three storage modules via relative import (`from .test_setup import …`). pytest collects it as a test module and finds nothing, and its `test_` prefix is why `tests/storage/__init__.py` must exist for the relative imports to resolve.
**Why it's debt:** It shows up in `--collect-only` output and file listings as a test module, inflating the apparent test surface, and it invites `pytest tests/storage/test_setup.py` runs that report "no tests ran" as if something were broken.
**Fix:** Rename to `tests/storage/conftest.py` (folding in TS-8) or `tests/storage/_helpers.py`.

#### TS-10. `TestGetAlignmentType` is defined twice in the same file with overlapping tests — `Low` / `S`
**Where:** `tests/storage/test_alignments.py:415` (nested inside `class TestAlignments`) and `tests/storage/test_alignments.py:830` (module level)
**What:** The nested class has `test_returns_stored_alignment_type`, `test_infers_hand_from_engine_id_when_field_missing`, `test_infers_corrected_from_engine_id_when_field_missing`, `test_defaults_to_automatic_when_field_missing`. The module-level class re-tests three of those four under different names — `test_returns_recorded_type`, `test_infers_hand_from_legacy_sentinel`, `test_defaults_to_automatic_for_legacy_data` — with the same assertions against the same `get_alignment_type` function, differing only in whether `engine_id` is `"mfa"` or `"MFAENGINE"`.
**Why it's debt:** A future change to `get_alignment_type` semantics must be reconciled against two independent specifications of it in one file, and identically-named classes make failure output ambiguous.
**Fix:** Delete the module-level duplicate at `:830-851`, keeping only the `corrected`-sentinel case the nested class covers and the outer one does not.

### Cross-module notes

- **`pyproject.toml:112` references a file that no longer exists.** The ruff per-file-ignore `"src/voxkit/gui/pages/pipeline/evaluation_stacker.py" = ["S603", "S607"]` points at a path absent from the tree — a stale rule that silently does nothing. Belongs to whoever owns build/lint config.
- **`src/voxkit/services/mfa.py:13** `_no_window()` unconditionally dereferences `subprocess.CREATE_NO_WINDOW` when `sys.platform == "win32"`. That is correct in production but makes the function untestable from any other OS, which is the direct cause of TS-1. A `getattr(subprocess, "CREATE_NO_WINDOW", 0)` would fix the testability without changing Windows behaviour — a production-side change, flagged for the services auditor.
- **AGENTS.md:103** already notes that `_ensure_mfa_server_running` "deliberately ignores return codes, which hides both failures". `tests/services/test_mfa.py:115-172` tests the *shape* of the calls (no piping, correct order) but nothing asserts on return-code handling — the suite documents the known bug's symptoms without covering the fix. Flagged for whoever owns `services/`.
- **`assets/coverage.svg` is committed but referenced by no README, docs page, or workflow** (only `tasks.py:260` writes it and `AGENTS.md:60` mentions the task). If nothing actually displays it, the simplest resolution of TS-2(a) is deleting it rather than automating it.
