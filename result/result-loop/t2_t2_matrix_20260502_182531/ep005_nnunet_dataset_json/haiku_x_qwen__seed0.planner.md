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
- nnU-Net v2 supports multi-channel images, but the prompt specifies **single channel (DRR)**, so only `_0000` is expected.
- Reject any file matching `<case_id>_000[1-9].nii.gz` as an error condition.

---

### 6. **Additional Metadata Fields — Not Required**
Worker_v1 asked about `description`, `reference`, `licence`, `release`, `modality`. The original request does **not mention these**.

**Correction**: The spec should state that these fields are **not required** for this task. If the requester later needs them, they can be added. Do not invent defaults.

---

### 7. **Logging/Reporting — Specify Output**
Worker_v1 asked whether to output a summary. The prompt does not specify.

**Correction**: The spec should require:
- **Stdout**: Print a summary upon success (e.g., "Generated dataset.json with 2 training cases, 1 test case")
- **Stderr**: Print validation errors or warnings (e.g., "ERROR: case_001 in imagesTr/ has no label in labelsTr/")
- **Exit code**: 0 on success, non-zero on failure

---

### 8. **Numeric vs. String Label Keys — Confirmed as Strings**
Worker_v1 asked for confirmation. The planner spec already shows string keys (`"0"`, `"1"`).

**Correction**: Confirm that label keys **must be strings** in the JSON output (not integers). This is nnU-Net v2 convention.

---

### 9. **Path Separator — Use Forward Slashes**
Worker_v1 noted the ambiguity. The spec already assumes forward slashes for JSON portability.

**Correction**: Explicitly state: **Always use forward slashes (`/`) in JSON paths, regardless of OS.** This ensures portability across Linux, macOS, and Windows.

---

### 10. **Test Set Disjointness — Assume No Overlap**
Worker_v1 assumed training and test cases are disjoint. The prompt does **not explicitly state this**, but it is a reasonable assumption for a typical ML workflow.

**Correction**: State this as an assumption, but do **not validate** it (i.e., do not fail if a case ID appears in both `imagesTr/` and `imagesTs/`). If overlap occurs, include the case in both arrays and let nnU-Net handle it.

---

## Still Missing (Unresolvable Without Requester Input)

1. **Overwrite policy**: Refuse, overwrite, or prompt? → **Recommend refuse; flag for decision**
2. **Additional metadata fields**: Are `description`, `reference`, `licence`, `release`, `modality` required? → **Assume not required unless specified**
3. **Empty directory behavior**: Fail or warn? → **Specified above; fail for imagesTr/labelsTr/, warn for imagesTs/**
4. **Summary output format**: Exact wording and destination? → **Recommend stdout with case counts**

---

## Worker Next Focus

1. **Verify the overwrite policy** with the requester (or document the chosen default clearly).
2. **Finalize the empty directory rules** (fail vs. warn) and document them in the spec.
3. **Add explicit validation rules** for duplicate channel suffixes (reject `_000[1-9]` patterns).
4. **Confirm path separator handling** (always forward slashes in JSON).
5. **Define the success/error output format** (stdout summary, stderr errors, exit codes).
6. **Update the schema example** to show test entries without a label field.

---

```json
{
  "corrected_constraints": [
    "Every case in imagesTr/ must have a corresponding label in labelsTr/ with matching case ID; mismatches must be detected and reported before JSON generation.",
    "If dataset.json already exists, the script must refuse to overwrite it and report the conflict (overwrite policy: refuse by default).",
    "File suffixes must be handled correctly: strip '_0000' from training image filenames to derive case ID; reject any file with channel suffix _000[1-9] as an error (single channel only).",
    "All file paths in the JSON must use forward slashes (/) and relative notation with './' prefix, regardless of operating system.",
    "The JSON must conform to nnU-Net v2 schema with string keys for channel_names and labels (e.g., '0', '1', not integers).",
    "No partial output: if validation fails (missing labels, file format errors, duplicate channels, empty imagesTr/labelsTr/), do not write dataset.json.",
    "Test images must be included in the JSON under a 'test' array without a 'label' field (omit entirely, do not use null).",
    "Do not include tensorImageSize in the JSON schema.",
    "Validate that all files end in .nii.gz; reject any file with a different extension.",
    "If imagesTr/ or labelsTr/ is empty, fail with an error. If imagesTs/ is empty, warn but continue (generate JSON with empty test array).",
    "Accept any non-empty string as a valid case ID; do not enforce format validation (numeric, alphanumeric, etc.).",
    "Do not validate whether training and test cases are disjoint; if overlap occurs, include the case in both arrays."
  ],
  "still_missing": [
    "Exact overwrite policy decision: refuse, silently overwrite, or prompt user? (Recommend refuse; requires requester confirmation.)",
    "Whether additional metadata fields (description, reference, licence, release, modality) are required in the schema. (Assume not required unless specified.)",
    "Exact format and destination of success/error output (stdout vs. stderr, message wording, exit codes). (Recommend: stdout summary on success, stderr errors on failure, exit 0/non-zero.)",
    "Whether the script should validate that training and test case IDs are disjoint. (Assume no validation required; allow overlap.)"
  ],
  "worker_next_focus": [
    "Confirm the overwrite policy with the requester or document the chosen default (refuse recommended).",
    "Finalize and document the empty directory behavior: fail for imagesTr/labelsTr/, warn for imagesTs/.",
    "Add explicit validation rule: reject any file matching <case_id>_000[1-9].nii.gz as an error (single channel only).",
    "Verify that test entries in the JSON omit the 'label' field entirely (not null).",
    "Define the exact success/error output format (stdout summary with case counts, stderr for errors, exit codes).",
    "Confirm that label keys in the JSON must be strings ('0', '1') not integers.",
    "