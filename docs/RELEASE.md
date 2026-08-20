# Releasing VoxKit

This covers the whole deployment path for a VoxKit release, and doubles as a
reference document for agents in the loop; i.e. how a version of this code is
promoted to become the newest version source of truth. We use GitHub releases
to host new versions/deployments of the app.

## Table of Contents

- [What a release is](#what-a-release-is)
- [Versioning and tag conventions](#versioning-and-tag-conventions)
- [Step 1 — Bump the version](#step-1--bump-the-version)
- [Step 2 — Build the artifact](#step-2--build-the-artifact)
- [Step 3 — Smoke-test](#step-3--smoke-test)
- [Step 4 — Tag the release commit](#step-4--tag-the-release-commit)
- [Step 5 — Create the GitHub release](#step-5--create-the-github-release)
- [Step 6 — Upload the artifact and verify](#step-6--upload-the-artifact-and-verify)
- [How a release reaches the website](#how-a-release-reaches-the-website)
- [Release notes template](#release-notes-template)

---

## What a release is

A release is a snapshot of the app hosted on GitHub, a tagged commit plus the
distributable assets built from it. See [GitHub releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) for more context.

It boils down to three things:

1. **A tagged version**:

   ```bash
   git tag v0.5.1 && git push origin v0.5.1
   ```

2. **A release attached to that tag**:

   ```bash
   gh release create v0.5.1 --title v0.5.1 --notes-file notes.md
   ```

3. **The distributable assets attached to that release**:

   ```bash
   gh release upload v0.5.1 installer/windows/output/VoxKit-setup.exe
   ```

Feature work lands on develop; a sprint reaches users by squash merging `develop`
into `main`, with the [main_merge](../.github/PULL_REQUEST_TEMPLATE/main_merge.md) PR template. Releases are always cut from `main`.

---

## Versioning and tag conventions

Pre-1.0.0 releases are early previews. Versioning is semver-shaped:
patch for fixes, minor for features, and `1.0.0` reserved for the first
non-preview release.

`config/VERSION` is the single source of truth.

| Consumer | How it reads the version |
|---|---|
| `pyproject.toml` | `[tool.setuptools.dynamic] version = {file = ["config/VERSION"]}` |
| `src/voxkit/__init__.py` | `__version__`, read at import (handles PyInstaller `_MEIPASS`) |
| `AppConfig.from_yaml` | Overrides any YAML `version:` with this file |
| `installer/windows/VoxKit.iss` | Read via ISPP at installer **compile** time |

> [!NOTE]
> Because the installer reads the file at compile time, the version bump has to
> be committed *before* you build.

**Tags** are `vX.Y.Z` (`v0.4.1`, `v0.5.0`). The older
`vX.Y.Z-macos-VoxKit` form (through `v0.4.0-macos-VoxKit`) is historical, from
when macOS was the only target; do not use it for new releases. The GitHub
release title matches the tag exactly (`v0.5.0`), and releases are published
normally, not as drafts, not flagged as prereleases.

**Artifact names** are stable across releases, because users follow
step-by-step instructions that name the file:

| Platform | Release asset name |
|---|---|
| Windows | `VoxKit-setup.exe` |
| macOS | `VoxKit-macOS.dmg` |
| Linux | `VoxKit-x86_64.AppImage`

---

## Step 1 — Bump the version

On a branch off `main` (or as part of the `develop` → `main` release PR):

```bash
# e.g. 0.5.0 -> 0.5.1
echo "0.5.1" > config/VERSION
```

Commit it and get it onto `main`. Everything downstream (aside from the tag) 
hangs off this value.

---

## Step 2 — Build the artifact

All build tasks run `invoke clean` first, so each build starts from an empty
`build/` and `dist/`. Build from a checkout of the tagged `main` commit, with
no uncommitted changes.

See [BUILD.md](./BUILD.md) for what goes into the bundle (the vendored micromamba 
binary, the pinned MFA environment lockfile, and the MSVC runtime DLLs 
that ship beside it on Windows).

### Windows (`VoxKit-setup.exe`)

Two stages: PyInstaller produces the executable, then Inno Setup wraps it in
an installer.

```powershell
# 1. PyInstaller onefile, windowed -> dist\VoxKit.exe
invoke windows-build

# 2. Compile the installer. VoxKit.iss reads config\VERSION for AppVersion and
#    pulls in ..\..\dist\VoxKit.exe, so it must run after the build.
#    Equivalent to opening installer\windows\VoxKit.iss in the Inno Setup GUI
#    and choosing Build -> Compile.
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\windows\VoxKit.iss
```

### macOS (`VoxKit-macOS.dmg`)

```bash
# 1. PyInstaller onedir + BUNDLE -> dist/VoxKit.app (and dist/VoxKit/)
invoke macos-build

# 2. Wrap the bundle in a compressed disk image.
mkdir -p dmg_contents
cp -R dist/VoxKit.app dmg_contents/
hdiutil create -volname "VoxKit" -srcfolder dmg_contents -ov \
    -format UDZO VoxKit-macOS.dmg
```

### Linux (AppImage)

```bash
invoke linux-build   # -> dist/VoxKit-x86_64.AppImage
```

---

## Step 3 — Smoke-test

Smoke-test the app or installer on a machine that is not the build machine before
publishing: install it, launch from the Start menu, and let first-run MFA
provisioning finish. The frozen build exercises code paths a dev run never
touches.

---

## Step 4 — Tag the release commit

Tag the `main` commit that carries the bumped `config/VERSION`:

```bash
git checkout main
git pull origin main
git tag v0.5.1
git push origin v0.5.1
```

---

## Step 5 — Create the GitHub release

Either the GitHub UI (Releases → Draft a new release → pick the existing
tag) or the CLI:

```bash
gh release create v0.5.1 --title v0.5.1 --notes-file notes.md
```

---

## Step 6 — Upload the artifact and verify

```bash
gh release upload v0.5.1 installer/windows/output/VoxKit-setup.exe
```

Then check, in this order:

- [ ] The asset is attached under the **exact** name the installation steps
      tell users to download (`VoxKit-setup.exe` / `VoxKit-macOS.dmg` / `VoxKit-x86_64.AppImage`)
- [ ] The release is published. Drafts are invisible to the website 
      and to `gh release list` consumers.
- [ ] The tag on the release is the one you pushed, pointing at the intended
      `main` commit.
- [ ] Download the asset from the release page (not your local build) and
      install it once. This catches a truncated upload and, on macOS, confirms
      the quarantine instructions still match reality.

---

## How a release reaches the website

The download page on the VoxKit site ([`BrainBehaviorAnalyticsLab/voxkit-web`](https://github.com/BrainBehaviorAnalyticsLab/voxkit-web),
deployed on Vercel) is generated from the GitHub releases API so nothing is
published to the site by hand. `lib/releases.ts` fetches
`https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/releases` during
server render and reduces it to one "latest" entry per operating system.

---

## Release notes template

Keep the shape; drop sections that do not apply.

````markdown
> [!NOTE]
> Any caveat that applies to this release as a whole — a platform that is not
> shipping this time, a known issue with a link to its tracking issue.

## Installation

### Windows
1. Download VoxKit-setup.exe
2. Run the installer and follow the prompts
3. Launch VoxKit from the Start menu; the startup script will download some
   assets like models and initialize the local storage on the first open
   (be patient please)
```powershell
# FYI deleting local storage will trigger a fresh startup the next time the app is opened
Remove-Item -Recurse -Force $env:USERPROFILE\.voxkit
```

## System Requirements
- Windows 10/11 (x64)
- Montreal Forced Aligner is bundled and provisioned on first launch; no
  separate Conda install required

## Changes
### Improvements
  - <User-visible change> (#PR)

### Fixes
  - <User-visible fix> (#PR)

**Full Changelog**: https://github.com/BrainBehaviorAnalyticsLab/voxkit-desktop/compare/v0.5.0...v0.5.1

## Contributors
* @handle
````