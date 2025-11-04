import os
import shutil
from datetime import datetime

from voxkit.config import Mode

STORAGE_ROOT = "~/.tpe-speech-analysis"
# Models are stored with this prefix for a more ceertain means of identification, set later
MODEL_PREFIX = "9276_model_"
DATA_PREFIX = "8372_dataset_"

TRAIN_ROOT = "train"


def get_storage_root() -> str:
    """Get the root directory for storing models and data."""
    if STORAGE_ROOT.startswith("~"):
        from pathlib import Path

        return str(Path(STORAGE_ROOT).expanduser())
    else:
        raise ValueError("STORAGE_ROOT must be a valid path starting with '~'")


def human_readable_date(date_str: str) -> str:
    """Convert YYYYMMDD_HHMMSS to 'MM-DD-YYYY H:MM am/pm' (e.g. 11-14-2001 6:00 pm)."""
    try:
        dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
        s = dt.strftime("%m-%d-%Y %I:%M %p")  # "11-14-2001 06:00 PM"
        date_part, time_part, ampm = s.split()
        hour, minute = time_part.split(":")
        hour = hour.lstrip("0")
        return f"{date_part} {hour}:{minute} {ampm.lower()}"
    except ValueError:
        return date_str


def machine_readable_date(date_str: str) -> str:
    """Convert 'MM-DD-YYYY H:MM am/pm' back to 'YYYYMMDD_HHMMSS'."""
    try:
        dt = datetime.strptime(date_str.strip(), "%m-%d-%Y %I:%M %p")
        return dt.strftime("%Y%m%d_%H%M%S")
    except ValueError:
        return date_str


def list_models(mode: Mode, add_date=False) -> list[str]:
    """List available model names for the given mode."""
    try:
        mode_path = f"{get_storage_root()}/{TRAIN_ROOT}/{mode}"

        if mode == "W2TG":
            if not os.path.exists(mode_path):
                print(f"Mode path does not exist: {mode_path}")
                return {}

            models = {}
            # Scan each subdirectory for a folder that starts with MODEL_PREFIX
            for entry in os.scandir(mode_path):
                if entry.is_dir():
                    for subentry in os.scandir(entry.path):
                        if subentry.is_dir() and subentry.name.startswith(MODEL_PREFIX):
                            print(f"Found model: {subentry.name} at {subentry.path}")
                            model_name = subentry.name[len(MODEL_PREFIX) :]
                            if add_date:
                                label = f"{model_name} ({human_readable_date(entry.name)})"
                            else:
                                label = model_name
                            models[label] = subentry.path

            return models

        elif mode == "MFA":
            if not os.path.exists(mode_path):
                print(f"Mode path does not exist: {mode_path}")
                return {}

            models = {}
            # Scan each subdirectory for a folder that starts with MODEL_PREFIX
            for entry in os.scandir(mode_path):
                if entry.is_dir():
                    for subentry in os.scandir(entry.path):
                        if subentry.is_dir() and subentry.name.startswith(MODEL_PREFIX):
                            print(f"Found model: {subentry.name} at {subentry.path}/model.zip")
                            model_name = subentry.name[len(MODEL_PREFIX) :]
                            if add_date:
                                label = f"{model_name} ({human_readable_date(entry.name)})"
                            else:
                                label = model_name
                            if not os.path.exists(subentry.path + "/model.zip"):
                                print(f"Error -- Model zip not found at: {subentry.path}/model.zip")
                                continue
                            models[label] = subentry.path + "/model.zip"

            return models

    except Exception as e:
        print(f"Error listing models: {e}")
        return {}


# TODO Combine with list_models
def list_modelz(mode: Mode, add_date=False) -> list[str]:
    """List available model names for the given mode."""
    try:
        mode_path = f"{get_storage_root()}/{TRAIN_ROOT}/{mode}"

        if mode == "W2TG":
            if not os.path.exists(mode_path):
                print(f"Mode path does not exist: {mode_path}")
                return {}

            models = {}
            # Scan each subdirectory for a folder that starts with MODEL_PREFIX
            for entry in os.scandir(mode_path):
                if entry.is_dir():
                    for subentry in os.scandir(entry.path):
                        if subentry.is_dir() and subentry.name.startswith(MODEL_PREFIX):
                            print(f"Found model: {subentry.name} at {subentry.path}")
                            model_name = subentry.name[len(MODEL_PREFIX) :]
                            if add_date:
                                date_time = human_readable_date(entry.name).split(" ")
                                label = f"{model_name}"
                                models[label] = {
                                    "path": subentry.path,
                                    "date": date_time[0],
                                    "time": date_time[1],
                                    "train_root": entry.name,
                                }
                            else:
                                label = model_name
                                models[label] = {"path": subentry.path, "train_root": entry.name}

            return models

        elif mode == "MFA":
            if not os.path.exists(mode_path):
                print(f"Mode path does not exist: {mode_path}")
                return {}

            models = {}
            # Scan each subdirectory for a folder that starts with MODEL_PREFIX
            for entry in os.scandir(mode_path):
                if entry.is_dir():
                    for subentry in os.scandir(entry.path):
                        if subentry.is_dir() and subentry.name.startswith(MODEL_PREFIX):
                            print(f"Found model: {subentry.name} at {subentry.path}/model.zip")
                            model_name = subentry.name[len(MODEL_PREFIX) :]
                            if not os.path.exists(subentry.path + "/model.zip"):
                                print(f"Error -- Model zip not found at: {subentry.path}/model.zip")
                                continue
                            if add_date:
                                label = f"{model_name}"
                                date_time = human_readable_date(entry.name).split(" ")
                                print(subentry.path)
                                models[label] = {
                                    "path": subentry.path + "/model.zip",
                                    "date": date_time[0],
                                    "time": date_time[1],
                                    "train_root": entry.name,
                                }
                            else:
                                label = model_name
                                models[label] = {
                                    "path": subentry.path + "/model.zip",
                                    "train_root": entry.name,
                                }
            return models

    except Exception as e:
        print(f"Error listing models: {e}")
        return {}


def delete_training_run(mode: Mode, train_root: str):
    """Delete a training run given its mode and root directory."""
    train_path = f"{get_storage_root()}/{TRAIN_ROOT}/{mode}/{train_root}"
    if os.path.exists(train_path):
        shutil.rmtree(train_path)
    else:
        raise FileNotFoundError(f"Training run path does not exist: {train_path}")


def create_train_destination(model_name: str, mode: Mode) -> str:
    """Create a directory for storing a new trained model and it information."""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    if mode == "W2TG":
        train_path = f"{get_storage_root()}/{TRAIN_ROOT}/{mode}/{now}"
        model_path = f"{train_path}/{MODEL_PREFIX}{model_name}"
        data_path = f"{train_path}/{DATA_PREFIX}{model_name}"
        eval_path = f"{train_path}/eval_output_textgrids"
        os.makedirs(model_path, exist_ok=True)
        os.makedirs(data_path, exist_ok=True)
        return data_path, model_path, train_path, eval_path
    elif mode == "MFA":
        train_path = f"{get_storage_root()}/{TRAIN_ROOT}/{mode}/{now}"
        model_path = f"{train_path}/{MODEL_PREFIX}{model_name}"
        data_path = f"{train_path}/{DATA_PREFIX}{model_name}"
        eval_path = f"{train_path}/eval_output_textgrids"
        os.makedirs(model_path, exist_ok=True)
        os.makedirs(data_path, exist_ok=True)
        return data_path, model_path + "/model.zip", train_path, eval_path
