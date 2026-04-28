# VoxKit — Interspeech 2026 Release Readiness Checklist

Defines completeness criteria for VoxKit prior to Interspeech 2026, where Nina and Michael will present using the app.

---

## 1. Dataset Registration

- [ ] Empty dataset fails with a descriptive popup
- [ ] Valid dataset registers successfully
- [ ] Valid dataset with optional hand alignments registers and ingests alignments
- [ ] Cached dataset is properly ingested
- [ ] `transcribed` flag is verified at registration:
  - [ ] Marked transcribed but isn't → fails with descriptive popup
  - [ ] Not marked transcribed but is → fails with descriptive popup
- [ ] DeID label works for a valid dataset
- [ ] Invalid folder structures are caught at registration time
- [ ] Folder with valid structure but no audio files (determined by extension) fails registration

## 2. Dataset Bundle Lifecycle

Registration ingests a dataset into a VoxKit-compatible bundle. One user registers; others can import the bundle and skip validation/scanning/copying.

- [ ] Import a registered dataset bundle (skips validation/scanning/copy)
- [ ] Export a dataset bundle
- [ ] Delete a dataset

## 3. Dataset Analysis

Analysis captures metadata via a class instantiated at registration time.

- [ ] Analyze a dataset using 2+ methods
- [ ] Metadata is captured correctly per method

## 4. Model Registration

Engines in scope: **W2TG** and **MFA**. Test 2 models per engine.

- [ ] Register a model (×2 per engine)
- [ ] Import a model (×2 per engine)
- [ ] Export a model (×2 per engine)
- [ ] Delete a model (×2 per engine)

## 5. Transcription Pipeline

- [ ] Transcribe audio with each of the 2 engine options
- [ ] Custom settings: notable combinations either function correctly or give clear error feedback
- [ ] Run transcription on every registered dataset from §1
- [ ] Run transcription on every imported variant from §2
- [ ] `transcribed = false` → transcription succeeds
- [ ] `transcribed = true` → transcription fails (does not overwrite existing transcript files)

## 6. Aligner Training

- [ ] Train a new aligner using hand alignments, per engine
- [ ] Validate different settings combinations (function correctly or give clear error feedback)

## 7. Alignment Generation

- [ ] Generate alignments for each dataset variant from import
- [ ] Generate alignments using the newly trained models (edge-case coverage)

## 8. Alignment Comparison Plots

- [ ] Generate plots comparing alignment sets of the same dataset
- [ ] All comparison-plot functionality exercised

## 9. Praat-Style Alignment Viewer

- [ ] View alignments in Praat-style visualization

## 10. PLLR Score Plotting

- [ ] Plot PLLR scores
- [ ] Settings combinations function correctly or provide clear error feedback
