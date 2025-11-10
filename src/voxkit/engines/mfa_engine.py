# from typing import Literal, NotRequired, TypedDict

# from .api import AlignerOutputModel, AlignmentEngine, TrainerOutputModel


# class TrainerSettings(TypedDict):
#     """Comprehensive MFA training settings"""
#     # Base settings
#     base_model: str | None
#     eval_dataset: str | None
#     epochs: int
#     batch_size: int
#     use_gpu: bool

#     # MFA-specific training
#     num_iterations: NotRequired[int]  # Number of training iterations
#     max_gaussians: NotRequired[int]  # Maximum number of Gaussians
#     num_leaves: NotRequired[int]  # Number of leaves in decision tree
#     cluster_threshold: NotRequired[int]  # Clustering threshold
#     subset: NotRequired[int]  # Subset size for training
#     boost_silence: NotRequired[float]  # Silence boosting factor (default: 1.25)
#     power: NotRequired[float]  # Power for training (default: 0.25)

#     # Validation and checkpointing
#     validation_frequency: NotRequired[int]
#     save_frequency: NotRequired[int]


# class AlignmentSettings(TypedDict):
#     """Comprehensive MFA alignment settings"""
#     # Core settings
#     aligner_model: str | None  # Path or name of acoustic model
#     dictionary_path: NotRequired[str | None]  # Path to pronunciation dictionary
#     speaker_adaptation: NotRequired[bool]  # Use speaker adaptation (fMLLR)
#     use_gpu: NotRequired[bool]

#     # Beam search parameters
#     beam: NotRequired[int]  # Beam width (default: 10)
#     retry_beam: NotRequired[int]  # Retry beam width (default: 40, typically 4x beam)

#     # Speaker and file handling
#     speaker_characters: NotRequired[int]  # Chars from filename for speaker ID
#     audio_directory: NotRequired[str | None]  # Root directory for audio files

#     # Text processing
#     punctuation: NotRequired[str]  # Punctuation to strip (e.g., ":,.")
#     clitic_markers: NotRequired[str]  # Clitic markers
#     compound_markers: NotRequired[str]  # Compound word markers

#     # Silence and probability settings
#     initial_silence_probability: NotRequired[float]  # Silence at start (0.0-1.0)
#     final_silence_probability: NotRequired[float]  # Silence at end
#     final_non_silence_correction: NotRequired[float]

#     # Output settings
#     output_format: NotRequired[Literal["long_textgrid", "short_textgrid", "json"]]
#     include_original_text: NotRequired[bool]  # Include utterance text in output
#     textgrid_cleanup: NotRequired[bool]  # Clean up silences/compounds (default: True)

#     # G2P (Grapheme-to-Phoneme) for OOV words
#     g2p_model_path: NotRequired[str | None]  # G2P model for out-of-vocabulary words

#     # Processing options
#     clean: NotRequired[bool]  # Clean temp files before run
#     fine_tune: NotRequired[bool]  # Run extra fine-tuning stage
#     use_mp: NotRequired[bool]  # Use multiprocessing (default: True)
#     use_threading: NotRequired[bool]  # Use threading instead of multiprocessing
#     single_speaker: NotRequired[bool]  # Single speaker mode
#     num_jobs: NotRequired[int]  # Number of parallel jobs

#     # Advanced configuration
#     config_path: NotRequired[str | None]  # Path to YAML config file
#     phone_mapping: NotRequired[str | None]  # YAML for phone set mapping
#     disable_tokenization: NotRequired[bool]  # Disable pretrained tokenization

#     # Debug and logging
#     verbose: NotRequired[bool]
#     debug: NotRequired[bool]
#     quiet: NotRequired[bool]
#     overwrite: NotRequired[bool]  # Overwrite existing output files

# class MFAEngine(AlignmentEngine):
#     """Montreal Forced Aligner engine"""

#     def run_alignment(
#         self,
#         audio_root: str,
#         output_root: str,
#         model_id: str,
#         settings: AlignmentSettings,
#     ) -> AlignerOutputModel:
#         """Run MFA alignment with comprehensive settings"""
#         # Implementation here
#         pass

#     def train_aligner(
#         self,
#         audio_root: str,
#         model_id: str,
#         settings: TrainerSettings,
#     ) -> TrainerOutputModel:
#         """Train MFA acoustic model"""
#         # Implementation here
#         pass
