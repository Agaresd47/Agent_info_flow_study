### Implementation Plan: Affine Alignment Worker

#### Observed Facts:
- The task involves correcting affine transformations in medical imaging data (CT and masks).
- Each patient has a `ct.nii.gz` file with an affine matrix.
- Other mask files in the same directory need their affine matrices corrected to match the CT's affine.
- The correction process includes QR decomposition to clean rotation noise and sign alignment.

#### Assumptions:
- All input files are in NIfTI format (`*.nii.gz`).
- The `ct.nii.gz` file is present in each patient directory.
- Mask files are named such that they can be identified as non-CT files within the same directory.
- The affine matrices are 4x4 homogeneous transformation matrices.
- The worker will use libraries like `nibabel` for reading/writing NIfTI files and `numpy` for matrix operations.

#### Constraints:
- Must preserve original data integrity; no overwrite without backup or confirmation.
- Parallel processing must be safe and avoid race conditions on shared resources.
- The worker must handle potential errors gracefully (e.g., missing files, invalid affine matrices).

#### Risks:
- Incorrect application of affine corrections may lead to misalignment between CT and mask volumes.
- Sign flipping during QR decomposition could introduce unexpected orientation changes if not carefully handled.
- Parallel execution might cause issues if multiple workers access the same directory simultaneously unless properly synchronized.

#### Open Questions:
- What is the exact naming convention for mask files? Are all `.nii.gz` files except `ct.nii.gz` considered masks?
- Should the worker log progress or errors during processing?
- Is there a specific way to validate that the affine alignment was successful after correction?

---

```json
{
  "assumptions": [
    "All input files are in NIfTI format.",
    "Each patient directory contains exactly one `ct.nii.gz` file.",
    "Mask files are any `.nii.gz` files other than `ct.nii.gz` in the same directory.",
    "Affine matrices are 4x4 homogeneous transformation matrices.",
    "The worker uses `nibabel` and `numpy` for processing."
  ],
  "risks": [
    "Incorrect affine correction leads to misalignment between CT and mask volumes.",
    "Sign flipping during QR decomposition introduces unexpected orientation changes.",
    "Parallel processing may cause race conditions if not properly synchronized."
  ],
  "open_questions": [
    "What is the exact naming convention for mask files?",
    "Should the worker log progress or errors during processing?",
    "Is there a validation method to confirm successful affine alignment?"
  ]
}
```