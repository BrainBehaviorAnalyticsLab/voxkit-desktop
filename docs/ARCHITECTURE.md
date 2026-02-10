# Software Architecture

## 1. Purpose

This document describes the terminology, layout, and organizational patterns used in VoxKit. It serves as an onboarding guide for understanding the repository structure.

---

## 2. Terminology

> Custom terminology for this project. Technical accuracy matters only where distinction is necessary for development.

- **Dataset** — Audio samples organized in a speaker-directory structure
- **Engine** — A speech toolkit backend providing one or more tools (alignment, training, transcription)
- **Tool** — A modular capability provided by an engine (e.g., alignment, transcription)
- **Analyzer** — Extracts metadata from datasets at registration time, producing CSV summaries
- **Registration** — Adding an entity (dataset, model, etc.) to VoxKit storage

---

## 3. System Layers

VoxKit is organized into four primary layers:

### 3.1 GUI Layer (`voxkit.gui`)

PyQt6 presentation layer for user interactions.

- **pages/**: Main views (Datasets, Models, Pipeline)
- **components/**: Reusable widgets
- **frameworks/**: UI patterns (settings modals, categorical tables)
- **workers/**: QThread background workers for long operations

### 3.2 Storage Layer (`voxkit.storage`)

Persistence and CRUD operations for all entities.

- **datasets**: Dataset registration, metadata, validation
- **models**: Model metadata and file storage
- **alignments**: Alignment outputs per dataset
- **utils**: ID generation and path management

### 3.3 Engine Layer (`voxkit.engines`)

Abstraction for speech toolkit backends.

- Engines implement an abstract base class
- Each engine provides one or more tools
- Manager singleton for engine discovery

### 3.4 Analyzer Layer (`voxkit.analyzers`)

Dataset metadata extraction at registration time.

- Analyzers implement an abstract base class
- Produce CSV summaries stored with dataset
- Manager singleton for analyzer discovery

---

## 4. Architecture Pattern

VoxKit follows a **hybrid "unstructured state + signals"** pattern common in PyQt applications:

1. **Views directly access storage** — No intermediary controller
2. **Storage acts as the Model layer** — CRUD operations and persistence
3. **QThread workers for async** — Long operations use workers with pyqtSignal
4. **Distributed state** — State managed locally in pages, persisted via storage

**Communication Flow:**
- UI → Storage: Direct function calls
- Async: Workers emit signals → Views update
- Cross-page: Parent window calls `reload()` on tab switch

---

## 5. Storage Structure

```
~/.voxkit/
├── datasets/{dataset_id}/
│   ├── voxkit_dataset.json
│   ├── {analyzer}_summary.csv
│   ├── cache/
│   └── alignments/{alignment_id}/
└── {engine_id}/
    ├── train/{model_id}/
    └── {tool}/settings.json
```
