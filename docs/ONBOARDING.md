# Taking Over VoxKit

This is a handover document. It assumes you are inheriting VoxKit from someone
who is leaving, and that you have not seen the codebase before.

The other docs in this folder tell you *how* things work
([ARCHITECTURE](./ARCHITECTURE.md), [BUILD](./BUILD.md), [RELEASE](./RELEASE.md)).
This one tells you what you have actually been handed, what state it is in, what
will bite you, and what to do in your first week.

Everything factual here was verified against the repository on **2026-08-24**,
at version **0.5.0** (`main` @ `93dfc1e`). Where something is likely to drift,
it says so.

## Table of Contents

- [1. What VoxKit is](#1-what-voxkit-is)
- [2. Day one — get it running](#2-day-one--get-it-running)
- [3. What you now own](#3-what-you-now-own)
- [4. The mental model](#4-the-mental-model)
- [5. What the product actually does](#5-what-the-product-actually-does)
- [6. Your first week](#6-your-first-week)
- [7. Things that will bite you](#7-things-that-will-bite-you)
- [8. Current state of play](#8-current-state-of-play)
- [9. Making a change](#9-making-a-change)
- [10. Shipping a release](#10-shipping-a-release)
- [11. Handover checklist](#11-handover-checklist)
- [12. If you remember only five things](#12-if-you-remember-only-five-things)

---

## 1. What VoxKit is

VoxKit is a **PyQt6 desktop application for speech-language pathology
research**. It is a graphical front end over a set of command-line speech
toolkits — chiefly the Montreal Forced Aligner (MFA) — so that researchers who
are not comfortable in a terminal can do forced alignment, model training,
transcription, and pronunciation scoring on their own speech datasets.

The product thesis, in one sentence: **the science is not the bottleneck, the
tooling is.** MFA is excellent and largely unusable for the target audience —
it requires conda, a terminal, and a mental model of acoustic models and
dictionaries. VoxKit's job is to make that disappear behind a window with
buttons. Most of the hard-won engineering in this repo is in service of that one
goal, which is why so much of it is about bundling, provisioning, and
subprocess management rather than about speech science.

Users are SLP researchers, phoneticians, grad students, and research assistants.
They are not developers. They install a `.exe`, `.dmg`, or `.AppImage`, and they
expect it to work with no setup. That expectation drives most of the difficult
decisions in [section 7](#7-things-that-will-bite-you).

It is developed under **BrainBehaviorAnalyticsLab** in collaboration with
**WISCLab**. It is MIT-licensed, public, and pre-1.0 — everything shipped so far
is explicitly an early preview.

---

## 2. Day one — get it running

### 2.0 The access blocker — deal with this first

`uv sync` **will fail** without read access to a private repository.

VoxKit depends on `pypllrcomputer`, which resolves to
[`pkadambi/PyPhonemePronunciationScorer`](https://github.com/pkadambi/PyPhonemePronunciationScorer)
(`pyproject.toml:65`). That repo is **private** and is owned neither by
BrainBehaviorAnalyticsLab nor by WISCLab. If you cannot clone it, you cannot
install the project, run the tests, or build the app.

CI works around this with a `PRIVATE_REPO_TOKEN` secret (see any workflow in
`.github/workflows/`). Locally you need your own GitHub credentials to have
access to that repo. **Get this sorted before anything else** — ideally while
the outgoing maintainer is still reachable, since it needs an invitation from
someone outside the lab.

### 2.1 Prerequisites

- **git**
- **[uv](https://docs.astral.sh/uv/)** — the package manager. Not pip, not poetry.
- **[invoke](https://www.pyinvoke.org/)** — the task runner: `uv tool install invoke`
- Python 3.11+ (uv will fetch it; `.python-version` pins the interpreter)

### 2.2 First run

```bash
git clone https://github.com/BrainBehaviorAnalyticsLab/voxkit-desktop.git
cd voxkit-desktop

invoke setup     # uv sync + install pre-commit hooks. Run on every fresh checkout.
invoke dev       # launches the app
invoke --list    # every other command
```

**Use `invoke` tasks, not the underlying tools.** Do not run `pytest`, `ruff`,
`mypy`, or `pyinstaller` directly. `tasks.py` sets flags, paths, and dependency
groups that CI also relies on; bypassing it gives you results that do not match
CI. If a task is missing a flag you need, add the flag to the task rather than
working around it.

### 2.3 What happens on first launch

The first launch is slow and does real work — this is the part users complain
about, so it is worth watching once:

1. `startup_routine()` (`src/voxkit/config/startup_config.py`) downloads two MFA
   acoustic models (English, Spanish), the W2TG model from HuggingFace, and an
   NLTK tagger.
2. `ensure_mfa_environment()` provisions a private conda-style environment
   containing MFA itself, using the vendored micromamba binary and a pinned
   lockfile. This is a **1–2 GB download**, and currently only on Windows —
   `config/mfa-env/` holds `aligner-win-64.lock` and nothing else. On macOS and
   Linux, MFA falls back to a user-supplied conda install (the "Conda Path"
   setting).
3. A flag file `~/.voxkit/.first_launch_complete` marks step 1 as done so it
   never repeats. Step 2 is deliberately *not* gated on that flag — it re-checks
   readiness every launch, so an interrupted download resumes.

### 2.4 Runtime state lives outside the repo

Everything the app creates for a user lives in **`~/.voxkit/`**:

```
~/.voxkit/
├── .first_launch_complete       # flag file
├── datasets/{dataset_id}/       # registered datasets, analyzer CSVs, alignments
├── {ENGINE_ID}/train/{model_id} # per-engine models
├── {ENGINE_ID}/{tool}/*.json    # per-engine tool settings
├── mfa-env/                     # the provisioned MFA environment (Windows)
├── mfa-root/                    # MFA's global config + Postgres data
└── logs/voxkit.log              # rotating log, 5 MB × 3
```

To reset to a virgin install, delete `~/.voxkit`. **Stop the MFA server first on
Windows** — see [section 7.2](#72-mfa-on-windows-is-the-hardest-part-of-this-codebase),
this is not optional and the failure it causes is unrecoverable.

`~/.voxkit/logs/voxkit.log` is your primary debugging tool and the first thing
to ask a user for.

---

## 3. What you now own

VoxKit is not just this repository. The full footprint:

| Thing | Where | Notes |
|---|---|---|
| This app | [`BrainBehaviorAnalyticsLab/voxkit-desktop`](https://github.com/BrainBehaviorAnalyticsLab/voxkit-desktop) | Public, MIT |
| The website + docs host | [`BrainBehaviorAnalyticsLab/voxkit-web`](https://github.com/BrainBehaviorAnalyticsLab/voxkit-web) | Next.js on Vercel. Download page reads the GitHub releases API; API docs are pushed into it by CI |
| Product planning | [Jira (VOX board)](https://voxkit.atlassian.net/jira/software/projects/VOX/boards/2/) | Large features and direction |
| Code planning | [GitHub Projects](https://github.com/orgs/BrainBehaviorAnalyticsLab/projects/1) | Issue triage |
| PHI scanner | [`WISCLab/shred-guard`](https://github.com/WISCLab/shred-guard) | Pre-commit hook; patterns configured in `pyproject.toml` |
| CI secret | `PRIVATE_REPO_TOKEN` | Repo secret. Every workflow needs it. **If it expires, all CI goes red at once.** |

### Forked dependencies — read this twice

Four dependencies are installed from **git branches, not PyPI**
(`pyproject.toml:64-69`):

| Package | Source | Branch | Owner |
|---|---|---|---|
| `pypllrcomputer` | `pkadambi/PyPhonemePronunciationScorer` | `voxkit-windows-variant` | **Private**, outside the lab |
| `wav2textgrid` | `pkadambi/Wav2TextGrid` | `voxkit-windows-variant` | Outside the lab |
| `alignment-comparison-plots` | `WISCLab/alignment-comparison-plots` | `voxkit-windows-variant` | WISCLab |
| `speechbrain` | `BrainBehaviorAnalyticsLab/speechbrain` | `fix/windows-lazy-import-inspect-path` | The lab — a fork of upstream carrying a Windows fix |

Every one of these declares a **branch**, not a `rev` or tag. `uv.lock` does pin
each to an exact commit, so builds are reproducible right up until the lockfile
is regenerated — and `invoke fresh-slate`, the repo's own documented remedy for a
broken environment, deletes `uv.lock`. Running it re-resolves all four against
whatever those branch heads point at that day. (This is finding `RT-5` in
`docs/TECH_DEBT.md`, with a concrete fix: move the SHAs out of `uv.lock` and into
`[tool.uv.sources]` as `rev = "..."`.)

Two of the four repos are outside the lab's control, and one of those is private.
If a branch there is deleted or force-pushed, `uv sync` breaks for everyone
including CI, and the fix is not in this repository.

Treat this as the single largest continuity risk you have inherited. The
`speechbrain` fork has already been moved from a personal account into the org —
do the same for the rest where you can, pin by `rev`, and upstream the Windows
fixes so the forks can eventually be retired. Note that none of the forks records
an upstream PR link or a condition for removal, so nobody currently knows when
they stop being necessary.

---

## 4. The mental model

Read [ARCHITECTURE.md](./ARCHITECTURE.md) for the canonical version. The
short form:

```
src/voxkit/
├── gui/        PyQt6 — pages, components, frameworks, workers   (12,958 LOC)
├── storage/    persistence + CRUD; this is the model layer       (1,977 LOC)
├── engines/    speech-toolkit backends behind an ABC             (1,179 LOC)
├── analyzers/  dataset metadata extractors behind an ABC           (657 LOC)
├── services/   subprocess wrappers around external binaries        (514 LOC)
└── config/     profile-aware YAML config loaders                   (664 LOC)
```

Roughly **18,000 lines**, and **72% of it is GUI**. That ratio is the single
most useful fact about this codebase: most of your time will be spent in Qt, not
in speech processing.

Four things to internalize:

**1. Views talk to storage directly.** There is no controller layer. A page
imports `voxkit.storage.datasets` and calls it. `storage/` *is* the model. This
is a deliberate choice for a small Qt app, not an accident — do not start
introducing controllers without reading `docs/ARCHITECTURE.md` first.

**2. Anything slow runs in a QThread worker** (`gui/workers/`) and communicates
back with `pyqtSignal`. Alignment, training, and transcription all take minutes
to hours; blocking the Qt event loop freezes the window.

**3. Engines and analyzers are plugin-shaped.** Each has an abstract base class
and a singleton manager for discovery. Adding a new alignment backend means
subclassing `AlignmentEngine` (`engines/base.py` — its docstring is a working
tutorial) and registering it in `engines/__init__.py`. There are three today:
`MFAEngine`, `W2TGEngine`, `FasterWhisperEngine`.

**4. The pipeline UI is configured in YAML, not code.** `config/profile.txt`
names an active profile under `config/profiles/<name>/`; today it is
`explanatory`. That profile's `pipeline_definitions.yaml` decides which pipeline
steps exist, their order, their labels, and their entire help text. Changing the
user-facing workflow often means editing YAML, not Python. `config/VERSION` is
the single source of truth for the version number — see AGENTS.md for the full
list of consumers.

---

## 5. What the product actually does

Read `config/profiles/explanatory/pipeline_definitions.yaml` end to end. It is
the best single description of the product that exists, because it is the help
text users actually see. The pipeline:

| Step | Name | What it does |
|---|---|---|
| Ⓐ | Transcribe Audio | `.wav` → `.lab` transcripts, via Faster-Whisper |
| Ⓑ | Train Aligners | Adapt an acoustic model to your speakers/conditions |
| Ⓒ | **Generate Alignments** | The core step: audio + transcript → TextGrid with phoneme boundaries |
| Ⓓ | View Alignments | Inspect a TextGrid file-by-file with audio playback |
| Ⓔ | Compare Alignments | Four diagnostic plots between two alignment runs |
| Ⓕ | Correct Alignments | Hand-drag boundaries; always saves to a *new* alignment |
| Ⓖ | Extract PLLR Scoring | Pronunciation-quality scores → CSV |

The common path is Ⓐ → Ⓒ. Everything else is refinement of that.

Each step is a "stacker" — a self-contained form widget under
`gui/pages/pipeline/`, subclassing `base_stacker.py` and named in the YAML by
class. Three other pages sit outside the pipeline: Datasets (register and
analyze), Models (manage and import), and the pipeline container itself.

---

## 6. Your first week

Concrete, in order. Each step ends with something you can verify.

**Day 1 — Get it running.** Solve the private-repo access problem, then
`invoke setup` and `invoke dev`. Let first-launch provisioning finish completely,
however long it takes. Watch `~/.voxkit/logs/voxkit.log` while it runs.

**Day 2 — Be a user.** Register a small dataset (a handful of `.wav` files in
speaker-named directories), transcribe it (Ⓐ), align it with a pretrained model
(Ⓒ), and view the result (Ⓓ). Do not read any code yet. You need to know what
"working" looks like before you can recognize broken.

**Day 3 — Trace one alignment end to end.** This is the highest-value reading in
the codebase. Follow a single click through:

`gui/pages/pipeline/prediction_stacker.py` → `gui/workers/worker_thread.py` →
`engines/mfa_engine.py` → `services/mfa.py` → the actual `mfa align` subprocess
→ `storage/alignments.py` writing the result.

You will have seen every layer of the architecture in one pass, plus the
subprocess boundary where most real bugs live.

**Day 4 — Read the ugly parts.** In this order:
- `docs/BUILD.md` in full — every paragraph is a bug someone already paid for.
- The "MFA runtime state on Windows" section of `AGENTS.md`.
- `services/mfa.py` — the comments are load-bearing, especially around
  `_ensure_mfa_server_running` and `_mfa_invocation`.

**Day 5 — Ship something small.** Pick a `good first issue`, or one of the
smaller open issues from [section 8](#8-current-state-of-play) — #136 (rename a
table header) is about as small as it gets. Go through the full loop: branch,
change, `invoke lint`/`format`/`mypy-check`/`run-tests`, PR, merge. You want the
mechanics to be boring before you need them under pressure.

**Week 2 — Do a release.** Even a no-op patch bump. Follow
[RELEASE.md](./RELEASE.md) exactly. Releases are entirely manual (see
[section 10](#10-shipping-a-release)); the worst time to discover that is when
users are waiting on a fix.

---

## 7. Things that will bite you

Honest section. None of this is hypothetical — all of it has already cost
someone a day.

### 7.1 The frozen build is a different program

The app is shipped via PyInstaller with `--windowed`. In that build:

- **There is no stdout.** `main.py:16-19` redirects it to `/dev/null` because
  `sys.stdout` is `None` and libraries like tqdm crash on it. Any `print()` in
  shipped code is therefore *discarded exactly where you need it*. Ruff enforces
  this (`T20`) — use `logging` and it lands in `~/.voxkit/logs/voxkit.log`.
- **Paths resolve differently.** Bundled resources live under `sys._MEIPASS`.
  `config/` and `vendor/` are bundled via `--add-data`; anything new you add
  *outside* those directories will not ship.
- **DLL search order changes** on Windows, in a way that broke micromamba
  entirely. See the MSVC runtime section of BUILD.md.
- **Child processes inherit all of the above.**

The practical rule: **a change that touches subprocesses, paths, or bundled
assets is not tested until you have run it from `dist/`.** Dev runs cannot
reproduce these failures.

### 7.2 MFA on Windows is the hardest part of this codebase

Disproportionate difficulty concentrates here, and the symptoms are opaque —
most of it surfaces to the user as `MFA alignment failed (exit 1)`.

Two failure modes are environmental rather than code bugs, and are documented in
full in `AGENTS.md`:

- **A half-deleted Postgres data directory deadlocks alignment permanently.**
  `mfa server start` spawns a *detached* Postgres that outlives the app. If you
  delete `~/.voxkit` while it is running, you strip the contents of
  `mfa-root/pg_mfa_global/` but cannot unlink the directory itself. MFA keys both
  `server init` and `server start` off directory *existence*, so it lands in a
  state its own CLI cannot recover from. **Always stop the server before cleaning
  `~/.voxkit` by hand.**
- **Windows Developer Mode changes MFA's code path**, because `os.symlink`
  succeeding unprivileged skips a fallback that MFA relies on. Your dev machine
  may never execute a branch that every user hits.

And one code-level trap: **never capture the output of `mfa server init`/
`start`.** `pg_ctl` takes ownership of whatever stdout/stderr handles it is
given and holds them as long as the server runs; with `capture_output=True` the
pipes never reach EOF and the app freezes permanently. A `timeout=` does not
save you — on Windows `subprocess.run` handles `TimeoutExpired` by calling
`communicate()` again with no timeout. This is why `_ensure_mfa_server_running`
passes `DEVNULL`, and why there are regression tests guarding it.

### 7.3 Failure is silent by default

The dominant error idiom in this codebase is `except Exception` → log → return a
falsy value. There are ~58 such handlers, 22 in `storage/` alone. Combined with
§7.1, a permission error, a 404, a corrupt JSON file, and a genuine bug can all
present to the user as the same empty list.

When you are handed a vague bug report, assume the real error was swallowed
somewhere and go looking for it. When you write new code, prefer surfacing the
failure.

### 7.4 The safety nets are narrower than they look

- **Coverage measures ~7% of the app.** `[tool.coverage.run] omit` in
  `pyproject.toml` excludes all of `gui/`, all of `services/`, and every engine
  implementation — that is, everything hard. The coverage badge is accurate about
  a small denominator, not about the application.
- **mypy has `check_untyped_defs = false`**, so it does not analyse the body of
  any unannotated function — roughly half of them, skewed toward the largest.
- A green CI run means "the typed, non-GUI 7% is fine." Manual testing is not
  optional here.

### 7.5 Two tests are red on macOS and Linux — and it is the test's fault

Verified on 2026-08-24: **322 pass, 2 fail.**

```
FAILED tests/services/test_mfa.py::TestEnsureMfaServerRunning::test_output_is_discarded_not_captured
FAILED tests/services/test_mfa.py::TestEnsureMfaServerRunning::test_enables_postgres_before_starting_the_server
```

Cause: both tests monkeypatch `mfa.sys.platform` to `"win32"`
(`tests/services/test_mfa.py:128`) to exercise the Windows-only branch. That
branch reaches `_no_window()` (`src/voxkit/services/mfa.py:16`), which reads
`subprocess.CREATE_NO_WINDOW` — a constant that **only exists on Windows**. So
the tests raise `AttributeError` on macOS and Linux, and pass on Windows CI.

The product is fine. The test is platform-dependent in a way it did not intend.
The fix is one line either way — `getattr(subprocess, "CREATE_NO_WINDOW", 0)` in
`_no_window()`, or monkeypatch the constant alongside the platform in the test.

**Fix this in your first week.** Not because two failures matter, but because a
permanently-red suite trains everyone to ignore the signal, and PRs have already
been merged over it.

### 7.6 The branching model has drifted

`CONTRIBUTING.md` and `RELEASE.md` describe: feature work → `develop`, then
squash-merge `develop` → `main` per sprint.

That is not what has been happening. `develop` was last updated **2026-07-30**;
every PR merged since #162 (2026-07-30) has targeted `main` directly, so `develop`
is now missing roughly a month of work. Merging it as-is would revert ~2,600 lines
that only exist on `main`.

Neither model is wrong, but pick one and make the docs match. If you keep
`develop`, it needs resetting to `main` first — it is stale enough that merging
it now would revert work.

---

## 8. Current state of play

**Version 0.5.0.** Pre-1.0, explicitly an early preview. The app is in real use
by researchers, so treat regressions as real.

**Tests:** 324 total, 322 passing. See §7.5 for the 2 failures.

**Open PRs (2):**
- #169 — Ship another application icon in packaged builds
- #166 — Gray out Train Aligners until a dataset has manual alignments

**Open issues (20).** They cluster into four groups:
- *Fresh, user-facing:* #174 (startup popup shimmers), #171 (Windows taskbar
  button, not reproduced), #164 (Developer Mode breakage on Windows — see §7.2)
- *Config and data hygiene:* #165 (profile configs out of sync), #120, #136, #127
- *UI refactors, long-standing:* #119 (restructure the Stacker pattern), #118,
  #117, #111, #115, #114, #113 — mostly from April, mostly deferred
- *Project-level decisions:* #124 (**switch MIT → GPL** — a licensing decision
  that needs a human owner), #116 (publish to PyPI), #66 (HuggingFace integration)

**Technical debt:** `docs/TECH_DEBT.md` is a 171-finding audit from 2026-08-19
(45 High, 93 Medium, 33 Low), every finding cited to `file:line`. It is long, but
its executive summary and "Cross-cutting themes" sections are the fastest way to
understand what is structurally weak. Its "Priority: quick wins" section is a
ready-made backlog. Note that some findings are already fixed and marked in
place — verify before acting on any individual item.

**Citation:** the README's BibTeX block is still `<TODO>`. If this gets used in
published research — which is the entire point — someone needs to fill it in.

---

## 9. Making a change

```bash
git switch -c fix/short-description

# ... edit ...

invoke format          # ruff format
invoke lint            # ruff check --fix
invoke mypy-check      # types
invoke run-tests       # unit + GUI (pytest-qt)
invoke dev             # and then actually click the thing you changed
```

Pre-commit runs shredguard, ruff, ruff-format, mypy, and whitespace hooks on
commit. **shredguard is a PHI scanner** — patterns are in `pyproject.toml`
(`[[tool.shredguard.patterns]]`), currently phone numbers and patient IDs of the
form `123_M_`. This is a clinical-data project; do not disable it, and never
commit a real dataset path or participant identifier.

CI runs tests on Ubuntu, macOS, and Windows plus a lint/format/mypy job. All four
need `PRIVATE_REPO_TOKEN` to install dependencies.

Where to put tests: business logic in `storage/`, `config/`, and `analyzers/`
is straightforwardly testable and should be tested. GUI is testable with
`pytest-qt` where it is worth it (see `tests/gui/`) but is excluded from coverage
metrics. Engines and services wrap external binaries and are largely untested by
design — which is exactly why manual verification matters there.

For agent-assisted work, `AGENTS.md` is the entry point and is kept accurate;
`.github/agents/` holds several task-specific agent definitions.

---

## 10. Shipping a release

Read [RELEASE.md](./RELEASE.md) before your first one. The critical fact:

> **Nothing is automated.** There is no tag-triggered build. A `release.yml`
> workflow existed and was deliberately removed in #96. Pushing a tag builds
> nothing and uploads nothing.

You build every artifact by hand, on a machine of that platform:

| Platform | Artifact | Needs |
|---|---|---|
| Windows | `VoxKit-setup.exe` | Windows + Inno Setup 6 |
| macOS | `VoxKit-macOS.dmg` | a Mac (`hdiutil`) |
| Linux | `VoxKit-x86_64.AppImage` | Linux |

So **cross-platform releases require access to all three platforms.** If you
only have one, know now which platforms you can and cannot ship — and say so in
the release notes rather than shipping a stale artifact.

The flow is: bump `config/VERSION` → commit to `main` → build → smoke-test on a
machine that is *not* the build machine → tag `vX.Y.Z` → `gh release create` →
upload assets under their exact expected filenames. Asset names are load-bearing:
the install instructions name the file, and the website's download page is
generated from the GitHub releases API.

The docs on the website are pushed automatically — `sync-docs.yml` runs pdoc on
every push to `main` and commits the HTML into `voxkit-web`.

---

## 11. Handover checklist

Things to confirm you actually have, ideally while the outgoing maintainer is
still reachable. Access is the part that cannot be reverse-engineered from the
code.

- [ ] Write access to `voxkit-desktop`
- [ ] Write access to `voxkit-web` (the website and hosted docs)
- [ ] **Read access to `pkadambi/PyPhonemePronunciationScorer`** — private, outside the lab, and a hard blocker on `uv sync`
- [ ] A documented owner for each of the four forked dependencies, and — for the two `pkadambi/*` repos — a named contact who can restore a branch if one disappears
- [ ] The `PRIVATE_REPO_TOKEN` CI secret: who owns it, when it expires, how to rotate it
- [ ] Vercel access for the website deployment
- [ ] Jira access (VOX board) and the GitHub Project board
- [ ] Admin on the GitHub org, or a named person who has it
- [ ] The support email in `config/profiles/*/app_info.yaml` — it currently points at the outgoing maintainer's personal address (`code@beckettfrey.com`), and it is what the in-app Feedback button opens. **Change this.**
- [ ] Any signing identity or notarization credentials, if macOS builds ever move beyond ad-hoc signing
- [ ] A named research contact — the person who can answer "is this alignment output *correct*", which is not a question the code can answer
- [ ] A walkthrough of anything in `docs/TECH_DEBT.md` marked High that is currently in flight

---

## 12. If you remember only five things

1. **`~/.voxkit/logs/voxkit.log` is your debugger.** `print()` is discarded in
   shipped builds. Always ask a user for the log first.
2. **The frozen build is a different program from the dev build.** Subprocess,
   path, or bundling changes are untested until run from `dist/`.
3. **Green CI covers about 7% of the app and none of the GUI.** Click the thing
   you changed.
4. **Four dependencies track git branches rather than pinned revisions, two of
   them in repos the lab does not control and one of those private.** This is
   your biggest continuity risk. Address it early.
5. **The users are researchers, not developers.** Every architectural
   complication in this repo — the bundled MFA environment, the vendored
   micromamba, the YAML-configured help text — exists so that they never have to
   open a terminal. Preserve that, and the rest is negotiable.
