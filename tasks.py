"""Invoke task definitions for VoxKit. Run with `invoke <task>` or `invoke --list`."""

import shutil
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

from invoke import task

BLUE = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

ROOT = Path(__file__).parent


def _log(msg: str, color: str = BLUE) -> None:
    print(f"{color}{msg}{RESET}")


def _rmtree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


@task
def setup(c):
    """Install dependencies and setup pre-commit hooks."""
    _log("Installing dependencies with uv sync...")
    c.run("uv sync")
    _log("Installing pre-commit hooks...")
    c.run("uv run pre-commit install")
    _log("Setup completed successfully!", GREEN)


@task
def dev(c):
    """Run the development server."""
    _log("Starting development server...")
    c.run("uv run main.py", pty=sys.platform != "win32")


@task
def watch(c):
    """Watch for file changes and restart dev server (requires entr on Unix)."""
    if sys.platform == "win32":
        _log("watch is not supported on Windows (requires entr). Falling back to dev.", YELLOW)
        c.run("uv run main.py")
        return
    if not shutil.which("entr"):
        _log("entr not installed. Install with: brew install entr (macOS) or apt install entr", RED)
        _log("Falling back to single run...", YELLOW)
        c.run("uv run main.py", pty=True)
        return
    _log("Watching for changes... Press Ctrl+C to stop")
    files = [str(p) for p in (ROOT / "src").rglob("*.py")]
    if not files:
        _log("No Python files found under src/", RED)
        return
    subprocess.run(  # noqa: S603
        ["entr", "-r", "uv", "run", "main.py"],  # noqa: S607
        input="\n".join(files),
        text=True,
        check=False,
    )


@task
def clean(c):
    """Clean build artifacts."""
    _log("Cleaning build artifacts...")
    for name in ("build", "dist"):
        _rmtree(ROOT / name)
    for spec in ROOT.glob("*.spec"):
        spec.unlink(missing_ok=True)
    for pycache in ROOT.rglob("__pycache__"):
        if ".venv" in pycache.parts:
            continue
        _rmtree(pycache)
    for pyc in ROOT.rglob("*.pyc"):
        if ".venv" in pyc.parts:
            continue
        pyc.unlink(missing_ok=True)
    _log("Cleanup completed", GREEN)


@task(pre=[clean], name="macos-build")
def macos_build(c):
    """Build standalone executable for macOS."""
    _log("Building VoxKit for macOS...")
    c.run(
        "uv run --group installation python scripts/build.py build "
        "--entry main.py --name VoxKit --icon ./assets/voxkit.icns --windowed"
    )


