import shutil
from pathlib import Path
from typing import Optional


def download_and_copy_huggingface_model(
    model_path: str,
    destination: str,
) -> Optional[str]:
    """
    Download model from HuggingFace and copy actual files to destination.
    Follows symlinks to get real model files (like git clone behavior).
    
    Args:
        model_path: HuggingFace model path (e.g., 'pkadambi/Wav2TextGrid')
        destination: Where to copy the model files
    
    Returns:
        Destination path if successful, None if failed
    """
    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import HfHubHTTPError, RepositoryNotFoundError
        
        # Validate model path format
        if not model_path or '/' not in model_path:
            print(f"Invalid model path format: {model_path}")
            return None
        
        # Download to HF cache (returns path to snapshot with symlinks)
        cache_snapshot_path = snapshot_download(
            repo_id=model_path,
            resume_download=True,
        )
        
        print(f"Downloaded to cache: {cache_snapshot_path}")
        
        # Create destination directory
        dest_path = Path(destination).expanduser()
        dest_path.mkdir(parents=True, exist_ok=True)
        
        # Copy all files, following symlinks (like git clone)
        cache_path = Path(cache_snapshot_path)
        for item in cache_path.iterdir():
            if item.name.startswith('.'):
                # Skip .gitattributes and other hidden files if desired
                continue
                
            if item.is_symlink() or item.is_file():
                # Resolve symlink to get actual file, then copy
                actual_file = item.resolve()
                dest_file = dest_path / item.name
                shutil.copy2(actual_file, dest_file)
                print(f"Copied: {item.name}")
            elif item.is_dir():
                # Recursively copy directories
                shutil.copytree(item, dest_path / item.name, 
                              symlinks=False,  # Follow symlinks
                              dirs_exist_ok=True)
        
        print(f"Successfully copied model to: {dest_path}")
        return str(dest_path)
        
    except RepositoryNotFoundError:
        print(f"Model not found: {model_path}")
        return None
        
    except HfHubHTTPError as e:
        print(f"HTTP error downloading model: {e}")
        return None
        
    except Exception as e:
        print(f"Error downloading model {model_path}: {e}")
        return None


# # Update your dialog's accept method:
# class ImportModelDialog(GenericDialog):
#     # ... existing code ...
    
#     def accept(self):
#         """Override accept to trigger import callback"""
#         values = self.get_values()
#         hf_model_path = values.get("model_path", "").strip()
#         local_model_path = values.get("local_model_path", "").strip()

#         # Determine which path to use
#         if hf_model_path:
#             # Download from HuggingFace
#             destination = create_train_destination(self.engine_id)
#             result = download_and_copy_huggingface_model(hf_model_path, destination)
            
#             if result is None:
#                 # Show error - could use QMessageBox here
#                 print("Failed to download model")
#                 return
            
#             final_path = result
            
#         elif local_model_path:
#             # Use local path
#             final_path = local_model_path
#         else:
#             print("Please provide either HuggingFace path or local path")
#             return

#         # Call the import callback with final path
#         if self.on_import_callback:
#             self.on_import_callback(self.engine_id, final_path)
        
#         super().accept()