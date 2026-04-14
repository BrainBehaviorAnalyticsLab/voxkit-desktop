<p align="center">
  <img src="assets/header_image.png" alt="VoxKit" width="350">
</p>

<p align="center">
  <a href="https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/releases/latest"><img src="https://img.shields.io/github/v/release/BrainBehaviorAnalyticsLab/PyPLLR_GUI?label=Release&style=flat-square" alt="Release"></a>
  <a href="https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/releases"><img src="https://img.shields.io/github/downloads/BrainBehaviorAnalyticsLab/PyPLLR_GUI/total?style=flat-square" alt="Downloads"></a>
  <img src="./assets/coverage.svg" alt="Coverage">
</p>

<p align="center">
  <a href="https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/actions/workflows/tests-ubuntu.yml"><img src="https://img.shields.io/github/actions/workflow/status/BrainBehaviorAnalyticsLab/PyPLLR_GUI/tests-ubuntu.yml?branch=main&label=Ubuntu&logo=ubuntu&style=flat-square" alt="Ubuntu Tests"></a>
  <a href="https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/actions/workflows/tests-macos.yml"><img src="https://img.shields.io/github/actions/workflow/status/BrainBehaviorAnalyticsLab/PyPLLR_GUI/tests-macos.yml?branch=main&label=macOS&logo=apple&style=flat-square" alt="macOS Tests"></a>
  <a href="https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/actions/workflows/tests-windows.yml"><img src="https://img.shields.io/github/actions/workflow/status/BrainBehaviorAnalyticsLab/PyPLLR_GUI/tests-windows.yml?branch=main&label=Windows&logo=windows&style=flat-square" alt="Windows Tests"></a>
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
- [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) – Version control
- [uv](https://docs.astral.sh/uv/getting-started/installation/) – Python package manager
- [invoke](https://www.pyinvoke.org/installing.html) – Task runner (installed via `uv tool install invoke`)

**Getting-started:**
```bash
# Clone repository
git clone https://github.com/BrainBehaviorAnalyticsLab/voxkit-desktop.git
cd voxkit-desktop

# As easy as...

# (1) Browse developer commands
invoke --list

# (2) Install precommit and initialize environment
invoke setup

# (3) Start app (developer mode)
invoke dev
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
