"""Example startup script for testing.

This is an example of how to configure a startup script that will run
on the first launch of VoxKit.

To use this:
1. Import the function in your config.py
2. Set STARTUP_SCRIPT = example_startup_script
"""

import time


def example_startup_script():
    """Example startup script that simulates downloading assets.
    
    This function demonstrates what a startup script might do:
    - Simulate downloading models or assets
    - Set up initial configuration
    - Perform one-time initialization
    """
    print("[STARTUP] Running first-launch startup script...")
    
    # Simulate downloading/preparing assets
    time.sleep(2)  # Simulate a 2-second operation
    
    print("[STARTUP] Assets retrieved successfully!")
    print("[STARTUP] First launch initialization complete.")


if __name__ == "__main__":
    # For testing the script directly
    example_startup_script()
