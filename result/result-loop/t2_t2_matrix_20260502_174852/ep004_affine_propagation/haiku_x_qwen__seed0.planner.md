# Implementation Spec: Affine Propagation for TotalSeg Mask Alignment

## Observed Facts

- Input: ~3000 patient directories, each containing `ct.nii.gz` and multiple mask files
- Problem: TotalSeg masks have affine matrices with sign inconsistencies after QR decomposition, causing spatial misalignment
- Solution approach: Use CT affine as reference, clean via QR decomposition, align signs, propagate to all masks in directory
- Execution model: Parallel processing across patients
- Context: Data alignment preprocessing for medical imaging pipeline

## Specification

### Phase 1: Reference Affine Extraction & Cleaning

**For each patient directory:**

1. Load `ct.nii.gz` and extract its affine matrix (4×4)
2. Perform QR decomposition on the 3×3 rotation-scale block
3. Extract spacing (diagonal of R matrix, absolute values)
4. Reconstruct "clean" affine: diagonal matrix of spacing + translation component from original
5. **Store this clean affine as the reference for the patient**

### Phase 2: Sign Alignment

6. Compare the sign pattern of the clean affine's rotation-scale block against the original CT affine's rotation-scale block
7. Determine sign flip requirements (which axes need negation to match original orientation)
8. Apply these sign corrections to the clean affine
9. **Verify the result preserves spacing magnitudes while matching CT orientation signs**

### Phase 3: Mask Propagation

10. Identify all mask files in the patient directory (exclude `ct.nii.gz`)
11. For each mask file:
    - Load the NIfTI file
    - Replace its affine matrix with the cleaned, sign-aligned affine from Phase 2
    - Write back to disk (preserve filename, format, data array)
12. **Log which files were modified and their original vs. new affine matrices**

### Phase 4: Validation (Recommended)

13. Spot-check: Load a mask and CT, verify their affine matrices now match
14. Verify data array shapes remain unchanged

---

## Constraints & Irreversible Actions

| Constraint | Impact | Mitigation |
|-----------|--------|-----------|
| **Disk writes are destructive** | Original mask affines will be overwritten | Require explicit backup or dry-run mode before execution |
| **QR decomposition sign ambiguity** | Different libraries may produce different Q/R signs | Must document which library/convention is used; test on sample data first |
| **Parallel I/O on ~3000 patients** | Risk of file locks, incomplete writes, or race conditions | Use process-level locking per patient directory; implement atomic writes (write-to-temp, then rename) |
| **Affine mismatch detection** | No stated tolerance for "acceptable" mismatch | Need threshold definition: what constitutes "sign inconsistency"? |

---

## Assumptions

- All patient directories follow the same structure: `{patient_dir}/ct.nii.gz` + mask files
- Mask files are NIfTI format (`.nii.gz` or `.nii`)
- The CT affine is always valid and represents the ground truth orientation
- QR decomposition is applied only to the 3×3 rotation-scale block; translation (4th column) is preserved
- "Sign alignment" means matching the sign pattern of the rotation matrix, not arbitrary flipping
- Spacing values are always positive (absolute values from R diagonal)

---

## Open Questions

1. **Mask file naming/identification**: What is the exact naming pattern for mask files? (e.g., `*_mask.nii.gz`, `seg_*.nii.gz`, or a specific list?)
2. **QR decomposition convention**: Should we use NumPy's `np.linalg.qr()`, SciPy, or another library? Are there known sign conventions to follow?
3. **Sign alignment criterion**: How is "matching original CT affine signs" formally defined? (e.g., maximize dot product of rotation matrices, or match specific axis signs?)
4. **Tolerance for "small inconsistency"**: What magnitude of affine difference triggers the cleaning process? Is every mask always cleaned, or only those exceeding a threshold?
5. **Backup/rollback strategy**: Should original affines be saved (e.g., in a metadata file per patient) for auditability?
6. **Parallelization granularity**: Process-per-patient, or thread-pool within each patient? Memory constraints?
7. **Error handling**: If a mask file is corrupted or missing, should the entire patient fail, or skip that file and continue?
8. **Output logging**: What level of detail is required? (e.g., per-file affine diffs, summary statistics, or just success/failure counts?)

---

## First Actions for Worker

1. **Clarify the 8 open questions above** with the requester before implementation
2. **Obtain a sample patient directory** (1–3 patients) to test QR decomposition and sign alignment logic
3. **Document the exact QR convention and sign-matching algorithm** in pseudocode before coding
4. **Design the atomic write pattern** (write to temp file, verify, rename) to ensure safety
5. **Set up logging infrastructure** to track which files were modified and any errors encountered

---

```json
{
  "assumptions": [
    "All patient directories contain ct.nii.gz as the reference affine source",
    "Mask files are in NIfTI format (.nii.gz or .nii)",
    "CT affine is always valid and represents ground truth orientation",
    "QR decomposition is applied to 3×3 rotation-scale block only; translation is preserved",
    "Spacing values are positive (absolute values extracted from R diagonal)",
    "Sign alignment means matching rotation matrix sign pattern, not arbitrary flipping",
    "Parallel execution is safe if implemented with per-patient file locking"
  ],
  "risks": [
    "Disk writes are irreversible; original mask affines will be overwritten without backup",
    "QR decomposition sign ambiguity across different libraries or versions",
    "Race conditions and file locks during parallel I/O on ~3000 patients",
    "No stated tolerance for affine mismatch; unclear when cleaning is triggered",
    "Corrupted or missing mask files could cause partial or total patient failure",
    "Incorrect sign alignment could introduce new spatial misalignment instead of fixing it"
  ],
  "open_questions": [
    "What is the exact naming pattern for mask files in each patient directory?",
    "Which QR decomposition library and sign convention should be used?",
    "How is 'matching original CT affine signs' formally defined (e.g., dot product criterion)?",
    "What magnitude of affine difference triggers the cleaning process?",
    "Should original affines be backed up for auditability or rollback?",
    "What is the preferred parallelization granularity (process-per-patient vs. thread-pool)?",
    "How should errors be handled (fail entire patient, skip file, or continue)?",
    "What level of logging detail is required (per-file diffs, summary stats, or counts only)?"
  ]
}
```