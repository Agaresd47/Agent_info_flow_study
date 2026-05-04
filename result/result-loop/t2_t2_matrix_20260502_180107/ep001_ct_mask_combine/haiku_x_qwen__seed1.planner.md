# Implementation Spec: CT Mask Combine Worker

## Overview
This worker processes patient CT scans and TotalSeg masks to produce:
1. **Grouped structure masks** (e.g., combining rib_left_* and rib_right_* into single rib mask)
2. **Real-intensity masks** (CT intensity values within mask regions)
3. **Soft-tissue CT output** (foreground structures + soft-tissue background)

The worker must support resumption after failure and prioritize throughput for multi-machine parallel execution.

---

## 1. Input Data Contract

### CT Files
- **Location:** `<dataset_root>/ct/<patient_id>.nii.gz`
- **Format:** NIfTI gzip compressed
- **Assumption:** Single 3D volume per patient; intensity values represent Hounsfield units or equivalent

### Mask Files
- **Location:** `<dataset_root>/mask/<patient_id>_total/`
- **Format:** Individual `.nii.gz` files, one per TotalSeg structure
- **Naming convention:** Structure names embedded in filenames (e.g., `rib_left_1.nii.gz`, `rib_right_3.nii.gz`)
- **Assumption:** Each mask is binary (0 or 1)

---

## 2. Mask Grouping Logic

### Mathematical Semantics
- **Operation:** Union (logical OR) across all masks matching a group pattern
- **Group definition:** Structures sharing a common prefix (e.g., `rib_left_*`, `rib_right_*` → `rib`)
- **Output:** Single binary mask per group where voxel = 1 if ANY constituent structure has value 1 at that location

### Structure Selection Strategy
**OPEN QUESTION:** How are group patterns defined?
- Is there a fixed mapping file (e.g., JSON) specifying which filenames belong to which group?
- Should the worker infer groups from filename prefixes (e.g., split on `_` and take first N components)?
- Are there structures that should NOT be grouped (singleton structures)?
- What is the canonical list of expected groups?

**OPEN QUESTION:** How should the worker handle:
- Filenames that don't match any known group pattern?
- Duplicate or conflicting structure definitions?
- Missing expected structures for a patient?

---

## 3. Real-Intensity Mask Generation

### Definition
For each grouped mask:
- **Where mask = 1:** Copy CT intensity value from corresponding voxel
- **Where mask = 0:** Use a background fill value (see below)

### Background/Fill Value Handling
**OPEN QUESTION:** What value should fill non-mask regions?
- Air (typically -1000 HU)?
- Zero?
- NaN or a sentinel value?
- Patient-specific minimum intensity?

**OPEN QUESTION:** How should out-of-bounds or missing CT voxels be handled?

---

## 4. Soft-Tissue CT Output

### Definition
- **Foreground:** Union of ALL grouped masks (all structures combined)
- **Background:** Voxels outside foreground
- **Background intensity value:** 

**OPEN QUESTION:** What intensity should represent soft-tissue background?
- Original CT intensity at that location?
- A fixed soft-tissue HU value (e.g., ~40 HU for muscle)?
- Zero or a sentinel?

**OPEN QUESTION:** Should this output be a single volume or separate foreground/background masks?

---

## 5. Output Structure

### Directory Layout
```
<output_root>/<patient_id>/
├── grouped_masks/
│   ├── rib.nii.gz
│   ├── vertebra.nii.gz
│   └── [other_group].nii.gz
├── real_intensity_masks/
│   ├── rib_intensity.nii.gz
│   ├── vertebra_intensity.nii.gz
│   └── [other_group]_intensity.nii.gz
├── soft_tissue_ct.nii.gz
└── .completion_marker
```

### Completion Marker
**OPEN QUESTION:** What format and content should mark successful completion?
- Empty file `.completion_marker`?
- JSON with timestamp and checksum?
- Specific filename convention?

---

## 6. Resumption & Idempotency

### Completion Detection
**OPEN QUESTION:** How should the worker determine if a patient has already been processed?
- Check for `.completion_marker` file?
- Verify all expected output files exist?
- Compare output file modification times against input times?
- Check for partial outputs and decide whether to re-run or resume?

### Partial Failure Handling
**OPEN QUESTION:** If processing fails mid-patient:
- Should incomplete outputs be deleted or left in place?
- Should the worker attempt to resume from the last successful stage (grouped masks → real-intensity → soft-tissue)?
- Or should it always restart from scratch?

