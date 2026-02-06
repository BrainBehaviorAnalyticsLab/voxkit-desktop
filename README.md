# 🌉 VoxKit

[![Project Management](https://img.shields.io/badge/Project-Jira%20Board-0052CC?logo=jira&style=flat-square)](https://voxkit.atlassian.net/jira/software/projects/VOX/boards/2/) 
[![Docs](https://img.shields.io/badge/Docs-Auto--Generated-blue?logo=readthedocs&style=flat-square)](https://voxkit-web.vercel.app/docs)

[![Release](https://img.shields.io/github/v/release/BrainBehaviorAnalyticsLab/PyPLLR_GUI?label=Latest%20Release&style=flat-square)](https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/releases/latest) 
[![Downloads](https://img.shields.io/github/downloads/BrainBehaviorAnalyticsLab/PyPLLR_GUI/total?style=flat-square)](https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/releases)

[![Tests](https://img.shields.io/github/actions/workflow/status/BrainBehaviorAnalyticsLab/PyPLLR_GUI/tests.yml?branch=main&label=Tests&style=flat-square)](https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/actions/workflows/tests.yml)
[![Code Quality](https://img.shields.io/github/actions/workflow/status/BrainBehaviorAnalyticsLab/PyPLLR_GUI/code-quality.yml?branch=main&label=Code%20Quality&style=flat-square)](https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/actions/workflows/code-quality.yml)

 > A PyQt-based platform that helps bridge AI/ML research and clinical speech-language pathology (SLP) applications. It provides an accessible interface to advanced audio analysis tools, such as forced alignment engines, while remaining flexible enough to support diverse research workflows.
---

## 🔎 Quick Links

- 🏗️ [ARCHITECTURE](./ARCHITECTURE.md) - Codebase terminology
- 🧪 [TESTING](./TESTING.md) - Testing strategy & coverage approach
- 📚 [RESEARCH](./RESEARCH.md) - Papers & research background
- ✍️ [CONTRIBUTING](./CONTRIBUTING.md) - Contribution guidelines
- 🌐 [Website](<TODO>) - Main site

## Project Structure

```
src/voxkit/
├── gui/                      # PyQt6 interface
│   ├── components/           # Reusable widgets
│   ├── frameworks/           # Dialog/modal frameworks
│   ├── pages/                # Main application pages
│   │   ├── datasets/         # Dataset management
│   │   ├── models/           # Model management
│   │   └── pipeline/         # Workflow stackers
│   └── workers/              # Background threads
├── engines/                  # Speech tool engines
│   ├── base.py               # Base engine interface
│   └── w2tg_engine.py        # Wav2TextGrid implementation
├── analyzers/                # Dataset information extraction
├── storage/                  # Data persistence
│   ├── datasets.py           # Dataset management
│   ├── models.py             # Model management
│   ├── alignments.py         # Alignment tracking
│   └── test/                 # Storage tests
└── services/                 # External services (non-engines)
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
