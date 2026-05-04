# Implementation Spec: nnU-Net v2 dataset.json Generator for Lung Lower Lobe Right Segmentation

## Overview
Generate a `dataset.json` file for nnU-Net v2 that describes a single-class lung lower lobe right segmentation task using DRR (Digital Reconstructed Radiograph) modality. The dataset follows nnU-Net v2 directory structure with training images/labels and test images already organized.

## Observed Facts
- Dataset root: `<dataset_root>/Dataset001_LungLobeRight/`
- Subdirectories present: `imagesTr/`, `labelsTr/`, `imagesTs/`
- Single foreground class: `lung_lower_lobe_right`
- Modality: DRR (not CT)
- Format: nnU-Net v2
- Request language: Chinese; output should be implementable in any language

## Constraints & Requirements

### 1. **Case ID Alignment Rule**
- Training images and labels must be paired by case identifier
- **Constraint**: Worker must establish and document the exact matching rule (e.g., `case_001_0000.nii.gz` ↔ `case_001.nii.gz`)
- **Constraint**: All training cases must have exactly one corresponding label file; mismatches must fail loudly

### 2. **File Discovery & Naming**
- **Constraint**: Worker must handle file suffix variations (`.nii.gz`, `.nii`, `.mha`, etc.) consistently
- **Constraint**: nnU-Net v2 convention uses `_0000`, `_0001` suffixes for multi-channel images; DRR is single-channel, so likely `_0000` only
- **Constraint**: Worker must not assume file extensions; must scan actual directory

### 3. **Test Set Handling**
- `imagesTs/` directory exists but **unclear whether test cases should be included in dataset.json**
- **Open Question**: Does nnU-Net v2 dataset.json include `test` key with test case entries, or is it training/validation only?

### 4. **Path Representation in JSON**
- **Open Question**: Should paths in dataset.json be absolute, relative to dataset root, or relative to the JSON file location?
- **Open Question**: Should paths use forward slashes (`/`) or be OS-agnostic?

### 5. **Schema Fields for nnU-Net v2**
Required fields to clarify:
- `channel_names`: How to represent single DRR channel (e.g., `{"0": "DRR"}` or similar)?
- `labels`: Mapping of label indices to class names (e.g., `{"0": "background", "1": "lung_lower_lobe_right"}`)?
- `numTraining`: Count of training cases
- `file_ending`: Expected file suffix (e.g., `.nii.gz`)?
- **Open Question**: Exact schema version identifier field (if any)?
- **Open Question**: Are there required fields for spacing, intensity normalization, or modality metadata?

### 6. **Write Safety**
- **Constraint**: If `dataset.json` already exists, worker must decide: overwrite, skip, or error
- **Constraint**: JSON must be valid and parseable; no partial writes on failure
- **Constraint**: Worker should validate that all referenced files exist before writing JSON

## Implementation Approach

### Phase 1: Discovery
1. Scan `imagesTr/` directory; collect all image files and their base names
2. Scan `labelsTr/` directory; collect all label files and their base names
3. Establish case ID extraction rule from filenames
4. Validate 1:1 pairing of images to labels; report any orphans

### Phase 2: Schema Construction
1. Determine nnU-Net v2 dataset.json schema version and required fields
2. Build `channel_names` entry for single DRR modality
3. Build `labels` entry: `{"0": "background", "1": "lung_lower_lobe_right"}`
4. Populate `numTraining` from validated case count
5. Decide on path format (absolute vs. relative)

### Phase 3: Test Set Decision
1. Scan `imagesTs/` directory
2. **Await decision**: Include test cases in JSON or omit?

### Phase 4: Validation & Write
1. Validate all image and label file paths resolve
2. Validate JSON schema against nnU-Net v2 specification
3. Write `dataset.json` with appropriate error handling

## Risks & Unsafe Actions
- **Risk**: Silently mismatching training images to wrong labels if case ID extraction is incorrect
- **Risk**: Overwriting existing `dataset.json` without backup
- **Risk**: Including non-existent file paths in JSON, causing downstream nnU-Net failures
- **Risk**: Incorrect channel or label indexing causing training pipeline errors

---

```json
{
  "assumptions": [
    "nnU-Net v2 dataset.json is the target format (not v1)",
    "Single-channel DRR images use _0000 suffix convention",
    "Training cases have exactly one image and one label file per case",
    "Case IDs can be extracted from filename stems (before suffix)",
    "Background class is implicitly index 0; foreground is index 1",
    "Dataset root and subdirectories are readable and contain only valid data files"
  ],
  "risks": [
    "CRITICAL: Case ID mismatch between images and labels will corrupt training data; must validate 1:1 pairing before JSON generation",
    "CRITICAL: Incorrect path format in JSON (absolute vs. relative) may cause nnU-Net to fail to locate files",
    "CRITICAL: Overwriting existing dataset.json without backup is irreversible",
    "HIGH: File suffix variations (.nii.gz vs .nii vs .mha) must be handled consistently",
    "HIGH: Test set inclusion/exclusion in JSON is unclear and may cause downstream errors",
    "MEDIUM: Channel naming convention for DRR modality is not specified; may need custom metadata"
  ],
  "open_questions": [
    "Does nnU-Net v2 dataset.json include a 'test' key with test case entries, or only training/validation?",
    "Should paths in dataset.json be absolute, relative to dataset root, or relative to JSON file location?",
    "What is the exact nnU-Net v2 dataset.json schema version and all required top-level fields?",
    "How should single-channel DRR modality be represented in 'channel_names' field?",
    "Are there required fields for image spacing, intensity normalization, or modality-specific metadata?",
    "What is the policy for handling existing dataset.json: overwrite, skip, or error?",
    "What file suffix(es) are present in imagesTr/, labelsTr/, imagesTs/ directories?",
    "Is there a specific case ID naming convention already in use, or should worker infer from directory contents?"
  ]
}
```