### Write Safety
**OPEN QUESTION:** 
- Should outputs be written to a temporary directory and atomically moved on success?
- Is overwriting existing outputs acceptable?
- Should there be a lock mechanism to prevent concurrent processing of the same patient?

---

## 7. Performance & Parallelization

### Constraints
- **Multi-machine execution:** Worker must not assume shared state or locks
- **Speed priority:** Minimize I/O and redundant computation
- **Assumption:** NIfTI I/O library (e.g., nibabel, SimpleITK) is available

### Optimization Considerations
**OPEN QUESTION:**
- Should grouped masks be computed once and reused for both real-intensity and soft-tissue outputs?
- Is memory-mapped I/O acceptable for large volumes?
- Should the worker process one patient per invocation or batch multiple patients?

---

## 8. Error Handling & Logging

### Required Logging Points
- Patient ID and processing stage
- Input file existence and validity checks
- Mask grouping decisions (which files matched which groups)
- Output file write status
- Resumption decisions (skipped vs. reprocessed)

**OPEN QUESTION:** What is the logging format and destination?

---

## 9. Data Validation

### Pre-processing Checks
- CT file exists and is readable NIfTI
- Mask directory exists and contains at least one mask file
- All mask files are readable and binary (values in {0, 1})
- CT and mask spatial dimensions are compatible (same shape or resample required?)

**OPEN QUESTION:** If CT and mask shapes differ, should the worker:
- Resample masks to CT space?
- Resample CT to mask space?
- Fail with an error?

---

## 10. First Actions for Worker

1. **Clarify all open questions** before implementation begins
2. **Define and document** the group mapping (structure name → group name)
3. **Specify** background fill values for real-intensity and soft-tissue outputs
4. **Define** completion marker format and resumption logic
5. **Establish** write-safety and overwrite policies
6. **Implement** input validation with clear error messages
7. **Add** comprehensive logging for debugging multi-machine runs

---

```json
{
  "assumptions": [
    "Each CT file is a single 3D NIfTI volume with Hounsfield-like intensity values",
    "Each mask file is binary (0 or 1) and spatially aligned with the CT",
    "Mask grouping uses logical OR (union) semantics",
    "Structures are grouped by filename prefix matching (e.g., rib_left_*, rib_right_* → rib)",
    "Worker runs independently per patient with no shared state across machines",
    "Output directory structure is flat (one patient_id per output_root subdirectory)",
    "Resumption is based on checking for a completion marker or output file presence"
  ],
  "risks": [
    "CRITICAL: No specification of group mapping rules—worker may misclassify or miss structures",
    "CRITICAL: Background fill values undefined—real-intensity and soft-tissue outputs may be incorrect or unusable",
    "CRITICAL: Completion marker format not specified—resumption logic cannot be safely implemented",
    "CRITICAL: Write-safety policy absent—concurrent writes or partial overwrites could corrupt outputs",
    "HIGH: Spatial dimension mismatch between CT and masks not addressed—resampling strategy unclear",
    "HIGH: No specification of what to do with unmatched or singleton structures",
    "MEDIUM: Logging format and destination not defined—debugging multi-machine runs will be difficult",
    "MEDIUM: No error recovery strategy for mid-patient failures—unclear whether to resume or restart"
  ],
  "open_questions": [
    "How are structure-to-group mappings defined? Fixed file? Filename pattern inference? Canonical list?",
    "What intensity value should fill non-mask regions in real-intensity masks?",
    "What intensity value should represent soft-tissue background in the soft-tissue CT output?",
    "What format and content should the completion marker use?",
    "How should the worker detect if a patient has already been successfully processed?",
    "If processing fails mid-patient, should outputs be deleted, left in place, or resumed from last checkpoint?",
    "Is atomic write (temp → final) required, or is direct overwrite acceptable?",
    "Should there be a locking mechanism to prevent concurrent processing of the same patient across machines?",
    "If CT and mask spatial dimensions differ, should the worker resample, fail, or use a specific strategy?",
    "Should the worker process one patient per invocation or batch multiple patients?",
    "What is the required logging format and destination (stdout, file, structured JSON)?",
    "Are there structures that should NOT be grouped (singletons)?",
    "How should the worker handle missing expected structures or unmatched filenames?"
  ]
}
```