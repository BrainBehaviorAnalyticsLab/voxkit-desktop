"""PyInstaller hook for nltk package.

This hook prevents PyInstaller from collecting NLTK data files.
NLTK data is downloaded at runtime by the application instead.
"""

# Don't collect any NLTK data files - they will be downloaded at runtime
datas = []

# Exclude data collection
excludedimports = []
