# Implementation Spec: nnU-Net v2 dataset.json Generator

## Overview
Generate a single `dataset.json` file conforming to nnU-Net v2 schema for a lung lower-lobe-right segmentation task. The script must scan three directories (`imagesTr`, `labelsTr`, `imagesTs`), align training pairs by case ID, and produce valid v2 metadata without modifying source files.

---

## Observed Facts

1. **Directory structure** (provided):
   - `imagesTr/`: training images, named `case_NNN_0000.nii.gz`
   - `labelsTr/`: training labels, named `case_NNN.nii.gz`
   - `imagesTs/`: test images, named `case_NNN_0000.nii.gz`

2. **File naming pattern**:
   - Training images: `case_001_0000.nii.gz`, `case_002_0000.nii.gz`
   - Training labels: `case_001.nii.gz`, `case_002.nii.gz`
   - Test images: `case_101_0000.nii.gz`
   - Suffix `_0000` indicates channel 0 (single modality)

3. **Task metadata**:
   - Single foreground class: `lung_lower_lobe_right`
   - Modality: DRR (not CT)
   - Format: `.nii.gz`

4. **Output location**: `dataset.json` should be written to `<dataset_root>/Dataset001_LungLobeRight/`

---

## Implementation Constraints

### Case ID Alignment Rule
- Extract case ID from filename stem (e.g., `case_001` from `case_001_0000.nii.gz`)
- A training pair is valid only if **both** `imagesTr/case_NNN_0000.nii.gz` **and** `labelsTr/case_NNN.nii.gz` exist
- Unpaired images or labels must be skipped with a warning log

### Path Representation in JSON
- Paths in `dataset.json` must be **relative to dataset root** or **absolute**
  - *(Open question: which convention does nnU-Net v2 expect?)*
- Example candidates:
  - Relative: `imagesTr/case_001_0000.nii.gz`
  - Absolute: `/full/path/to/Dataset001_LungLobeRight/imagesTr/case_001_0000.nii.gz`

### Test Set Inclusion
- Determine whether `imagesTs` cases should appear in `dataset.json` under a `test` key or remain omitted
  - *(Open question: nnU-Net v2 schema requirement)*

### Write Safety
- If `dataset.json` already exists, define behavior:
  - Overwrite silently?
  - Overwrite with backup?
  - Raise error and abort?
  - *(Open question: policy not specified)*

---

## nnU-Net v2 Schema Fields (To Verify)

The script must produce a JSON object with at minimum:

```
{
  "channel_names": { ... },
  "labels": { ... },
  "numTraining": <int>,
  "file_ending": ".nii.gz",
  "training": [ ... ],
  "test": [ ... ] or omitted,
  ...
}
```

**Required clarifications**:

1. **`channel_names`**: Should map channel indices to modality names
   - Example: `{"0": "DRR"}` or `{"0": "drr"}`?
   - *(Open question: naming convention and case sensitivity)*

2. **`labels`**: Maps label integer to class name
   - Example: `{"0": "background", "1": "lung_lower_lobe_right"}`?
   - Should background always be `0`?
   - *(Open question: exact schema and whether background must be explicit)*

3. **`training` array**: Each entry structure
   - Example: `{"image": "imagesTr/case_001_0000.nii.gz", "label": "labelsTr/case_001.nii.gz"}`?
   - Or: `{"image": ["imagesTr/case_001_0000.nii.gz"], "label": "labelsTr/case_001.nii.gz"}`?
   - *(Open question: single vs. multi-channel image representation)*

4. **`numTraining`**: Count of valid training pairs (after alignment check)

5. **`file_ending`**: Hardcoded to `".nii.gz"`

6. **Additional v2 fields**: Are there required fields like `description`, `reference`, `licence`, `release`, `tensorImageSize`, `modality`?
   - *(Open question: full v2 schema specification)*

---

## First Actions for Worker

1. **Validate input**:
   - Confirm `<dataset_root>/Dataset001_LungLobeRight/` exists and contains all three subdirectories
   - List all files in each directory and log counts

