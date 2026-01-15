import time
from typing import Callable, Literal

from voxkit.storage.config import MODELS_ROOT
from voxkit.storage.utils import get_storage_root
from voxkit.storage import models
from voxkit.services.hf import download_and_copy_huggingface_model
from voxkit.services.mfa import download_acoustic_model

AppName = "VoxKit"
Dimensions = {"min_width": 200, "min_height": 800, "max_width": 500, "max_height": None}
Defaults = {
    "mode": "W2TGENGINE",
    "output_path": "/path/to/output",
    "audio_path": "/path/to/audio",
    "textgrid_path": "/path/to/textgrids",
    "num_epochs": 10,
}

Mode = Literal["MFAENGINE", "W2TGENGINE"]
HELP_URL = "http://localhost:3000/help"


def startup_routine():
    """Example startup routine to be executed on first launch."""
    print("[STARTUP] Initializing VoxKit...")
    time.sleep(1)  # Simulate initialization

    storage_root = get_storage_root()
    print(f"[STARTUP] Storage root: {storage_root}")

    print("[STARTUP] Creating required directories...")
    (storage_root / "computed-likelihoods").mkdir(parents=True, exist_ok=True)
    (storage_root / "custom-likelihoods").mkdir(parents=True, exist_ok=True)
    time.sleep(1)  # Simulate directory setup

    # Download MFA models
    print("[STARTUP] Downloading MFA models...")
    mfa_models = ["acoustic-english_us_arpa-v3.0.0/english_us_arpa.zip", "acoustic-spanish_mfa-v3.3.0/spanish_mfa.zip"]
    mfa_models_path = storage_root / "MFAENGINE" / MODELS_ROOT
    mfa_models_path.mkdir(parents=True, exist_ok=True)
    for model in mfa_models:
        success, metadata = models.create_model('MFAENGINE', model.split('/')[1].replace('.zip', ''))
        if not success:
            print(f"[STARTUP] Failed to create model metadata for {model}. {metadata}")
            continue
        model_dest = metadata.get('model_path')
        if not model_dest:
            print(f"[STARTUP] Model path not found in metadata for {model}.")
            continue

        # Remove last part of path and relace with .zip
        output_file = model_dest.parent / model.split('/')[1]

        try:
            download_acoustic_model(model, str(output_file))
            # Update metadata to reflect downloaded file
            print(f"[STARTUP] MFA model {model} downloaded to: {output_file}")
            success, message = models.update_model_metadata('MFAENGINE', metadata['id'], {'model_path': str(output_file)})

            if not success:
                print(f"[STARTUP] Failed to update model metadata for {model}. {message}")

            print(f"[STARTUP] MFA model downloaded to: {output_file}")
        except Exception as e:
            print(f"[STARTUP] Failed to download MFA model {model}. Error: {e}")
    
    # Download W2TG model from HuggingFace
    print("[STARTUP] Downloading W2TG model from HuggingFace...")
    # Create folder for W2TG model
    w2tg_path = storage_root / "W2TGENGINE" / MODELS_ROOT
    w2tg_path.mkdir(parents=True, exist_ok=True)
    success, metadata = models.create_model('W2TGENGINE', 'prads_model')
    if not success:
        print(f"[STARTUP] Failed to create model metadata. {metadata}")
        return
    model_dest = metadata.get('model_path')
    if not model_dest:
        print("[STARTUP] Model path not found in metadata.")
        return
    result = download_and_copy_huggingface_model(
        model_path="pkadambi/Wav2TextGrid",
        destination=str(model_dest),
    )
    if result:
        print(f"[STARTUP] W2TG model downloaded to: {result}")
    else:
        print("[STARTUP] Failed to download W2TG model.")



    print("[STARTUP] Initialization complete!")


# Startup script configuration
# Set this to a callable function to run on first launch, or None to disable
STARTUP_SCRIPT: Callable[[], None] | None = startup_routine
