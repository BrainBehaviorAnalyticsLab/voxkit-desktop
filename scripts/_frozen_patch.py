"""
Runtime patch to disable problematic inspect operations in frozen apps
"""

import sys

if getattr(sys, "frozen", False):
    # We're running in a PyInstaller bundle
    import inspect

    # Patch inspect.getsource to return empty string instead of raising
    _original_getsource = inspect.getsource

    def _patched_getsource(object):
        try:
            return _original_getsource(object)
        except (OSError, TypeError):
            # Return a dummy source code
            return "# Source code not available in frozen application\npass\n"

    inspect.getsource = _patched_getsource

    # Patch getsourcelines similarly
    _original_getsourcelines = inspect.getsourcelines

    def _patched_getsourcelines(object):
        try:
            return _original_getsourcelines(object)
        except (OSError, TypeError):
            return (["# Source code not available\n", "pass\n"], 0)

    inspect.getsourcelines = _patched_getsourcelines

    print("[PATCH] Disabled source code inspection for frozen app")
