import os
import shutil
import subprocess
import sys
from pathlib import Path

from voxkit.services import mfa_provision


def _no_window() -> dict:
    """Return creationflags to suppress console windows on Windows."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def _mfa_invocation(conda_path: str | None = None) -> tuple[list[str], dict]:
    """Return (command_prefix, extra_env) for invoking `mfa <subcommand> ...`.

    Prefers VoxKit's own bundled/provisioned aligner environment
    (`mfa_provision`) when it's ready, so most users never need conda
    installed at all. Falls back to exactly the previous behavior --
    `_find_conda(conda_path)` + `conda run -n aligner mfa` -- for anyone
    with their own pre-existing conda + `aligner` environment, with zero
    change to that path.

    The bundled environment is invoked as `micromamba run -p <env> python
    <env>/Scripts/mfa-script.py`, not the `mfa`/`mfa.exe` entry-point stub
    directly -- confirmed via real-world testing that the stub can fail to
    launch ("failed to create process") on a machine where invoking Python
    with the underlying script directly, inside the same activated
    environment, works correctly. `micromamba run -p <env>` still performs
    full environment activation (PATH/DLL search paths Kaldi and the
    bundled Postgres server need), just naming the interpreter explicitly
    rather than relying on the stub.
    """
    # is_aligner_env_ready() only ever returns True on win32 in v1 (the only
    # platform with a bundled lockfile today), so the Windows-specific
    # env-layout paths below (Scripts/, python.exe) are always correct here.
    if mfa_provision.is_aligner_env_ready():
        micromamba = str(mfa_provision.vendored_micromamba_path())
        env_path = mfa_provision.bundled_env_path()
        python = str(env_path / "python.exe")
        script = str(env_path / "Scripts" / "mfa-script.py")
        prefix = [micromamba, "run", "-p", str(env_path), python, script]
        extra_env = {"MFA_ROOT_DIR": str(mfa_provision.mfa_root_dir())}
        return prefix, extra_env

    conda = _find_conda(conda_path)
    return [conda, "run", "-n", "aligner", "mfa"], {}


def _find_conda(conda_path: str | None = None) -> str:
    """Return the conda executable path.

    Resolution order:
        1. ``conda_path`` argument, when it points to an existing file. This is
           the path a user configures in the MFA engine settings, primarily so
           Windows users with a non-standard Anaconda/Miniconda install can
           point VoxKit straight at their ``conda.exe``.
        2. The ``VOXKIT_CONDA_PATH`` environment variable, when it points to an
           existing file.
        3. ``conda`` on the system PATH.
        4. Common install locations on Windows.

    Args:
        conda_path: Optional user-configured path to the conda executable.

    Raises:
        FileNotFoundError: If conda cannot be located through any of the above.
    """
    # User-configured path (settings dialog) or environment override take
    # precedence over auto-detection so a deliberate choice always wins.
    for candidate in (conda_path, os.environ.get("VOXKIT_CONDA_PATH")):
        if candidate:
            resolved = Path(candidate).expanduser()
            if resolved.exists():
                return str(resolved)

    # Fast path: conda is already on PATH
    if shutil.which("conda"):
        return "conda"

    if sys.platform == "win32":
        home = Path.home()
        candidates = [
            home / "miniconda3" / "Scripts" / "conda.exe",
            home / "anaconda3" / "Scripts" / "conda.exe",
            home / "miniforge3" / "Scripts" / "conda.exe",
            home / "mambaforge" / "Scripts" / "conda.exe",
            home / "Miniconda3" / "Scripts" / "conda.exe",
            home / "Anaconda3" / "Scripts" / "conda.exe",
            Path("C:/ProgramData/miniconda3/Scripts/conda.exe"),
            Path("C:/ProgramData/anaconda3/Scripts/conda.exe"),
            Path("C:/tools/miniconda3/Scripts/conda.exe"),
        ]
        # Also check CONDA_PREFIX env var (set when a conda env is active)
        conda_prefix = os.environ.get("CONDA_PREFIX") or os.environ.get("CONDA_EXE", "")
        if conda_prefix:
            candidates.insert(0, Path(conda_prefix).parent / "conda.exe")
            candidates.insert(0, Path(conda_prefix))

        for path in candidates:
            if path.exists():
                return str(path)

    raise FileNotFoundError(
        "conda not found. Install Miniconda from https://docs.conda.io/en/latest/miniconda.html "
        "and create the aligner environment with: "
        "conda create -n aligner -c conda-forge montreal-forced-aligner. "
        "If conda is installed but not on PATH (common on Windows), set its full path in the "
        "MFA engine settings ('Conda Path') or via the VOXKIT_CONDA_PATH environment variable."
    )


def ensure_dictionary_downloaded(
    dictionary_name: str = "english_us_arpa", conda_path: str | None = None
) -> None:
    """Ensure the specified MFA dictionary is downloaded.

    Args:
        dictionary_name: Name of the dictionary to download (default: "english_us_arpa").
        conda_path: Optional user-configured path to the conda executable.

    Raises:
        AssertionError: If dictionary download fails and dictionary is not available.
    """
    prefix, extra_env = _mfa_invocation(conda_path)
    run_env = {**os.environ, **extra_env}
    download_cmd = [*prefix, "model", "download", "dictionary", dictionary_name]

    print(f"[mfa] Ensuring dictionary '{dictionary_name}' is downloaded...")
    result = subprocess.run(
        download_cmd, capture_output=True, text=True, env=run_env, **_no_window()
    )

    # Check if dictionary is available (either just downloaded or already present)
    # MFA returns success if already downloaded, or downloads successfully
    if result.returncode != 0:
        # Try to list dictionaries to check if it's already available
        list_cmd = [*prefix, "model", "list", "dictionary"]
        list_result = subprocess.run(
            list_cmd, capture_output=True, text=True, env=run_env, **_no_window()
        )
        assert dictionary_name in list_result.stdout, (
            f"Dictionary '{dictionary_name}' is not available. "
            f"Download failed with: {result.stderr}"
        )
        print(f"[mfa] Dictionary '{dictionary_name}' already available.")
    else:
        print(f"[mfa] Dictionary '{dictionary_name}' is ready.")


def _ensure_mfa_server_running(conda_path: str | None = None) -> None:
    """Start MFA's bundled Postgres server on Windows. No-op elsewhere.

    Why: MFA 3.3.x's SQLite backend has a multiprocessing race in
    `collect_alignments` on Windows where the `word_interval_temp` staging
    table goes missing between worker connections, aborting the run with
    "no such table: word_interval_temp". The Postgres backend (also bundled
    in the aligner conda env) does not have this race. macOS and Linux are
    not affected by the SQLite race in practice, so this is gated to win32
    to avoid changing their behavior.
    """
    if sys.platform != "win32":
        return

    prefix, extra_env = _mfa_invocation(conda_path)
    run_env = {**os.environ, **extra_env}
    # Both calls are idempotent: `init` errors if the server dir already exists,
    # `start` errors if it's already running. Either error state is the goal,
    # so we ignore returncodes and only guard against true failures (timeout,
    # missing conda). If the server genuinely can't come up, alignment will
    # fall back to SQLite and surface its own error via the existing path.
    for sub in (("server", "init"), ("server", "start")):
        try:
            subprocess.run(
                [*prefix, *sub],
                capture_output=True,
                text=True,
                timeout=60,
                env=run_env,
                **_no_window(),
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass


def run_mfa_align(
    corpus_dir,
    model_path,
    output_dir,
    dictionary_name="english_us_arpa",
    eval_dir=None,
    conda_path=None,
) -> None:
    """
    Run MFA align command with the provided arguments.

    Args:
        corpus_dir: Path to the corpus directory.
        model_path: Path to the acoustic model.
        output_dir: Path to output TextGrids.
        dictionary_name: MFA dictionary name (default: "english_us_arpa").
        eval_dir: Optional path to reference alignments for evaluation.
        conda_path: Optional user-configured path to the conda executable.

    Raises:
        AssertionError: If dictionary is not available.
        subprocess.CalledProcessError: If MFA alignment fails.
    """
    # Ensure dictionary is downloaded
    ensure_dictionary_downloaded(dictionary_name, conda_path=conda_path)
    _ensure_mfa_server_running(conda_path=conda_path)

    prefix, extra_env = _mfa_invocation(conda_path)
    cmd = [*prefix, "align", corpus_dir, dictionary_name, model_path, output_dir, "--clean"]

    if eval_dir:
        cmd.append("--reference_alignments")
        cmd.append(eval_dir)

    try:
        print(f"[mfa.run_mfa_align] Running MFA align with command: {' '.join(cmd)}")
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, **extra_env},
            **_no_window(),
        )
        print("[mfa.run_mfa_align] MFA alignment completed successfully.")
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.strip() if e.stderr else "(no output captured)"
        print(f"[mfa.run_mfa_align] MFA alignment failed:\n{stderr_msg}")
        raise RuntimeError(f"MFA alignment failed (exit {e.returncode}):\n{stderr_msg}") from e


def run_mfa_adapt(
    corpus_dir,
    base_model_path,
    output_model_path,
    dictionary_name="english_us_arpa",
    num_iterations=1,
    conda_path=None,
) -> None:
    """
    Run MFA adapt command with the provided arguments.

    Args:
        corpus_dir (str): Path to the corpus directory (must contain audio + TextGrid files).
        base_model_path (str): Path to the base model file.
        output_model_path (str): Path where the adapted model will be saved.
        dictionary_name (str): Name of the dictionary to use (default: "english_us_arpa").
        num_iterations (int): Number of adaptation iterations.
        conda_path (str | None): Optional user-configured path to the conda executable.

    Raises:
        AssertionError: If dictionary is not available.
        subprocess.CalledProcessError: If MFA adaptation fails.
    """
    # Ensure dictionary is downloaded
    ensure_dictionary_downloaded(dictionary_name, conda_path=conda_path)
    _ensure_mfa_server_running(conda_path=conda_path)

    prefix, extra_env = _mfa_invocation(conda_path)
    cmd = [
        *prefix,
        "adapt",
        corpus_dir,
        dictionary_name,
        base_model_path,
        output_model_path,
        "--num_iterations",
        str(num_iterations),
        "--clean",  # Add clean flag to avoid cache issues
    ]

    try:
        print(f"[mfa.run_mfa_adapt] Running MFA adapt with command: {' '.join(cmd)}")
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, **extra_env},
            **_no_window(),
        )
        print("[mfa.run_mfa_adapt] MFA adaptation completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[mfa.run_mfa_adapt] MFA adaptation failed with error: {e}")
        if e.stderr:
            print(f"[mfa.run_mfa_adapt] Error output: {e.stderr}")
        raise


def download_acoustic_model(release_path, output_file):
    """
    Download an MFA acoustic model using the github releases api.

    For example, release_path = acoustic-spanish_mfa-v3.3.0/spanish_mfa.zip becomes url
    "https://github.com/MontrealCorpusTools/mfa-models/releases/download/acoustic-spanish_mfa-v3.3.0/spanish_mfa.zip"
    """
    url = f"https://github.com/MontrealCorpusTools/mfa-models/releases/download/{release_path}"
    cmd = ["curl", "-L", "-o", output_file, url]
    try:
        print(f"[mfa.download_acoustic_model] Downloading model from {url} to {output_file}")
        subprocess.run(cmd, check=True, **_no_window())
        print("[mfa.download_acoustic_model] Model downloaded successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[mfa.download_acoustic_model] Model download failed with error: {e}")
        raise


if __name__ == "__main__":
    # Example model download
    download_acoustic_model(
        "acoustic-spanish_mfa-v3.3.0/spanish_mfa.zip",
        "spanish_mfa.zip",
    )
    download_acoustic_model(
        "acoustic-english_us_arpa-v3.0.0/english_us_arpa.zip",
        "english_us_arpa.zip",
    )
