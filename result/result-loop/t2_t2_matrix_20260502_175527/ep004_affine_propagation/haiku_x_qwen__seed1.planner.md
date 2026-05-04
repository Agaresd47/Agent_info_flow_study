# Implementation Spec: Affine Propagation & Alignment for TotalSeg Masks

## Overview
Correct spatial misalignment between CT images and TotalSeg-derived masks by:
1. Extracting and cleaning the reference affine from each patient's `ct.nii.gz`
2. Applying QR decomposition to isolate and standardize rotation/spacing
3. Aligning sign conventions across all mask files in the patient directory
4. Writing corrected affines to all mask files in parallel across ~3000 patients

---

## Observed Facts

- **Input data**: Per-patient directories containing `ct.nii.gz` and multiple mask files (format/naming not specified)
- **Problem**: TotalSeg masks have affine inconsistencies post-QR decomposition; sign mismatches cause spatial misalignment downstream
- **Scale**: ~3000 patients, parallelizable workload
- **Language/environment**: Not specified; Chinese request suggests flexibility on tooling
- **Condition**: `B0_guardrailed` (safety-first handoff)

---

## Constraints & Safety Boundaries

### Destructive Operations
- **Mask file modification**: Rewriting affine matrices in-place is irreversible. Must have:
  - Backup/rollback strategy (copy originals before write, or write to staging directory first)
  - Validation checkpoint before committing writes
  - Clear policy on partial failure (e.g., if 1 of 5 masks fails, do we revert the patient?)

### Numerical Stability
- QR decomposition sign ambiguity: both `(Q, R)` and `(-Q, -R)` are valid. Must specify:
  - Which sign convention to adopt (e.g., diagonal of R always positive?)
  - How to detect and flip signs consistently across all masks in a patient

### Parallelization Hazards
- 3000 patients in parallel: risk of resource exhaustion, I/O contention, or partial failures
- No mention of retry logic, checkpointing, or resume markers

---

## Missing Information (Open Questions)

### File & Directory Structure
1. **Mask file naming convention**: What are the exact filenames or glob patterns? (e.g., `*_mask.nii.gz`, `seg_*.nii.gz`, specific organ names?)
2. **Patient directory layout**: Is the structure `{patient_id}/ct.nii.gz` and `{patient_id}/*mask*.nii.gz`? Or different?
3. **Root input path**: Where is the patient data rooted? (e.g., `/data/patients/`, relative path?)

### Affine Cleaning Algorithm
4. **QR decomposition target**: Should the cleaned affine preserve only spacing (diagonal) and translation, removing all rotation? Or preserve some rotation?
5. **Sign alignment rule**: How to decide which sign is "correct"? 
   - Match the sign of the diagonal of R from the reference CT's QR?
   - Match the sign of the first non-zero element?
   - Other convention?
6. **Tolerance for "small" inconsistencies**: What threshold determines if a rotation component is "noise" vs. intentional?

### Write Safety & Validation
7. **Overwrite policy**: 
   - Overwrite masks in-place?
   - Write to a new directory and swap?
   - Write to a staging area with manual approval?
8. **Validation before commit**: What checks confirm the corrected affine is valid? (e.g., determinant check, spacing magnitude bounds?)
9. **Failure handling**: If a mask file is corrupted or unreadable, skip it, fail the patient, or log and continue?

### Parallelization & Resumption
10. **Parallelism level**: How many workers/processes? Per-patient or per-file granularity?
11. **Resume/checkpoint strategy**: If the job crashes after processing 1500 patients, how do we resume without reprocessing or double-writing?
12. **Completion marker**: How to record which patients have been successfully processed? (e.g., `.done` file, database entry, log line?)

### I/O & Tooling
13. **NIfTI library**: Which library to use? (nibabel, SimpleITK, other?)
14. **Logging & monitoring**: Where should logs go? What level of detail (per-patient, per-file, errors only)?

---

## Recommended First Actions for Worker

