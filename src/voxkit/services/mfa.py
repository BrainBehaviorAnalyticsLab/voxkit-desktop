import subprocess


def ensure_dictionary_downloaded(dictionary_name: str = "english_us_arpa") -> None:
    """Ensure the specified MFA dictionary is downloaded.

    Args:
        dictionary_name: Name of the dictionary to download (default: "english_us_arpa").

    Raises:
        AssertionError: If dictionary download fails and dictionary is not available.
    """
    download_cmd = [
        "conda",
        "run",
        "-n",
        "aligner",
        "mfa",
        "model",
        "download",
        "dictionary",
        dictionary_name,
    ]

    print(f"[mfa] Ensuring dictionary '{dictionary_name}' is downloaded...")
    result = subprocess.run(download_cmd, capture_output=True, text=True)

    # Check if dictionary is available (either just downloaded or already present)
    # MFA returns success if already downloaded, or downloads successfully
    if result.returncode != 0:
        # Try to list dictionaries to check if it's already available
        list_cmd = [
            "conda",
            "run",
            "-n",
            "aligner",
            "mfa",
            "model",
            "list",
            "dictionary",
        ]
        list_result = subprocess.run(list_cmd, capture_output=True, text=True)
        assert dictionary_name in list_result.stdout, (
            f"Dictionary '{dictionary_name}' is not available. "
            f"Download failed with: {result.stderr}"
        )
        print(f"[mfa] Dictionary '{dictionary_name}' already available.")
    else:
        print(f"[mfa] Dictionary '{dictionary_name}' is ready.")


def run_mfa_align(
    corpus_dir, model_path, output_dir, dictionary_name="english_us_arpa", eval_dir=None
) -> None:
    """
    Run MFA align command with the provided arguments.

    Args:
        corpus_dir: Path to the corpus directory.
        model_path: Path to the acoustic model.
        output_dir: Path to output TextGrids.
        dictionary_name: MFA dictionary name (default: "english_us_arpa").
        eval_dir: Optional path to reference alignments for evaluation.

    Raises:
        AssertionError: If dictionary is not available.
        subprocess.CalledProcessError: If MFA alignment fails.
    """
    # Ensure dictionary is downloaded
    ensure_dictionary_downloaded(dictionary_name)

    cmd = [
        "conda",
        "run",
        "-n",
        "aligner",
        "mfa",
        "align",
        corpus_dir,
        dictionary_name,
        model_path,
        output_dir,
        "--clean",  # Add clean flag to avoid cache issues
    ]

    if eval_dir:
        cmd.append("--reference_alignments")
        cmd.append(eval_dir)

    try:
        print(f"[mfa.run_mfa_align] Running MFA align with command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        print("[mfa.run_mfa_align] MFA alignment completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[mfa.run_mfa_align] MFA alignment failed with error: {e}")
        raise


def run_mfa_adapt(
    corpus_dir,
    base_model_path,
    output_model_path,
    dictionary_name="english_us_arpa",
    num_iterations=1,
) -> None:
    """
    Run MFA adapt command with the provided arguments.

    Args:
        corpus_dir (str): Path to the corpus directory (must contain audio + TextGrid files).
        base_model_path (str): Path to the base model file.
        output_model_path (str): Path where the adapted model will be saved.
        dictionary_name (str): Name of the dictionary to use (default: "english_us_arpa").
        num_iterations (int): Number of adaptation iterations.

    Raises:
        AssertionError: If dictionary is not available.
        subprocess.CalledProcessError: If MFA adaptation fails.
    """
    # Ensure dictionary is downloaded
    ensure_dictionary_downloaded(dictionary_name)

    cmd = [
        "conda",
        "run",
        "-n",
        "aligner",
        "mfa",
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
        subprocess.run(cmd, check=True, capture_output=True, text=True)
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
        subprocess.run(cmd, check=True)
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
