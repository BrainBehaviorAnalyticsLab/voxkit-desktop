# PyPLLR GUI

A modern PyQt6-based graphical user interface for phonetic alignment and PLLR (Phoneme-Level Likelihood Ratios) score extraction. This application provides an intuitive workflow for researchers working with speech data.

## Features

- **🎯 Intuitive Workflow**: Step-by-step interface with numbered navigation (1️⃣ Train Aligner → 2️⃣ Predict Alignments → 3️⃣ Extract PLLR Scores)
- **🔄 Multiple Alignment Methods**:
  - **MFA (Montreal Forced Aligner)**: Traditional acoustic model-based alignment
  - **Wav2TextGrid**: Neural network-based alignment using speech embeddings
- **📊 PLLR Score Extraction**: Automatic extraction of phoneme-level likelihood ratios
- **⚡ Background Processing**: Non-blocking operations with progress feedback
- **🎨 Modern UI**: Clean, professional interface with dark theme

## Prerequisites

### System Requirements
- **Python**: 3.11 or higher
- **Operating System**: macOS, Windows, or Linux
- **Memory**: At least 8GB RAM recommended
- **Storage**: ~5GB free space for models and dependencies

### Required Software
- **uv**: Modern Python package manager (`pip install uv`)
- **Conda/Miniconda**: For MFA environment management

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd PyPLLR_GUI
```

### 2. Install Dependencies
```bash
# Install Python dependencies
uv sync
```

### 3. Set Up MFA

(SEE => https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html)

## Usage

### Launch the Application
```bash
uv run main.py
```

### Workflow Overview

#### 1️⃣ Train Aligner (Coming Soon)
- Training interface for custom acoustic models
- Currently displays placeholder content

#### 2️⃣ Predict Alignments
1. **Select Alignment Model**:
   - **MFA**: Traditional acoustic model alignment (requires conda environment)
   - **Wav2TextGrid**: Neural network-based alignment (no setup required)

2. **Set Paths**:
   - **Data Corpus Path**: Directory containing WAV files and transcripts
   - **TextGrid Output Path**: Where alignment results will be saved

3. **Run Alignment**:
   - Click "Predict Alignments"
   - Monitor progress in the status area
   - Results saved as TextGrid files

#### 3️⃣ Extract PLLR Scores
1. **Set Input Paths**:
   - **TextGrid Path**: Directory containing alignment TextGrid files
   - **Wav/Lab Path**: Directory containing corresponding WAV files

2. **Set Output Path**:
   - **Output Path**: Where PLLR scores will be saved

3. **Extract Scores**:
   - Click "Extract PLLR"
   - Generates CSV files with phoneme-level and frame-level probabilities

## Data Format Requirements

### For Alignment (Step 2)
```
corpus_directory/
├── speaker1/
│   ├── audio1.wav
│   ├── audio1.lab  # Transcript text
│   ├── audio2.wav
│   └── audio2.lab
└── speaker2/
    ├── audio3.wav
    └── audio3.lab
```

### For PLLR Extraction (Step 3)
```
textgrid_directory/
├── audio1.TextGrid  # From alignment step
├── audio2.TextGrid
└── audio3.TextGrid

wav_directory/
├── audio1.wav
├── audio2.wav
└── audio3.wav
```

## Output Files

### Alignment Output
- **TextGrid files**: Praat-compatible alignment files with phoneme timestamps

### PLLR Output
- **phonewise_proba.csv**: Phoneme-level likelihood ratios
- **framewise_proba.csv**: Frame-level probability distributions

## Troubleshooting

### Common Issues

#### MFA Alignment Fails
**Error**: `Could not find a model named "english_us_arpa"`
**Solution**: Ensure MFA models are downloaded:
```bash
conda run -n aligner mfa model download acoustic english_us_arpa
conda run -n aligner mfa model download dictionary english_us_arpa
```

#### Import Errors
**Error**: `ModuleNotFoundError` for torch/torchaudio
**Solution**: Install specific versions:
```bash
uv pip install torch==2.8.0 torchaudio==2.8.0
```

#### GUI Won't Start
**Error**: PyQt6 import issues
**Solution**: Reinstall dependencies:
```bash
uv sync --reinstall
```

#### Memory Issues
**Problem**: Application crashes with large datasets
**Solution**:
- Process data in smaller batches
- Ensure at least 8GB RAM available
- Close other memory-intensive applications

### Getting Help
1. Check the status messages in the GUI for specific error details
2. Verify all paths exist and are accessible
3. Ensure conda environment is properly activated for MFA operations

## Development

### Project Structure
```
PyPLLR_GUI/
├── main.py              # Main application code
├── pyproject.toml       # Project configuration
├── README.md           # This file
└── .venv/              # Virtual environment (created by uv)
```

### Key Dependencies
- **PyQt6**: GUI framework
- **PyPLLRComputer**: PLLR score extraction
- **Wav2TextGrid**: Neural alignment
- **Montreal Forced Aligner**: Traditional alignment
- **torch/torchaudio**: Neural network backend

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[TODO: Add license information here]

## Citation

If you use this software in your research, please cite:

```
[TODO: Add citation details here]
```

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check the troubleshooting section above
- Review the dependency documentation for PyPLLRComputer and Wav2TextGrid
