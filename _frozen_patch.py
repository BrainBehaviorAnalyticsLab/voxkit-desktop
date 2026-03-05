"""
Runtime patch to disable problematic inspect operations in frozen apps
"""

import sys

if getattr(sys, "frozen", False):
    # We're running in a PyInstaller bundle
    print("[PATCH] Applying frozen app patches...")
    
    # Patch 1: Disable typeguard runtime checking
    try:
        import typeguard
        
        # Replace typechecked decorator with a no-op
        def _noop_decorator(func=None, **kwargs):
            """No-op decorator that just returns the function unchanged"""
            if func is None:
                # Called with arguments: @typechecked(...)
                return lambda f: f
            # Called without arguments: @typechecked
            return func
        
        typeguard.typechecked = _noop_decorator
        print("[PATCH] Disabled typeguard runtime checking")
    except ImportError:
        pass
    
    # Patch 2: Fix inspect.getsource to not fail in frozen apps
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

    # Patch findsource (used by torch library registration)
    _original_findsource = inspect.findsource

    def _patched_findsource(object):
        try:
            return _original_findsource(object)
        except (OSError, TypeError):
            return (["# Source code not available\n"], 0)

    inspect.findsource = _patched_findsource

    # Patch getsourcefile to return None instead of invalid paths
    _original_getsourcefile = inspect.getsourcefile

    def _patched_getsourcefile(object):
        try:
            result = _original_getsourcefile(object)
            # Check if the file actually exists
            if result and not __import__('os').path.exists(result):
                return None
            return result
        except (OSError, TypeError):
            return None

    inspect.getsourcefile = _patched_getsourcefile

    # Patch getfile similarly for completeness
    _original_getfile = inspect.getfile

    def _patched_getfile(object):
        try:
            return _original_getfile(object)
        except (OSError, TypeError):
            return "<frozen>"

    inspect.getfile = _patched_getfile

    print("[PATCH] Patched inspect module for frozen app")

    # Patch linecache to not fail on missing source files
    import linecache

    _original_getlines = linecache.getlines

    def _patched_getlines(filename, module_globals=None):
        try:
            return _original_getlines(filename, module_globals)
        except (OSError, TypeError):
            return []

    linecache.getlines = _patched_getlines

    print("[PATCH] Patched linecache for frozen app")

    # Patch 3: Pre-populate sys.modules with dummy modules for problematic imports
    # This prevents lazy imports from failing by providing stub modules
    import types

    problematic_modules = [
        # k2 integration
        "speechbrain.integrations.k2_fsa",
        "speechbrain.k2_integration",
        "k2",
        # NLP integrations that may have missing deps
        "speechbrain.integrations.nlp",
        "speechbrain.integrations.nlp.flair_embeddings",
        "speechbrain.integrations.nlp.flair_tagger",
        "speechbrain.integrations.nlp.spacy_pipeline",
        "speechbrain.integrations.nlp.bleu",
        "speechbrain.integrations.nlp.bgeM3_embeddings",
        "speechbrain.lobes.models.flair",
        "speechbrain.lobes.models.spacy",
        # Numba integration
        "speechbrain.integrations.numba",
        "speechbrain.integrations.numba.transducer_loss",
        "speechbrain.nnet.loss.transducer_loss",
        # Other optional integrations
        "speechbrain.integrations.decoders",
        "speechbrain.integrations.decoders.kenlm_scorer",
    ]

    for mod_name in problematic_modules:
        if mod_name not in sys.modules:
            dummy = types.ModuleType(mod_name)
            dummy.__file__ = "<frozen-stub>"
            dummy.__path__ = []
            dummy.__doc__ = "Stub module for frozen app compatibility"
            sys.modules[mod_name] = dummy

    print("[PATCH] Installed stub modules for k2/k2_fsa")
