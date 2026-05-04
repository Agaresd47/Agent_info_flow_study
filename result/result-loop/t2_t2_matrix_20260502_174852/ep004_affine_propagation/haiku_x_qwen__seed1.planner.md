# Implementation Spec: Affine Propagation for TotalSeg Mask Alignment

## Observed Facts

- **Problem**: TotalSeg-generated masks have minor affine inconsistencies with source CT images, causing spatial misalignment in downstream reads
- **Root cause**: QR decomposition produces sign inconsistencies between CT affine and mask affine
- **Scale**: ~3000 patient directories, requiring parallel execution
- **Input**: Each patient directory contains `ct.nii.gz` and multiple mask files
- **Task scope**: 
  1. Extract and clean CT affine via QR decomposition
  2. Align signs to CT affine reference
  3. Propagate cleaned affine to all mask files in the directory

## Implementation Approach

### Phase 1: Single Patient Processing (Serializable Unit)

For each patient directory:

1. **Load CT affine**
   - Read `ct.nii.gz` header
   - Extract 4×4 affine matrix
   - Store as reference

2. **QR decomposition and cleaning**
   - Decompose CT affine into Q (rotation/reflection) and R (upper triangular, encodes spacing)
   - Extract spacing values from R diagonal
   - Reconstruct "clean" affine using only spacing (remove rotation noise)
   - Document which components were removed

3. **Sign alignment**
   - Compare signs of cleaned affine against original CT affine
   - Apply sign corrections to match original orientation
   - Verify result is orthogonal (or near-orthogonal after spacing scaling)

4. **Mask file propagation**
   - Identify all mask files in patient directory (e.g., `*.nii.gz` excluding `ct.nii.gz`)
   - For each mask file:
     - Read current affine
     - Replace with cleaned, sign-aligned affine
     - Write back (in-place or to staging location)

### Phase 2: Parallelization

- Process patient directories in parallel (thread pool or process pool)
- Each worker handles one complete patient directory independently
- Aggregate results/errors for reporting

---

## Assumptions

- `ct.nii.gz` is always present and valid in each patient directory
- Mask files are NIfTI format (`.nii.gz` or `.nii`)
- Affine matrices are 4×4 homogeneous transforms
- "Spacing" refers to diagonal elements of R after QR decomposition (voxel dimensions)
- Sign alignment means matching the sign pattern of the original CT affine, not reorienting the image data
- No image data resampling is required; only affine header modification

## Constraints & Risks

### Irreversible Actions
- **Writing affine back to mask files**: This modifies input data. Recommend:
  - Create backup or staging directory before any writes
  - Implement dry-run mode (report changes without writing)
  - Provide rollback mechanism or version control

### Numerical Stability
- QR decomposition may produce near-singular or ill-conditioned matrices
- Sign alignment logic must handle edge cases (e.g., near-zero off-diagonal elements)
- Floating-point comparison for "sign" may need tolerance threshold

### Data Integrity
- Verify cleaned affine does not introduce NaN or Inf values
- Confirm all mask files in directory are intended targets (risk of over-applying to unrelated files)
- Check for read-only or locked files before attempting writes

### Parallelization Hazards
- Shared filesystem contention with ~3000 concurrent workers
- Error in one patient should not block others; implement per-patient error handling
- Memory usage per worker (NIfTI header I/O is lightweight, but accumulation matters)

---

## Open Questions

1. **QR decomposition specifics**
   - Should R be normalized (e.g., positive diagonal)?
   - How to handle negative determinant (reflection)? Preserve or flip?
   - Tolerance for "noise" removal—what magnitude of off-diagonal elements should be zeroed?

2. **Sign alignment definition**
   - Does "match original CT affine signs" mean element-wise sign matching, or orientation-preserving alignment?
   - If multiple valid sign patterns exist, which takes precedence?

3. **Mask file identification**
   - Are all `.nii.gz` files in the directory (except `ct.nii.gz`) valid masks?
   - Are there subdirectories or naming conventions to respect?
   - Should the script skip certain files (e.g., metadata, logs)?

4. **Output and validation**
   - Should cleaned affines be logged/reported per patient?
   - How to validate that alignment succeeded (e.g., spatial overlap check)?
   - What constitutes success/failure for reporting?

5. **Execution environment**
   - Parallelization strategy: thread pool, process pool, or distributed job queue?
   - Resource limits per worker (memory, CPU)?
   - Retry policy for transient I/O failures?

6. **Backup and rollback**
   - Should original masks be preserved? Where?
   - If errors occur mid-run, how to resume or revert?

---

## First Actions for Worker

1. Implement and test single-patient processing on a small sample (1–5 patients)
2. Verify QR decomposition logic and sign alignment on known test cases
3. Implement dry-run mode (report changes without writing)
4. Set up error logging and per-patient status tracking
5. Validate output affines (orthogonality, spacing preservation)
6. Only after validation: enable parallel execution and scale to full dataset

---

```json
{
  "assumptions": [
    "ct.nii.gz is always present and valid in each patient directory",
    "Mask files are NIfTI format (.nii.gz or .nii)",
    "Affine matrices are 4×4 homogeneous transforms",
    "Spacing is encoded in the diagonal of R from QR decomposition",
    "Sign alignment means matching sign pattern of original CT affine, not reorienting image data",
    "No image data resampling is required; only affine header modification",
    "All .nii.gz files in a directory (except ct.nii.gz) are valid mask targets"
  ],
  "risks": [
    "Writing affine back to mask files is irreversible; implement backup and dry-run mode first",
    "QR decomposition may produce ill-conditioned matrices; add numerical stability checks",
    "Sign alignment logic must handle edge cases (near-zero off-diagonal, negative determinant)",
    "Floating-point comparison for signs may need tolerance threshold",
    "Parallelizing ~3000 workers may cause filesystem contention; implement per-patient error handling",
    "Risk of over-applying affine to unrelated files; validate mask file identification",
    "Read-only or locked files will cause write failures; check permissions before batch execution"
  ],
  "open_questions": [
    "QR decomposition: should R diagonal be normalized? How to handle negative determinant?",
    "What tolerance threshold for removing 'noise' (off-diagonal elements) from affine?",
    "Does 'sign alignment' mean element-wise sign matching or orientation-preserving alignment?",
    "Are all .nii.gz files in directory valid masks, or are there naming/subdirectory conventions?",
    "Should cleaned affines be logged/reported per patient? What constitutes validation success?",
    "Parallelization strategy: thread pool, process pool, or distributed queue?",
    "Backup strategy: preserve originals? Where? How to resume or revert on failure?"
  ]
}
```