@task(pre=[clean], name="linux-build")
def linux_build(c):
    """Build AppImage for Linux."""
    tools_dir = ROOT / "tools"
    tools_dir.mkdir(exist_ok=True)

    # Step 1: PyInstaller one-dir build
    _log("Building VoxKit for Linux (one-dir)...")
    c.run(
        "uv run --group installation python scripts/build.py build "
        "--entry main.py --name VoxKit --icon ./assets/voxkit.png --windowed --no-onefile"
    )

    dist_dir = ROOT / "dist" / "VoxKit"
    if not dist_dir.exists():
        _log(f"PyInstaller output not found at {dist_dir}", RED)
        return

    # Step 2: Bundle libxcb-cursor — Qt's xcb platform plugin loads it via dlopen
    # at runtime so PyInstaller's ldd scan misses it. We copy it next to libqxcb.so
    # so LD_LIBRARY_PATH (set by PyInstaller's bootloader) picks it up.
    _log("Bundling libxcb-cursor...")
    xcb_cursor_candidates = [
        Path("/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0"),
        Path("/usr/lib/libxcb-cursor.so.0"),
    ]
    xcb_cursor_src = next((p for p in xcb_cursor_candidates if p.exists()), None)
    if xcb_cursor_src is None:
        result = subprocess.run(  # noqa: S603
            ["find", "/usr", "-name", "libxcb-cursor.so.0"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
        found = result.stdout.strip().splitlines()
        xcb_cursor_src = Path(found[0]) if found else None

    if xcb_cursor_src is None:
        _log("libxcb-cursor.so.0 not found — run: sudo apt-get install libxcb-cursor0", RED)
        return

    internal_dir = dist_dir / "_internal"
    dest_dir = internal_dir if internal_dir.is_dir() else dist_dir
    shutil.copy2(xcb_cursor_src, dest_dir / "libxcb-cursor.so.0")
    _log(f"Bundled {xcb_cursor_src} -> {dest_dir / 'libxcb-cursor.so.0'}", GREEN)

    # Step 3: Set up AppDir
    _log("Setting up AppDir...")
    appdir = ROOT / "build" / "AppDir"
    _rmtree(appdir)
    appdir.mkdir(parents=True)

    shutil.copytree(dist_dir, appdir / "VoxKit")

    apprun = appdir / "AppRun"
    apprun.write_text(
        "#!/bin/bash\n"
        'APPDIR="$(dirname "$(readlink -f "$0")")"\n'
        'exec "$APPDIR/VoxKit/VoxKit" "$@"\n'
    )
    apprun.chmod(apprun.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    shutil.copy2(ROOT / "installer" / "linux" / "VoxKit.desktop", appdir / "VoxKit.desktop")
    shutil.copy2(ROOT / "assets" / "voxkit.png", appdir / "voxkit.png")

    # Step 4: Download appimagetool if needed
    appimagetool = tools_dir / "appimagetool-x86_64.AppImage"
    if not appimagetool.exists():
        _log("Downloading appimagetool...")
        url = "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
        urllib.request.urlretrieve(url, appimagetool)  # noqa: S310
        appimagetool.chmod(appimagetool.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Step 5: Package AppImage
    _log("Packaging AppImage...")
    output = ROOT / "dist" / "VoxKit-x86_64.AppImage"
    c.run(f"ARCH=x86_64 {appimagetool} {appdir} {output}")
    _log(f"AppImage created: {output}", GREEN)


@task(pre=[clean], name="windows-build")
def windows_build(c):
    """Build standalone executable for Windows."""
    _log("Building VoxKit for Windows...")
    c.run(
        "uv run --group installation python scripts/build.py build "
        "--entry main.py --name VoxKit --icon ./assets/voxkit.ico --windowed"
    )


@task
def format(c):
    """Format code with Ruff."""
    _log("Formatting code with Ruff...")
    c.run("uv run --only-group dev ruff format .")


@task(name="format-check")
def format_check(c):
    """Check code formatting with Ruff."""
    _log("Checking code formatting with Ruff...")
    c.run("uv run --only-group dev ruff format --check .")


@task
def lint(c):
    """Lint code with Ruff (auto-fix)."""
    _log("Linting with Ruff...")
    c.run("uv run --only-group dev ruff check --fix .")


@task(name="lint-check")
def lint_check(c):
    """Check linting with Ruff."""
    _log("Checking linting with Ruff...")
    c.run("uv run --only-group dev ruff check .")


@task(name="mypy-check")
def mypy_check(c):
    """Run mypy for type checking."""
    _log("Running mypy for type checking...")
    c.run("uv run --only-group dev mypy .")


@task(name="fresh-slate")
def fresh_slate(c):
    """Remove virtual environment and lock file."""
    _log("Removing virtual environment and lock file...")
    confirm = input("Are you sure you want to proceed? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return
    _rmtree(ROOT / ".venv")
    (ROOT / "uv.lock").unlink(missing_ok=True)
    _log("Removed .venv and uv.lock", GREEN)


@task(name="run-tests")
def run_tests(c):
    """Run all tests (unit + GUI)."""
    c.run("uv run pytest tests/")


@task(name="test-coverage")
def test_coverage(c):
    """Run tests with detailed coverage report for core modules."""
    _log("Running tests with coverage (core modules only)...")
    c.run("uv run pytest --cov=voxkit --cov-report=term-missing --cov-report=html tests/")
    _log("Coverage report generated in htmlcov/index.html", GREEN)


@task(name="generate-coverage-badge")
def generate_coverage_badge(c):
    """Generate coverage badge."""
    _log("Generating coverage badge...")
    c.run("uv run pytest --cov=voxkit --cov-report=xml tests/")
    c.run("uv run genbadge coverage -i coverage.xml -o assets/coverage.svg")
    _log("Coverage badge updated: assets/coverage.svg", GREEN)


@task(name="generate-documentation")
def generate_documentation(c):
    """Generate API documentation."""
    c.run("uv run --group docs pdoc -o docs src/voxkit")
