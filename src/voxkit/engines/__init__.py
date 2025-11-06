"""
TODO
"""

from .api import AlignmentEngine
from .w2tg_engine import W2TGEngine

ENGINES_ALLOWED = ["MFA", "W2TG"]

class EngineManager:
    def __init__(self):
        print("Initializing EngineManager...")
        self.engines = {
            "W2TG": W2TGEngine(),
        }
    
    def get_engine(self, code: str) -> AlignmentEngine:
        if code not in ENGINES_ALLOWED:
            print(f"Engine code '{code}' is not allowed.")
            return None
        engine = self.engines.get(code)
        if engine is None:
            raise ValueError(f"Engine with code '{code}' is not configured properly")
        return engine
        
        
    
__all__ = [
    EngineManager,
    ENGINES_ALLOWED
]