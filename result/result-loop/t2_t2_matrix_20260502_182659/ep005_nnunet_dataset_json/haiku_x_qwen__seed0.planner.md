# Planner Revision: Corrections & Missing Details for nnU-Net v2 dataset.json Generator

## What Worker_v1 Got Right

Worker_v1 correctly understood:
- The three-directory structure and the need to validate training image–label alignment
- The file suffix handling rules (_0000 removal for images, full suffix for labels)
- The relative path format with `./` prefix and forward slashes
- The core schema fields (channel_names, labels, numTraining, numTest, file_ending, training, test arrays)
- The no-partial-output constraint (fail validation → no JSON written)
- The single foreground class (lung_lower_lobe_right) and background (label 0)

## Critical Corrections & Clarifications

### 1. **Overwrite Policy — Now Specified**
The original request does **not** specify an overwrite policy. Worker_v1 assumed "refuse to overwrite," but this is a **design choice, not a fact from the prompt**. 

**Correction**: The worker should **not assume** a policy. Instead, the implementation spec must state:
- **Option A**: Refuse to overwrite (safest, requires user to manually delete)
- **Option B**: Silently overwrite (convenient, risky)
- **Option C**: Prompt the user (interactive, not suitable for batch scripts)

**For this spec**: Recommend **Option A (refuse)** as the default, but flag this as a decision point for the requester.

---

### 2. **Test Set Label Field — Clarify Omission**
Worker_v1 correctly noted the ambiguity but did not resolve it. The nnU-Net v2 convention (based on typical usage) is:
- Test entries should **omit the `label` field entirely** (not include `null`)
- This signals to nnU-Net that no ground truth is available

**Correction**: Update the schema example to show test entries without a label field.

---

### 3. **Empty Directory Handling — Must Be Specified**
Worker_v1 flagged this as open but did not propose a safe default.

**Correction**: The spec should state:
- If `imagesTr/` is empty → **fail with error** (cannot generate meaningful dataset.json)
- If `labelsTr/` is empty → **fail with error** (training set requires labels)
- If `imagesTs/` is empty → **warn but continue** (test set is optional; generate JSON with empty test array)

---

### 4. **Case ID Format Validation — Do Not Validate**
Worker_v1 asked whether to validate case ID format. The prompt provides **no format constraints**.

**Correction**: Accept any non-empty string as a valid case ID. Do **not** enforce numeric or alphanumeric patterns. This maximizes flexibility for user naming schemes.

---

### 5. **Duplicate Channel Suffixes — Reject Ambiguity**
Worker_v1 flagged the case of `case_001_0000.nii.gz` and `case_001_0001.nii.gz` in the same directory.

**Correction**: The spec should state:
- If multiple files with the same case ID but different channel suffixes are found (e.g., `_0000`, `_0001`), **fail with error** and report the ambiguity.
- nnU-Net v2 expects a single image entry per case in the training array, but the image field is a **list** (for multi-channel support). The spec must clarify: **are we handling single-channel only, or multi-channel?**

**From the prompt**: "单类前景" (single foreground class) and "模态是 DRR（不是 CT）" suggest **single modality, single channel**. But the image field is a list, implying multi-channel support is possible.

**Correction**: For this spec, assume **single-channel only** (one file per case in imagesTr/). If multiple channel files exist, report an error. If multi-channel support is needed in the future, that is a separate feature.

---

### 6. **Additional Metadata Fields — Not Required**
Worker_v1 asked about `description`, `reference`, `licence`, `release`, `modality`.

**Correction**: The prompt does **not** mention these fields. The planner spec in the prompt shows only the core fields. **Do not include optional metadata fields unless explicitly requested.** If the requester wants them, they should ask.

---

### 7. **Logging/Reporting — Specify Output**
Worker_v1 asked whether to output a summary.

**Correction**: The spec should state:
- Print a summary to stdout upon successful generation (e.g., "Generated dataset.json with 2 training cases, 1 test case").
- Print detailed error messages to stderr if validation fails.
- Do not write a separate log file unless requested.

