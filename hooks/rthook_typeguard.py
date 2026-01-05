"""
Runtime hook to disable typeguard's runtime introspection in frozen apps.
This runs before any module imports that use typeguard decorators.
"""
import os
import sys

if getattr(sys, 'frozen', False):
    # Disable typeguard in frozen builds
    os.environ['TYPEGUARD_DISABLE'] = '1'
    
    # Patch inspect module to prevent source code lookups
    import inspect
    
    _original_getsource = inspect.getsource
    _original_getsourcelines = inspect.getsourcelines
    _original_findsource = inspect.findsource
    
    def _patched_getsource(object):
        try:
            return _original_getsource(object)
        except (OSError, TypeError):
            return "# Source unavailable in frozen app\n"
    
    def _patched_getsourcelines(object):
        try:
            return _original_getsourcelines(object)
        except (OSError, TypeError):
            return (["# Source unavailable\n"], 0)
    
    def _patched_findsource(object):
        try:
            return _original_findsource(object)
        except (OSError, TypeError):
            # Return dummy source
            return (["# Source unavailable\n"], 0)
    
    inspect.getsource = _patched_getsource
    inspect.getsourcelines = _patched_getsourcelines
    inspect.findsource = _patched_findsource
    
    print("[Runtime Hook] Typeguard inspection disabled for frozen build")