1. **Clarify file structure**: List a sample patient directory to confirm naming and layout.
2. **Confirm QR convention**: Provide or agree on the exact sign-alignment rule (e.g., "make diagonal of R positive").
3. **Define write safety**: Decide on backup/staging strategy before touching any files.
4. **Establish resume marker**: Agree on how to track completion (e.g., `.affine_corrected` flag file per patient).
5. **Validate on small subset**: Test the algorithm on 5–10 patients before scaling to 3000.

---

## Implementation Outline (Pseudostructure, Not Code)

```
For each patient in parallel:
  1. Load ct.nii.gz → extract affine_ref
  2. QR-decompose affine_ref → (Q_ref, R_ref)
  3. Determine sign convention from R_ref (e.g., ensure diag(R) > 0)
  4. Construct cleaned_affine from R_ref (spacing + translation only, or with rotation?)
  5. For each mask file in patient directory:
     a. Load mask → extract affine_mask
     b. QR-decompose affine_mask → (Q_mask, R_mask)
     c. Flip signs of Q_mask, R_mask to match convention from step 3
     d. Reconstruct affine_mask_corrected = Q_mask @ R_mask
     e. Validate affine_mask_corrected (e.g., det, spacing bounds)
     f. Write affine_mask_corrected back to mask file (or staging)
  6. Mark patient as complete (write .done flag or log entry)
  7. On error: log, decide whether to skip patient or fail job
```

---

```json
{
  "assumptions": [
    "Patient data is organized in per-patient directories, each containing ct.nii.gz and one or more mask files.",
    "NIfTI files are readable via standard libraries (nibabel or equivalent).",
    "QR decomposition is the correct mathematical tool for isolating rotation and spacing; both (Q, R) and (-Q, -R) are valid, and a sign convention must be chosen.",
    "The reference affine (from ct.nii.gz) is the ground truth; all masks should be aligned to it.",
    "Parallelization across patients is safe (no cross-patient dependencies).",
    "The task is to correct affine matrices in-place or via a safe write strategy; no other image data transformation is needed."
  ],
  "risks": [
    "Irreversible data loss: Overwriting mask affines without backup will corrupt data if the algorithm is wrong. Must implement backup or staging before any write.",
    "Sign ambiguity in QR: Without a clear sign convention, the algorithm may flip signs inconsistently across patients or files, worsening misalignment.",
    "Partial failure in parallel: If 1 of 3000 patients fails mid-way, unclear whether to revert that patient, skip it, or fail the entire job.",
    "Resume/idempotency: No checkpoint mechanism specified; restarting the job may reprocess patients or skip them, leading to inconsistent state.",
    "Numerical instability: QR decomposition of near-singular or poorly-conditioned affines may produce unreliable results; no tolerance thresholds given.",
    "File naming ambiguity: If mask file patterns are not precisely specified, the worker may miss some files or process unintended files."
  ],
  "open_questions": [
    "What is the exact glob pattern or naming convention for mask files in each patient directory?",
    "What is the root path or directory structure for patient data?",
    "Should the cleaned affine preserve only spacing (diagonal) and translation, or also rotation? If rotation is preserved, how much is 'noise' vs. intentional?",
    "What is the exact sign-alignment rule for QR decomposition? (e.g., ensure diag(R) > 0, or match sign of first non-zero element?)",
    "What is the write safety policy: overwrite in-place, write to staging, or create backups?",
    "What validation checks should confirm a corrected affine is valid before writing? (e.g., determinant bounds, spacing magnitude bounds?)",
    "How should the worker handle failures: skip the patient, fail the entire job, or log and continue?",
    "What is the parallelism strategy: per-patient workers, per-file workers, or a thread pool?",
    "How should completion be tracked for resumption? (e.g., .done flag file, database, log entry?)",
    "Which NIfTI library should be used (nibabel, SimpleITK, other)?",
    "Where should logs be written, and what level of detail is required?"
  ]
}
```