---

### 8. **Path Separator Assumption — Correct**
Worker_v1 correctly assumed forward slashes for JSON portability. This is safe.

---

## Still Missing (Not in Prompt, Must Be Decided)

1. **Overwrite policy**: Refuse, overwrite, or prompt?
2. **Summary output**: Print to stdout or silent?
3. **Error reporting**: Detailed or minimal?
4. **Multi-channel support**: Single-channel only, or prepare for multi-channel?
5. **Case ID sorting**: Should training and test arrays be sorted by case ID, or preserve filesystem order?

---

## Worker Next Focus

Before writing implementation code, the worker should:

1. **Verify the overwrite policy** with the requester (or assume "refuse" and document it).
2. **Confirm single-channel assumption**: Is the dataset always single-channel DRR, or should the script support multi-channel images?
3. **Decide on summary output**: Should the script print a success message?
4. **Test the file scanning logic** on a small mock directory structure to ensure case ID extraction is correct.
5. **Prepare error messages** for all failure modes (missing labels, empty directories, duplicate channels, existing dataset.json).

---

```json
{
  "corrected_constraints": [
    "Every case in imagesTr/ must have a corresponding label in labelsTr/ with matching case ID; mismatches must be detected and reported before JSON generation.",
    "If dataset.json already exists, the script must refuse to overwrite it and report the conflict (overwrite policy: REFUSE).",
    "File suffixes must be handled correctly: strip '_0000.nii.gz' from training image filenames to derive case ID; strip '_0000.nii.gz' from test image filenames to derive case ID; strip '.nii.gz' from label filenames to derive case ID.",
    "All file paths in the JSON must be relative to the dataset root using './' prefix and forward slashes.",
    "The JSON must conform to nnU-Net v2 schema including channel_names, labels, numTraining, numTest, file_ending, training, and test arrays; do not include tensorImageSize.",
    "No partial output: if validation fails (e.g., missing labels, file format errors, empty imagesTr/, empty labelsTr/), do not write dataset.json.",
    "Test images must be included in the JSON under a 'test' array without a 'label' field (omit entirely, do not use null).",
    "Validate that all files end in .nii.gz; reject files with other extensions.",
    "If multiple files with the same case ID but different channel suffixes (e.g., _0000, _0001) are found in imagesTr/, fail with an error (single-channel assumption).",
    "Accept any non-empty string as a valid case ID; do not enforce format validation.",
    "If imagesTr/ or labelsTr/ is empty, fail with an error. If imagesTs/ is empty, warn but continue (generate JSON with empty test array).",
    "Print a summary message to stdout upon successful generation (e.g., 'Generated dataset.json with N training cases, M test cases').",
    "Print detailed error messages to stderr if validation fails."
  ],
  "still_missing": [
    "Exact overwrite policy for dataset.json if it already exists (assumed REFUSE, but should be confirmed with requester).",
    "Whether the dataset is strictly single-channel (DRR only) or should support multi-channel images in the future.",
    "Whether training and test arrays should be sorted by case ID or preserve filesystem order.",
    "Whether the script should accept a command-line argument to override the overwrite policy.",
    "Whether additional metadata fields (description, reference, licence, release, modality) are required in the schema (assumed NO based on prompt, but should be confirmed)."
  ],
  "worker_next_focus": [
    "Verify the overwrite policy decision with the requester; if not specified, document the REFUSE assumption in the spec.",
    "Confirm that the dataset is single-channel only (DRR modality, no multi-channel support needed).",
    "Design the file scanning and case ID extraction logic, then test it on a mock directory structure to ensure correctness.",
    "Prepare comprehensive error messages for all failure modes: missing labels, empty directories, duplicate channels, existing dataset.json, invalid file extensions.",
    "Decide on sorting order for training and test arrays (recommend: sort by case ID for reproducibility).",
    "Draft the exact stdout summary message format (e.g., 'Generated dataset.json with 2 training cases, 1 test case')."
  ]
}
```