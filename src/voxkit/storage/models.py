import os
import shutil
from datetime import datetime
from typing import TypedDict

from .config import DATA_PREFIX, MODEL_PREFIX, TRAIN_ROOT
from .utils import get_storage_root, human_readable_date


class ModelMetadata(TypedDict):
    path: str
    date: str
    time: str
    name: str
    id: str
    train_root: str


def list_models(engine_id, add_date=False) -> list[str]:
    """List available model names for the given mode."""
    try:
        models_root = f"{get_storage_root()}/{engine_id}/{TRAIN_ROOT}"

        if engine_id == "W2TGENGINE":
            if not os.path.exists(models_root):
                print(f"Mode path does not exist: {models_root}")
                return {}

            models = {}
            # Scan each subdirectory for a folder that starts with MODEL_PREFIX
            for entry in os.scandir(models_root):
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

        elif engine_id == "MFAENGINE":
            if not os.path.exists(models_root):
                print(f"Mode path does not exist: {models_root}")
                return {}

            models = {}
            # Scan each subdirectory for a folder that starts with MODEL_PREFIX
            for entry in os.scandir(models_root):
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


def list_modelz(engine_id, add_date=False) -> dict[str, ModelMetadata]:
    """List available model names for the given mode."""
    try:

        models_root = f"{get_storage_root()}/{engine_id}/{TRAIN_ROOT}"

        if engine_id == "W2TGENGINE":
            if not os.path.exists(models_root):
                print(f"Mode path does not exist: {models_root}")
                return {}

            models = {}
            # Scan each subdirectory for a folder that starts with MODEL_PREFIX
            for entry in os.scandir(models_root):
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
                                    "name": model_name,
                                    "id": model_name,
                                    "train_root": entry.name,
                                }
                            else:
                                label = model_name
                                models[label] = {"path": subentry.path, "train_root": entry.name}

            return models

        elif engine_id == "MFAENGINE":
            if not os.path.exists(models_root):
                print(f"Mode path does not exist: {models_root}")
                return {}

            models = {}
            # Scan each subdirectory for a folder that starts with MODEL_PREFIX
            for entry in os.scandir(models_root):
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


def scrub_training_run(engine_id, train_code: str):
    """Delete a training run given its mode and root directory."""
    train_path = f"{get_storage_root()}/{engine_id}/{TRAIN_ROOT}/{train_code}"
    if os.path.exists(train_path):
        shutil.rmtree(train_path)
    else:
        raise FileNotFoundError(f"Training run path does not exist: {train_path}")


def create_train_destination(model_name: str, engine_id) -> str:
    """Create a directory for storing a new trained model and it information."""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    if engine_id == "W2TGENGINE":
        train_path = f"{get_storage_root()}/{engine_id}/{TRAIN_ROOT}/{now}"
        model_path = f"{train_path}/{MODEL_PREFIX}{model_name}"
        data_path = f"{train_path}/{DATA_PREFIX}{model_name}"
        eval_path = f"{train_path}/eval_output_textgrids"
        os.makedirs(model_path, exist_ok=True)
        os.makedirs(data_path, exist_ok=True)
        return data_path, model_path, train_path, eval_path
    elif engine_id == "MFAENGINE":
        train_path = f"{get_storage_root()}/{engine_id}/{TRAIN_ROOT}/{now}"
        model_path = f"{train_path}/{MODEL_PREFIX}{model_name}"
        data_path = f"{train_path}/{DATA_PREFIX}{model_name}"
        eval_path = f"{train_path}/eval_output_textgrids"
        os.makedirs(model_path, exist_ok=True)
        os.makedirs(data_path, exist_ok=True)
        return data_path, model_path + "/model.zip", train_path, eval_path