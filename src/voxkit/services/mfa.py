import subprocess


def run_mfa_align(corpus_dir, model_path, output_dir, eval_dir=None) -> None:
    """
    Run MFA align command with the provided arguments.

    Args:
        args (List[str]): List of command-line arguments for MFA align.
    """

    cmd = [
        "conda",
        "run",
        "-n",
        "aligner",
        "mfa",
        "align",
        corpus_dir,
        "english_us_arpa",
        model_path,
        output_dir,
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
    """
    # First, ensure the dictionary is downloaded
    download_cmd = [
        "conda",
        "run",
        "-n",
        "aligner",
        "mfa",
        "model",
        "download",
        "dictionary",
        "english_us_arpa",
    ]

    try:
        print("[mfa.run_mfa_adapt] Ensuring dictionary is downloaded...")
        subprocess.run(download_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        print(
            "[mfa.run_mfa_adapt] Dictionary already downloaded or "
            "download failed (continuing anyway)"
        )

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
    Download an MFA acoustic model using the github releases ai  for example release_path = acoustic-spanish_mfa-v3.3.0/spanish_mfa.zip becomes url "https://github.com/MontrealCorpusTools/mfa-models/releases/download/acoustic-spanish_mfa-v3.3.0/spanish_mfa.zip"
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
   