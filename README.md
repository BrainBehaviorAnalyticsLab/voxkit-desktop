# 🌉 VoxKit
[![Release](https://img.shields.io/github/v/release/BrainBehaviorAnalyticsLab/PyPLLR_GUI?label=Latest%20Release)](https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/releases/latest) [![Downloads](https://img.shields.io/github/downloads/BrainBehaviorAnalyticsLab/PyPLLR_GUI/total)](https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/releases) [![Tests](https://img.shields.io/github/actions/workflow/status/BrainBehaviorAnalyticsLab/PyPLLR_GUI/tests.yml?branch=main&label=Tests)](https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI/actions/workflows/tests.yml) [![Project Management](https://img.shields.io/badge/Project-Jira%20Board-0052CC?logo=jira)](https://voxkit.atlassian.net/jira/software/projects/VOX/boards/2/) [![Code Quality](https://img.shields.io/github/actions/workflow/status/BrainBehaviorAnalyticsLab/PyPLLR_GUI/code-quality.yml?branch=main&label=Code%20Quality)]

---

Providing cross-functional Speech Pathology research teams with the capability to connect their researchers with state of the art speech analysis tools and forced alignment. Effectively bridging the gap between cutting edge AI/ML capability and clinical applications in speech pathology.

---

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

**Orientation:**

- See [ARCHITECTURE](./ARCHITECTURE.md) for codebase terminology...
- See [RESEARCH](./RESEARCH.md) for papers and research background...
- See [CONTRIBUTING](./CONTRIBUTING.md) for contibution guidelines...
- See [Documentation](<TODO>) for the rendered documentation...

**Prerequisites:**
- [python](https://www.python.org/downloads/release/python-31114/) code language
- [uv](https://docs.astral.sh/uv/) package manager
- [git](https://git-scm.com/install/) version tracking

**Getting-started:**
```bash
# Clone repository
git clone https://github.com/BrainBehaviorAnalyticsLab/PyPLLR_GUI.git
cd PyPLLR_GUI

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
