<p align="center">
  <img src="assets/header_image.png" alt="VoxKit" width="350">
</p>

<p align="center">
  <a href="https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/releases/latest"><img src="https://img.shields.io/github/v/release/BrainBehaviorAnalyticsLab/PyPLLR_GUI?label=Release&style=flat-square" alt="Release"></a>
  <a href="https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/releases"><img src="https://img.shields.io/github/downloads/BrainBehaviorAnalyticsLab/PyPLLR_GUI/total?style=flat-square" alt="Downloads"></a>
  <img src="./coverage.svg" alt="Coverage">
</p>

<p align="center">
  <a href="https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/BrainBehaviorAnalyticsLab/PyPLLR_GUI/tests.yml?branch=main&label=Tests&style=flat-square" alt="Tests"></a>
  <a href="https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/actions/workflows/code-quality.yml"><img src="https://img.shields.io/github/actions/workflow/status/BrainBehaviorAnalyticsLab/PyPLLR_GUI/code-quality.yml?branch=main&label=Code%20Quality&style=flat-square" alt="Code Quality"></a>
  <a href="https://voxkit.atlassian.net/jira/software/projects/VOX/boards/2/"><img src="https://img.shields.io/badge/Project-Jira-0052CC?logo=jira&style=flat-square" alt="Jira"></a>
</p>

> [!IMPORTANT]
> VoxKit is currently in active development. Versions below **1.0.0** are considered **early preview releases** and should be treated as experimental. Your feedback during this development phase is invaluable! Please report issues, suggest improvements, and share your use cases. Thanks.

## Appendix

- [ARCHITECTURE](./docs/ARCHITECTURE.md) - System layers and terminology
- [RESEARCH](./docs/RESEARCH.md) - Papers and research background
- [CONTRIBUTING](./docs/CONTRIBUTING.md) - Contribution guidelines

## Project Structure

```
src/voxkit/
├── gui/           # PyQt6 interface (pages, components, workers)
├── engines/       # Speech toolkit backends
├── analyzers/     # Dataset metadata extraction
├── storage/       # Data persistence (datasets, models, alignments)
└── config/        # Application configuration
```


## Developers

**Prerequisites:**
- [python](https://www.python.org/downloads/release/python-31114/) code language
- [uv](https://docs.astral.sh/uv/) package manager
- [git](https://git-scm.com/install/) version tracking

**Getting-started:**
```bash
# Clone repository
git clone https://github.com/BrainBehaviorAnalyticsLab/voxkit-desktop.git
cd voxkit-desktop

# As easy as...

# (1) Browse developer commands
make help

# (2) Install precommit and initialize environment
make setup

# (3) Start app (developer mode)
make dev
```

---

## Citation

If you use VoxKit in your research, please cite:

```bibtex
<TODO>
```

**APA Format:**

```text
<TODO>
```

---

## License

See [LICENSE](LICENSE) for details...

---

>For questions or collaboration inquiries, please open an issue on GitHub.
