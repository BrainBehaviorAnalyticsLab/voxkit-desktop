import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

"""
Build script for VoxKit - Creates standalone macOS .app bundle using PyInstaller
Usage:
    python build.py build --entry path/to/app.py [options]

Example:
    python build.py build --entry main.py --name VoxKit --icon assets/icon.icns
"""


def codesign_macos_app(app_path):
    """Ad-hoc code sign the macOS app bundle"""
    print("[macOS] Code signing app bundle...")

    # Find all dylibs and executables to sign
    files_to_sign = []

    internal_dir = app_path / "_internal"
    if internal_dir.exists():
        for dylib in internal_dir.glob("*.dylib"):
            files_to_sign.append(dylib)
        for so in internal_dir.glob("**/*.so"):
            files_to_sign.append(so)

    executable = app_path / "VoxKit"
    if executable.exists():
        files_to_sign.append(executable)

    # Sign each file with ad-hoc signature
    for file_path in files_to_sign:
        print(f"[macOS]   Signing {file_path.name}...")
        result = subprocess.run(
            [
                "codesign",
                "--force",
                "--deep",
                "--sign",
                "-",  # Ad-hoc signature
                str(file_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"[WARNING] Failed to sign {file_path.name}: {result.stderr}")

    print("[macOS] Code signing complete")
    return True


def fix_macos_dylib_paths(app_path, python_lib_source):
    """Fix dylib paths for macOS .app bundles"""
    print("[macOS] Fixing dynamic library paths...")

    internal_dir = app_path / "_internal"
    executable = app_path / "VoxKit"

    if not internal_dir.exists():
        print(f"[ERROR] _internal directory not found at {internal_dir}")
        return False

    # Copy Python shared library if it exists
    python_lib_dest = internal_dir / "libpython3.11.dylib"

    if python_lib_source.exists() and not python_lib_dest.exists():
        print(f"[macOS] Copying Python library from {python_lib_source}")
        shutil.copy2(python_lib_source, python_lib_dest)

    if python_lib_dest.exists():
        print(f"[macOS] Fixing library ID for {python_lib_dest.name}")
        # Make writable
        os.chmod(python_lib_dest, 0o755)
        # Change library ID to use @loader_path
        subprocess.run(
            ["install_name_tool", "-id", "@loader_path/libpython3.11.dylib", str(python_lib_dest)],
            check=False,
        )

    if executable.exists():
        print("[macOS] Updating executable to reference bundled Python library")
        os.chmod(executable, 0o755)
        # Update executable to look for library relative to itself
        subprocess.run(
            [
                "install_name_tool",
                "-change",
                str(python_lib_source),
                "@loader_path/../_internal/libpython3.11.dylib",
                str(executable),
            ],
            check=False,
        )

    print("[macOS] Dylib path fixing complete")
    return True


def build(args):
    try:
        import PyInstaller.__main__ as pyi_main
    except Exception:
        print("PyInstaller not found. Install it with: pip install pyinstaller")
        sys.exit(1)

    opts = []

    # Basic options
    if args.name:
        opts.append(f"--name={args.name}")

    # macOS: Always use onedir mode for .app bundles
    if sys.platform == "darwin" and args.windowed:
        print("[macOS] Using onedir mode (required for .app bundles)")
        # Don't add --onefile
    elif args.onefile:
        opts.append("--onefile")

    if args.windowed:
        opts.append("--windowed")
    if args.clean:
        opts.append("--clean")
    if args.distpath:
        opts.append(f"--distpath={args.distpath}")
    if args.workpath:
        opts.append(f"--workpath={args.workpath}")
    if args.specpath:
        opts.append(f"--specpath={args.specpath}")
    if args.icon:
        opts.append(f"--icon={args.icon}")

    # Hidden imports
    default_hidden = [
        "typeguard",
        "inflect",
        "g2p_en",
        "speechbrain",
        "speechbrain.utils",
        # Engine modules that need to be explicitly included
        "voxkit.engines._w2tg_engine",
        "voxkit.engines._whisperx_engine",
        "voxkit.engines.mfa_engine",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtSvg",
        "PyQt6.QtSvgWidgets",
    ]
    for hi in default_hidden + args.hidden_import:
        opts.append(f"--hidden-import={hi}")

    # Add hooks directory if it exists
    hooks_dir = Path(__file__).parent / "hooks"
    if hooks_dir.exists():
        opts.append(f"--additional-hooks-dir={hooks_dir}")

    # Add data
    sep = ";" if os.name == "nt" else ":"
    for ad in args.add_data:
        if sep in ad:
            opts.append(f"--add-data={ad}")
        else:
            other = ";" if sep == ":" else ":"
            if other in ad:
                src, dest = ad.split(other, 1)
                opts.append(f"--add-data={src}{sep}{dest}")
            else:
                opts.append(f"--add-data={ad}{sep}{os.path.basename(ad)}")

    # Entry script is last
    opts.append(args.entry)

    print("Running PyInstaller with options:", opts)
    pyi_main.run(opts)

    # Post-build: Fix macOS dylib paths and code sign
    if sys.platform == "darwin":
        print("\n[macOS] Running post-build fixes...")
        dist_path = Path(args.distpath) if args.distpath else Path("dist")
        app_path = dist_path / args.name

        # Find Python shared library
        python_lib = Path(sys.base_prefix) / "lib" / "libpython3.11.dylib"

        if app_path.exists():
            fix_macos_dylib_paths(app_path, python_lib)
            codesign_macos_app(app_path)
            print(f"\n✅ Build complete: {app_path}")
            print(f"   Run with: ./dist/{args.name}/{args.name}")
        else:
            print(f"\n⚠️  Expected build output not found at {app_path}")


def main():
    parser = argparse.ArgumentParser(
        prog="build.py", description="Build a standalone executable using PyInstaller"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build_p = sub.add_parser("build", help="Create executable with PyInstaller")
    build_p.add_argument("--entry", "-e", required=True, help="Path to the entry-point python file")
    build_p.add_argument("--name", "-n", default="VoxKit", help="Name of the generated executable")
    build_p.add_argument(
        "--onefile",
        action="store_true",
        default=True,
        help="Produce a single-file executable (default enabled)",
    )
    build_p.add_argument(
        "--no-onefile", action="store_false", dest="onefile", help="Disable onefile mode"
    )
    build_p.add_argument(
        "--windowed", "-w", action="store_true", help="Windowed/GUI app (no console)"
    )
    build_p.add_argument("--icon", help="Path to icon file (.ico/.icns)")
    build_p.add_argument("--distpath", help="Where to put the bundled app")
    build_p.add_argument("--workpath", help="Where to put build files (PyInstaller work path)")
    build_p.add_argument("--specpath", help="Where to put the generated .spec file")
    build_p.add_argument(
        "--clean", action="store_true", help="Clean PyInstaller cache and remove temporary files"
    )
    build_p.add_argument(
        "--add-data",
        "-a",
        action="append",
        default=[],
        help="Additional data to bundle. Format src:dest (POSIX) or src;dest (Windows). Can be passed multiple times.",
    )
    build_p.add_argument(
        "--hidden-import",
        "-i",
        action="append",
        default=[],
        help="Hidden imports to pass to PyInstaller",
    )

    args = parser.parse_args()

    if args.command == "build":
        build(args)


if __name__ == "__main__":
    main()
