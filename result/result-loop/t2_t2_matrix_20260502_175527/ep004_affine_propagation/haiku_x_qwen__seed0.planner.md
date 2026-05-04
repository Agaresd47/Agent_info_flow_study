# Implementation Spec: Affine Propagation for TotalSeg Mask Alignment

## Overview
Correct spatial misalignment between CT images and TotalSeg-generated masks by:
1. Extracting and cleaning the reference affine from each patient's `ct.nii.gz`
2. Applying QR decomposition to isolate and standardize rotation/sign components
3. Propagating the corrected affine to all mask files in the patient directory
4. Processing ~3000 patients in parallel

---

## Observed Facts

- **Input data**: Patient directories, each containing `ct.nii.gz` and multiple mask files (format/naming TBD)
- **Problem**: TotalSeg masks have affine matrices with sign inconsistencies after QR decomposition relative to the reference CT
- **Scope**: All mask files in each patient directory require affine correction
- **Scale**: ~3000 patients, parallelizable workload
- **Language/Library**: Not specified; likely nibabel or similar NIfTI manipulation library

---

## Required Implementation Steps

### Step 1: Patient Directory Discovery
- Identify all patient directories in the input root
- Locate `ct.nii.gz` in each directory
- Identify all mask files (naming pattern and extensions: **OPEN QUESTION**)

### Step 2: Reference Affine Extraction & Cleaning
For each patient:
1. Load `ct.nii.gz` and extract its affine matrix (4×4)
2. Apply QR decomposition to the affine's rotation/scaling block (upper-left 3×3)
3. Extract the diagonal sign pattern from the R matrix
4. Store the cleaned affine and sign pattern as the reference

### Step 3: Sign Alignment
- For each mask file in the patient directory:
  1. Load the mask's affine matrix
  2. Apply QR decomposition to its rotation/scaling block
  3. Compare the sign pattern of R to the reference sign pattern
  4. If signs differ, apply a sign-correction transformation (method: **OPEN QUESTION**)

### Step 4: Affine Application
- Write the corrected affine back to each mask file's NIfTI header
- Preserve voxel data; only modify the affine matrix
- Confirm write success before proceeding to next patient

### Step 5: Parallelization & Checkpointing
- Distribute patients across workers (thread/process pool size: **OPEN QUESTION**)
- Define a completion marker or log entry per patient (format: **OPEN QUESTION**)
- Handle partial failures gracefully (retry policy: **OPEN QUESTION**)

---

## Constraints & Safety Considerations

| Constraint | Status | Details |
|-----------|--------|---------|
| **Destructive writes** | ⚠️ CRITICAL | Modifying mask affines is irreversible. Backup or versioning strategy required. |
| **File locking** | ⚠️ CRITICAL | Parallel writes to the same patient directory may conflict. Locking or atomic writes needed. |
| **NIfTI header preservation** | REQUIRED | All non-affine metadata (data type, shape, etc.) must remain unchanged. |
| **QR sign convention** | ⚠️ AMBIGUOUS | QR decomposition sign is arbitrary; clarify how to canonicalize across libraries. |
| **Mask file identification** | ⚠️ MISSING | No explicit list of mask file patterns (e.g., `*_mask.nii.gz`, `seg_*.nii.gz`). |

---

## Open Questions

1. **Mask file naming/selection**: What is the exact glob pattern or list of mask files per patient? (e.g., all `*.nii.gz` except `ct.nii.gz`? specific prefixes?)

2. **QR sign-correction method**: After detecting sign mismatch, how should the affine be corrected?
   - Flip the sign of specific rows/columns?
   - Apply a permutation matrix?
   - Reorder axes?

3. **Write safety & backups**: 
   - Should original masks be backed up before modification?
   - Should writes be atomic (temp file + rename)?
   - Overwrite in-place or create new versioned files?

4. **Parallelization strategy**:
   - Thread pool, process pool, or distributed job queue?
   - Max workers for ~3000 patients?
   - Timeout per patient?

5. **Completion & resumption**:
   - How to mark a patient as successfully processed?
   - If a run is interrupted, how to resume without reprocessing?
   - Log format and location?

6. **Error handling**:
   - What constitutes a fatal error vs. a warning? (e.g., missing mask file, NIfTI read failure)
   - Should a single patient failure halt the entire batch or continue?

7. **Validation**:
   - After affine correction, how to verify alignment? (e.g., check that spacing is preserved, rotation is orthogonal?)
   - Tolerance thresholds for numerical errors?

8. **Input/output paths**:
   - Root directory for patient data?
   - Output location (in-place or separate directory)?

---

```json
{
  "assumptions": [
    "Each patient directory contains exactly one ct.nii.gz file serving as the reference.",
    "All mask files are in NIfTI format (.nii.gz or .nii).",
    "QR decomposition is applied to the 3×3 rotation/scaling block of the 4×4 affine matrix.",
    "Sign mismatch is the primary source of spatial misalignment; voxel data and shape are already correct.",
    "Parallelization is safe at the patient level (no cross-patient dependencies).",
    "The affine matrix is the only NIfTI header field requiring modification."
  ],
  "risks": [
    "CRITICAL: Modifying affine matrices is irreversible without backups. Data loss risk if write fails mid-operation.",
    "CRITICAL: Parallel writes to the same patient directory may cause file corruption or race conditions.",
    "HIGH: QR decomposition sign convention varies by library (NumPy, SciPy, etc.); inconsistent canonicalization could propagate errors.",
    "HIGH: Incorrect sign-correction logic could worsen spatial misalignment instead of fixing it.",
    "MEDIUM: Missing or malformed mask files could silently fail or halt the batch.",
    "MEDIUM: Numerical precision in affine comparison could lead to false sign-mismatch detection."
  ],
  "open_questions": [
    "What is the exact file naming pattern or glob selector for mask files per patient?",
    "How should sign mismatches be corrected? (flip rows/columns, permutation, axis reordering?)",
    "Should original masks be backed up? If so, where and in what format?",
    "What is the write safety policy? (in-place, atomic temp+rename, versioned output?)",
    "How many parallel workers should be used for ~3000 patients?",
    "How should completion be marked and resumption handled after interruption?",
    "What error conditions should halt the batch vs. log and continue?",
    "What validation checks should confirm successful affine correction?",
    "What are the root input directory and output directory paths?",
    "Should the QR decomposition use a specific library or algorithm variant?"
  ]
}
```