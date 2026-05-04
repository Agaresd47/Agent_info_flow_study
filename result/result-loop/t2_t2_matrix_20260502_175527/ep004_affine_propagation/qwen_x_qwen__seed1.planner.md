### Implementation Plan: Affine Alignment Worker

#### Overview
The goal is to align all mask files within each patient directory to match the affine transformation of `ct.nii.gz`, using QR decomposition to clean the affine matrix and then aligning signs to ensure consistency.

---

### First Actions (Worker's Immediate Steps)

1. **Scan all patient directories**:
   - Traverse the root directory containing patient folders.
   - Identify each patient folder (assumed to be named uniquely per patient).
   - For each patient folder, locate `ct.nii.gz` and all `.nii.gz` mask files.

2. **Verify input structure**:
   - Confirm that `ct.nii.gz` exists in each patient directory.
   - Ensure that mask files are `.nii.gz` format and are located in the same directory as `ct.nii.gz`.

3. **Extract affine matrices**:
   - Load `ct.nii.gz` and extract its affine matrix.
   - Store this reference affine for use in alignment.

4. **Apply QR decomposition**:
   - Perform QR decomposition on the reference affine matrix.
   - Reconstruct the cleaned affine matrix using only the scaling/spacing components (i.e., remove rotational noise).

5. **Align signs of cleaned affine**:
   - Compare the sign pattern of the cleaned affine with the original affine from `ct.nii.gz`.
   - Adjust signs of the cleaned affine to match those of the original.

6. **Apply aligned affine to masks**:
   - For each mask file in the patient directory:
     - Load the mask image.
     - Apply the corrected affine to the mask.
     - Save the updated mask with the same filename (or a new name if overwrite policy is unclear).

7. **Parallelization strategy**:
   - Process one patient directory at a time in parallel.
   - Use a thread pool or job queue to manage up to 3000 concurrent jobs.

8. **Completion tracking**:
   - Track progress via a log or status file.
   - Optionally, mark each patient directory as processed once completed.

---

### Assumptions

- Each patient directory contains exactly one `ct.nii.gz` file.
- All mask files in a patient directory are `.nii.gz` and should be aligned to the same reference affine.
- The affine matrix is a 4x4 matrix compatible with NiBabel or similar libraries.
- No additional metadata or header information beyond affine is required for alignment.
- The worker will not modify the original `ct.nii.gz` file.

---

### Risks

- **Overwrite Risk**: If mask files are overwritten without a backup mechanism, data loss may occur.
- **Inconsistent File Naming**: If mask filenames vary or are not `.nii.gz`, the script might skip or misalign them.
- **Affine Incompatibility**: If the affine matrices are malformed or incompatible with expected transformations, alignment may fail silently or produce incorrect results.
- **Concurrency Issues**: If multiple workers access the same directory simultaneously, race conditions could occur unless proper locking or isolation is implemented.

---

### Open Questions

- What is the exact overwrite policy for mask files? Should they be saved under a new name or overwrite existing ones?
- Is there a specific naming convention for mask files (e.g., `mask_*.nii.gz`) or should all `.nii.gz` files be considered?
- Are there any completion markers or checkpoints needed to resume processing after interruption?
- Is there a specific library or tool to perform QR decomposition and affine manipulation (e.g., NiBabel, NumPy)?
- Should the worker validate that the affine matrices are valid before applying transformations?

---

```json
{
  "assumptions": [
    "Each patient directory contains exactly one `ct.nii.gz` file.",
    "All mask files in a patient directory are `.nii.gz` and should be aligned to the same reference affine.",
    "The affine matrix is a 4x4 matrix compatible with NiBabel or similar libraries.",
    "The worker will not modify the original `ct.nii.gz` file."
  ],
  "risks": [
    "Overwrite Risk: If mask files are overwritten without a backup mechanism, data loss may occur.",
    "Inconsistent File Naming: If mask filenames vary or are not `.nii.gz`, the script might skip or misalign them.",
    "Affine Incompatibility: If the affine matrices are malformed or incompatible with expected transformations, alignment may fail silently or produce incorrect results.",
    "Concurrency Issues: If multiple workers access the same directory simultaneously, race conditions could occur unless proper locking or isolation is implemented."
  ],
  "open_questions": [
    "What is the exact overwrite policy for mask files? Should they be saved under a new name or overwrite existing ones?",
    "Is there a specific naming convention for mask files (e.g., `mask_*.nii.gz`) or should all `.nii.gz` files be considered?",
    "Are there any completion markers or checkpoints needed to resume processing after interruption?",
    "Is there a specific library or tool to perform QR decomposition and affine manipulation (e.g., NiBabel, NumPy)?",
    "Should the worker validate that the affine matrices are valid before applying transformations?"
  ]
}
```