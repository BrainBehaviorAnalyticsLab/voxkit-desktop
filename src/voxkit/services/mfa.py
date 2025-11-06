"""
Until compatible exports are avalible through the MFA package this will serve as the alterative 
entrypoint for MFA logic bootstrapping the cli
"""

import logging
import subprocess
from typing import Optional


def run_mfa_adapt(
    corpus_dir: str,
    dictionary_path: str,
    acoustic_model_path: str,
    output_model_path: str,
    timeout: Optional[float] = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run the Montreal Forced Aligner 'adapt' subcommand as a subprocess.

    Raises:
      FileNotFoundError: if the MFA CLI is not available on PATH.
      subprocess.CalledProcessError: if the command exits with non-zero status.
      subprocess.TimeoutExpired: if the command times out.
    """
    cmd = [
        "conda",
        "run",
        "-n",
        "aligner",
        "mfa",
        "adapt",
        corpus_dir,
        dictionary_path,
        acoustic_model_path,
        output_model_path,
        "--clean",
        "--clean",  # wipe any previous broken temp files
        "-t",
        "/tmp/mfa_adapt_tmp",  # explicit temporary directory
        "--output_directory",
        "/tmp/mfa_adapt_output",  # explicit output directory,
    ]
    logging.debug("Running MFA adapt command: %s", " ".join(cmd))
    completed = subprocess.run(
        cmd,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.STDOUT if capture_output else None,
        text=True,
        timeout=timeout,
        check=True,
    )

    if capture_output:
        logging.debug("MFA adapt output:\n%s", completed.stdout)

    return completed


def run_mfa_evaluate(
    corpus_dir: str,
    dictionary_path: str,
    acoustic_model_path: str,
    output_model_path: str,
    timeout: Optional[float] = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run the Montreal Forced Aligner 'evaluate' subcommand as a subprocess.
    """
    pass
    
