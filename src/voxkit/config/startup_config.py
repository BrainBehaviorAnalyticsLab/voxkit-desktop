import logging
import subprocess
import time
from typing import Callable, Literal

from voxkit.services import mfa_provision
from voxkit.services.mfa import describe_process_failure, download_acoustic_model
from voxkit.storage import models
from voxkit.storage.constants import MODELS_ROOT
from voxkit.storage.models import download_and_copy_huggingface_model
from voxkit.storage.utils import get_storage_root

log = logging.getLogger(__name__)

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


def startup_routine():
    """Example startup routine to be executed on first launch."""
    log.info("Initializing VoxKit...")
    time.sleep(1)  # Simulate initialization

    storage_root = get_storage_root()
    log.info("Storage root: %s", storage_root)

    log.info("Creating required directories...")
    (storage_root / "computed-likelihoods").mkdir(parents=True, exist_ok=True)
    (storage_root / "custom-likelihoods").mkdir(parents=True, exist_ok=True)
    time.sleep(1)  # Simulate directory setup

    # Download MFA models
    log.info("Downloading MFA models...")
    mfa_models = [
        "acoustic-english_us_arpa-v3.0.0/english_us_arpa.zip",
        "acoustic-spanish_mfa-v3.3.0/spanish_mfa.zip",
    ]
    mfa_models_path = storage_root / "MFAENGINE" / MODELS_ROOT
    mfa_models_path.mkdir(parents=True, exist_ok=True)
    for model in mfa_models:
        success, metadata = models.create_model(
            "MFAENGINE", model.split("/")[1].replace(".zip", "")
        )
        if not success:
            log.error("Failed to create model metadata for %s: %s", model, metadata)
            continue
        assert not isinstance(metadata, str)
        model_dest = metadata.get("model_path")
        if not model_dest:
            log.error("Model path not found in metadata for %s", model)
            continue

        # Remove last part of path and relace with .zip
        output_file = model_dest.parent / model.split("/")[1]

        try:
            download_acoustic_model(model, str(output_file))
            # Update metadata to reflect downloaded file
            success, message = models.update_model_metadata(
                "MFAENGINE", metadata["id"], {"model_path": str(output_file)}
            )

            if not success:
                log.error("Failed to update model metadata for %s: %s", model, message)

            log.info("MFA model %s downloaded to %s", model, output_file)
        except Exception:
            log.exception("Failed to download MFA model %s", model)

    # Download W2TG model from HuggingFace
    log.info("Downloading W2TG model from HuggingFace...")
    # Create folder for W2TG model
    w2tg_path = storage_root / "W2TGENGINE" / MODELS_ROOT
    w2tg_path.mkdir(parents=True, exist_ok=True)
    success, metadata = models.create_model("W2TGENGINE", "default")
    if not success:
        log.error("Failed to create W2TG model metadata: %s", metadata)
        return
    assert not isinstance(metadata, str)
    model_dest = metadata.get("model_path")
    if not model_dest:
        log.error("Model path not found in W2TG metadata")
        return
    result = download_and_copy_huggingface_model(
        model_path="pkadambi/Wav2TextGrid",
        destination=str(model_dest),
    )
    if result:
        log.info("W2TG model downloaded to %s", result)
    else:
        log.error("Failed to download W2TG model")

    try:
        import nltk

        nltk.download("averaged_perceptron_tagger_eng")

    except Exception:
        log.exception("Failed to download NLTK resources")

    log.info("Initialization complete")


def ensure_mfa_environment() -> bool:
    """Provision VoxKit's own managed MFA ("aligner") environment if needed.

    Deliberately *not* part of `startup_routine` and not gated on the
    first-launch flag: readiness is its own gate. Provisioning used to live
    inside the first-launch routine, where a failure was swallowed, the flag
    was marked complete anyway, and the step then never ran again -- leaving
    MFA permanently unavailable with nothing in the log to say why. This is
    idempotent and cheap when the environment is ready, and micromamba
    resumes from its package cache when a previous attempt was interrupted,
    so running it on every launch costs nothing once setup has succeeded.

    Logs rather than prints: in a `--windowed` PyInstaller build `sys.stdout`
    is redirected to devnull (see `main.py`), so `print()` diagnostics from
    this path are discarded exactly when they are most needed.

    Returns:
        True if the environment is ready (already, or after provisioning).
    """
    if mfa_provision.lockfile_path() is None:
        log.info(
            "No bundled MFA environment for this platform; "
            "MFA will use the user-managed conda fallback."
        )
        return False

    if mfa_provision.is_aligner_env_ready():
        return True

    log.info("Setting up the MFA alignment environment (one-time, ~1-2GB)...")
    try:
        mfa_provision.provision_aligner_env()
    except subprocess.CalledProcessError as e:
        # CalledProcessError carries the same returncode/stdout/stderr trio.
        log.error("MFA environment setup failed: %s", describe_process_failure(e))
        return False
    except Exception:
        log.exception("MFA environment setup failed.")
        return False

    log.info("MFA alignment environment ready.")
    return True


# Startup script configuration
# Set this to a callable function to run on first launch, or None to disable
STARTUP_SCRIPT: Callable[[], None] | None = startup_routine
