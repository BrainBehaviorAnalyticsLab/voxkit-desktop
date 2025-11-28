import argparse
import os
import sys

"""
Build script for VoxKit - Creates standalone executable using PyInstaller
Usage:
    python build.py build --entry path/to/app.py [options]

Example:
    python build.py build --entry src/main.py --name VoxKit --onefile --windowed --icon assets/icon.icns --add-data "pkg/data:./data"
"""


def build(args):
        try:
                import PyInstaller.__main__ as pyi_main
        except Exception:
                print("PyInstaller not found. Install it with: pip install pyinstaller")
                sys.exit(1)

        opts = []

        if args.name:
                opts.append(f'--name={args.name}')
        if args.onefile:
                opts.append('--onefile')
        if args.windowed:
                opts.append('--windowed')
        if args.clean:
                opts.append('--clean')
        if args.distpath:
                opts.append(f'--distpath={args.distpath}')
        if args.workpath:
                opts.append(f'--workpath={args.workpath}')
        if args.specpath:
                opts.append(f'--specpath={args.specpath}')
        if args.icon:
                opts.append(f'--icon={args.icon}')
        for hi in args.hidden_import:
                opts.append(f'--hidden-import={hi}')

        # Add data: handle platform-specific separator for PyInstaller (--add-data "SRC;DEST" on Windows)
        sep = ';' if os.name == 'nt' else ':'
        for ad in args.add_data:
                # allow user to pass either "src:dest" or two args; normalize to required sep
                if sep in ad:
                        opts.append(f'--add-data={ad}')
                else:
                        # try to split on the other sep and remap
                        other = ';' if sep == ':' else ':'
                        if other in ad:
                                src, dest = ad.split(other, 1)
                                opts.append(f'--add-data={src}{sep}{dest}')
                        else:
                                # If user provided only a path, put it into same-name folder
                                opts.append(f'--add-data={ad}{sep}{os.path.basename(ad)}')

        # entry script is last argument
        opts.append(args.entry)

        print("Running PyInstaller with options:", opts)
        pyi_main.run(opts)

def main():
        parser = argparse.ArgumentParser(prog="build.py", description="Build a standalone executable using PyInstaller")
        sub = parser.add_subparsers(dest="command", required=True)

        build_p = sub.add_parser("build", help="Create executable with PyInstaller")
        build_p.add_argument("--entry", "-e", required=True, help="Path to the entry-point python file")
        build_p.add_argument("--name", "-n", default="VoxKit", help="Name of the generated executable")
        build_p.add_argument("--onefile", action="store_true", default=True, help="Produce a single-file executable (default enabled)")
        build_p.add_argument("--no-onefile", action="store_false", dest="onefile", help="Disable onefile mode")
        build_p.add_argument("--windowed", "-w", action="store_true", help="Windowed/GUI app (no console)")
        build_p.add_argument("--icon", help="Path to icon file (.ico/.icns)")
        build_p.add_argument("--distpath", help="Where to put the bundled app")
        build_p.add_argument("--workpath", help="Where to put build files (PyInstaller work path)")
        build_p.add_argument("--specpath", help="Where to put the generated .spec file")
        build_p.add_argument("--clean", action="store_true", help="Clean PyInstaller cache and remove temporary files")
        build_p.add_argument("--add-data", "-a", action="append", default=[], help="Additional data to bundle. Format src:dest (POSIX) or src;dest (Windows). Can be passed multiple times.")
        build_p.add_argument("--hidden-import", "-i", action="append", default=[], help="Hidden imports to pass to PyInstaller")

        args = parser.parse_args()

        if args.command == "build":
                build(args)

if __name__ == "__main__":
        main()
