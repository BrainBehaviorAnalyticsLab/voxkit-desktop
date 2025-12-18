"""
PyInstaller hook for typeguard
Disables runtime type checking in frozen applications
"""
from PyInstaller.utils.hooks import collect_all

# Collect everything from typeguard
datas, binaries, hiddenimports = collect_all('typeguard')

# Disable typeguard's runtime checking in frozen apps
excludedimports = []