2. **Extract and align case IDs**:
   - Scan `imagesTr/` for files matching `case_*_0000.nii.gz`
   - Scan `labelsTr/` for files matching `case_*.nii.gz`
   - For each training image, verify corresponding label exists
   - Log any unpaired cases and exclude them

3. **Scan test set** (if applicable):
   - List all files in `imagesTs/` matching `case_*_0000.nii.gz`
   - Determine whether to include in JSON (pending schema clarification)

4. **Construct JSON object**:
   - Populate schema fields according to nnU-Net v2 spec (to be confirmed)
   - Use relative or absolute paths (to be confirmed)
   - Ensure valid JSON syntax

5. **Write output**:
   - Apply write-safety policy (to be confirmed)
   - Write to `<dataset_root>/Dataset001_LungLobeRight/dataset.json`
   - Validate output JSON is parseable

---

## Risks & Constraints

| Risk | Mitigation |
|------|-----------|
| Case ID mismatch (e.g., `case_001_0000.nii.gz` but `case_001_seg.nii.gz`) | Implement strict regex matching; log all unpaired files |
| Empty training set after alignment | Abort with clear error message; do not generate empty JSON |
| Incorrect path format in JSON | Verify against nnU-Net v2 documentation before writing |
| Overwriting existing `dataset.json` | Define and document overwrite policy before execution |
| Schema version mismatch (v1 vs. v2) | Explicitly target v2 fields; do not assume v1 compatibility |
| Non-standard file suffixes (e.g., `.nii` instead of `.nii.gz`) | Confirm all files use `.nii.gz`; skip or error on mismatches |

---

## Deliverable

- A Python script (or equivalent) that:
  - Takes `<dataset_root>` as a command-line argument or environment variable
  - Performs the alignment and validation steps above
  - Outputs `dataset.json` to the dataset root
  - Logs all decisions (paired cases, skipped files, schema choices)
  - Exits with non-zero status on critical errors

---

```json
{
  "assumptions": [
    "All training images follow pattern case_NNN_0000.nii.gz",
    "All training labels follow pattern case_NNN.nii.gz",
    "All test images follow pattern case_NNN_0000.nii.gz",
    "Case ID is extracted from filename stem before first underscore or file extension",
    "Single foreground class label is 1; background is 0",
    "DRR modality is represented as a single channel (index 0)",
    "dataset.json should be written to <dataset_root>/Dataset001_LungLobeRight/",
    "File format is always .nii.gz (no other suffixes present)"
  ],
  "risks": [
    "Unpaired training images and labels will silently corrupt the dataset if not detected; must validate alignment before JSON generation",
    "Overwriting existing dataset.json without backup or confirmation could destroy prior work",
    "Path representation (relative vs. absolute) affects nnU-Net v2 loader behavior; incorrect choice may cause runtime failures",
    "Test set inclusion in JSON is schema-dependent; including or excluding incorrectly may break nnU-Net v2 preprocessing",
    "Schema field names and structure differ between nnU-Net v1 and v2; using v1 defaults will produce invalid v2 JSON",
    "Empty training set (zero valid pairs) should abort, not produce minimal JSON"
  ],
  "open_questions": [
    "What is the exact nnU-Net v2 dataset.json schema? Specifically: required top-level keys, structure of 'training' and 'test' arrays, and any version/metadata fields?",
    "Should paths in JSON be relative to dataset root or absolute filesystem paths?",
    "Should the 'test' key be included in dataset.json, and if so, what is its structure?",
    "What is the correct naming and case convention for channel_names (e.g., 'DRR' vs. 'drr')?",
    "Must the 'labels' object explicitly include background (label 0), or only foreground classes?",
    "If dataset.json already exists, what is the overwrite policy: silent overwrite, backup, error, or prompt?",
    "Are there additional required v2 fields such as 'description', 'reference', 'licence', 'release', 'tensorImageSize', or 'modality'? If so, what are their expected values?",
    "Should the script validate that label files contain only values 0 and 1, or