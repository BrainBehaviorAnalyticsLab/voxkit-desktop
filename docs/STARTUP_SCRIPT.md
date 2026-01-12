# Startup Script Feature

This document describes how to use VoxKit's configurable startup script feature, which allows you to execute a Python function on the first launch of the application.

## Overview

The startup script feature provides a mechanism to:
- Run custom initialization code only on the **first launch** of VoxKit
- Execute before any GUI stackers are initialized
- Display a loading dialog ("Retrieving assets...") while the script runs
- Track whether the app has been launched before using a flag file in the user's data directory

## How It Works

1. **First Launch Detection**: VoxKit checks for a `.first_launch_complete` flag file in the storage root (`~/.voxkit/`)
2. **Script Execution**: If this is the first launch and a startup script is configured, it runs in a background thread
3. **Loading Dialog**: A modal dialog displays "Retrieving assets..." while the script executes
4. **Completion Tracking**: After successful execution, the flag file is created to prevent re-running on subsequent launches

## Configuration

To configure a startup script, edit `src/voxkit/config.py` and set the `STARTUP_SCRIPT` variable:

```python
from typing import Callable

# Import your startup function
from my_module import my_startup_function

# Set the startup script (or None to disable)
STARTUP_SCRIPT: Callable[[], None] | None = my_startup_function
```

## Example Usage

See `example_startup_script.py` for a complete example:

```python
def example_startup_script():
    """Example startup script that simulates downloading assets."""
    print("[STARTUP] Running first-launch startup script...")
    
    # Your initialization code here
    # e.g., download models, set up configuration, etc.
    time.sleep(2)  # Simulate a 2-second operation
    
    print("[STARTUP] Assets retrieved successfully!")
```

To enable this example:

1. Edit `src/voxkit/config.py`
2. Import the example function:
   ```python
   from example_startup_script import example_startup_script
   ```
3. Set the configuration:
   ```python
   STARTUP_SCRIPT = example_startup_script
   ```

## API Reference

### Storage Utilities (`voxkit.storage.utils`)

#### `is_first_launch() -> bool`
Check if this is the first launch of the application.

**Returns:**
- `True` if this is the first launch
- `False` if the app has been launched before

#### `mark_first_launch_complete() -> None`
Mark the first launch as complete by creating a flag file.

This is automatically called after successful startup script execution.

### Startup Module (`voxkit.startup`)

#### `execute_startup_script(script: Callable[[], None] | None, app: QApplication) -> None`
Execute the startup script if this is the first launch.

**Parameters:**
- `script`: The startup script function to execute, or `None` to skip
- `app`: The QApplication instance for event processing

**Behavior:**
- Does nothing if `script` is `None` or if it's not the first launch
- Shows a loading dialog while the script runs
- Marks first launch as complete after successful execution
- Prints errors but still marks as complete to avoid infinite retries

### GUI Components (`voxkit.gui.components`)

#### `LoadingDialog(message: str, parent=None)`
A modal loading dialog with a message and progress indicator.

**Parameters:**
- `message`: The message to display (default: "Loading...")
- `parent`: Optional parent widget

**Methods:**
- `update_message(message: str)`: Update the displayed message

## Testing First Launch Again

If you want to test the first launch behavior again:

1. Delete the flag file:
   ```bash
   rm ~/.voxkit/.first_launch_complete
   ```
2. Launch VoxKit again

Or programmatically:
```python
from pathlib import Path
from voxkit.storage.utils import get_storage_root

flag_file = get_storage_root() / ".first_launch_complete"
flag_file.unlink(missing_ok=True)
```

## Error Handling

- If the startup script raises an exception, the error is printed to the console
- The loading dialog is updated to show the error message
- The first launch is still marked as complete to avoid infinite retries
- The application continues to start normally

## Integration Points

The startup script runs in `main.py` after:
1. QApplication is created
2. The application style is set

But before:
1. The main window (`AlignmentGUI`) is created
2. Any GUI stackers are initialized
3. The window is shown

This ensures that:
- PyQt event loop is available for the loading dialog
- No GUI components are initialized while assets are being retrieved
- The user sees the loading dialog immediately on first launch

## Use Cases

Common use cases for startup scripts:

1. **Download pre-trained models**: Download models from HuggingFace or other sources
2. **Initialize database**: Set up local database schemas or initial data
3. **Download assets**: Retrieve configuration files, dictionaries, or other resources
4. **System checks**: Verify dependencies or system requirements
5. **User onboarding**: Display welcome messages or setup wizards (though the loading dialog should stay simple)

## Notes

- The startup script runs synchronously (blocks the main thread until complete)
- Keep the script focused and fast to avoid long startup times
- Use the loading dialog message to communicate what's happening
- The script only runs once per installation (per user data directory)
- If you need to run setup again, delete the flag file manually
