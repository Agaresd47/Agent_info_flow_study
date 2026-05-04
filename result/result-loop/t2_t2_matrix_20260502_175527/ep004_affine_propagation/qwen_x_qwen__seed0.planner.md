### Implementation Plan: Affine Alignment Worker

#### Observed Facts:
- The task involves correcting affine transformations in medical imaging data (CT scans and masks).
- Each patient has a directory with `ct.nii.gz` and multiple mask files.
- The issue arises due to inconsistent signs in QR decomposition of affine matrices.
- The goal is to align all mask affines to match the reference CT affine after cleaning.

#### Assumptions:
- All input directories follow a consistent structure where `ct.nii.gz` exists and other mask files are present.
- The `ct.nii.gz` file contains a valid affine matrix.
- Mask files are in NIfTI format (`*.nii.gz`) and have corresponding affine matrices.
- QR decomposition is used to clean the affine matrix by removing rotational noise while preserving spacing.
- Symbol alignment refers to ensuring that the sign of the rotation components matches between the cleaned affine and the original CT affine.

#### Constraints:
- Must preserve original data integrity; no destructive writes unless explicitly allowed.
- Parallel processing is required across ~3000 patients.
- No overwrite policy or resume marker is defined — must be handled carefully.
- File naming convention for masks is not specified — must be inferred or queried.
- Schema version or metadata format for NIfTI files is not specified — must be assumed compatible with standard libraries like NiBabel.

#### Missing Information:
- Exact file path pattern for mask files (e.g., do they all end in `_mask.nii.gz`?).
- Whether there's a specific naming convention for mask files beyond general `.nii.gz`.
- Policy on how to handle cases where a mask does not exist or cannot be read.
- Whether the worker should generate a log or report of processed patients.
- Definition of “cleaned” affine — e.g., what constitutes acceptable deviation from the original affine during QR cleanup.
- Whether the worker needs to validate that the output affines result in aligned spatial coordinates post-transformation.

---

```json
{
  "assumptions": [
    "All patient directories contain a `ct.nii.gz` file and other mask files in NIfTI format.",
    "QR decomposition will remove rotational noise without altering spacing.",
    "Symbol alignment means matching the sign of each component of the rotation matrix."
  ],
  "risks": [
    "Overwriting original mask files if not handled carefully.",
    "Incorrect handling of affine matrices could lead to misalignment or data corruption.",
    "Parallel execution may cause race conditions if not properly synchronized."
  ],
  "open_questions": [
    "What is the exact naming convention for mask files?",
    "Is there a defined policy for handling missing or unreadable mask files?",
    "Should the worker produce logs or reports of its operations?",
    "How should the worker determine which affine matrix is considered 'correct' for symbol alignment?",
    "Are there any schema rules or metadata formats that must be preserved?"
  ]
}
```