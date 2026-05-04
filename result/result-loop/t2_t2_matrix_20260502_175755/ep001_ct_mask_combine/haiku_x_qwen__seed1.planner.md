# Implementation Spec: CT Mask Combine Worker

## Overview
This worker processes patient CT scans and TotalSeg masks to produce:
1. **Grouped structure masks** (e.g., combining rib_left_* and rib_right_* into single rib mask)
2. **Real-intensity masks** (CT intensity values within mask regions)
3. **Composite foreground + soft-tissue fallback** output

The worker must support resumption after failure and prioritize throughput for multi-machine parallel execution.

---

## Observed Facts

- Input CT: `<dataset_root>/ct/<patient_id>.nii.gz` (single file per patient)
- Input masks: `<dataset_root>/mask/<patient_id>_total/` (directory with multiple mask files from TotalSeg)
- Output destination: `<output_root>/<patient_id>/` (directory per patient)
- Format: NIfTI (.nii.gz)
- Constraint: Must resume after mid-process failure
- Constraint: Multi-machine, multi-patient parallelization expected

---

## Processing Pipeline

### Phase 1: Mask Grouping
- **Input**: All mask files in `<dataset_root>/mask/<patient_id>_total/`
- **Task**: Identify which masks belong to the same anatomical group (e.g., rib_left_*, rib_right_*)
- **Output**: Grouped binary masks (one per group)
- **Missing**: Exact grouping rules/mapping (e.g., is it prefix-based? is there a config file?)

### Phase 2: Real-Intensity Masking
- **Input**: CT volume + grouped binary masks from Phase 1
- **Task**: For each grouped mask, extract CT intensity values where mask == 1
- **Output**: NIfTI volumes with original CT intensities in mask regions
- **Missing**: What value/handling for mask == 0 regions? (zeros? NaN? background intensity?)

### Phase 3: Composite Foreground + Soft-Tissue Fallback
- **Input**: All grouped masks + original CT
- **Task**: 
  - Union all grouped masks → foreground binary mask
  - For voxels in foreground: use CT intensity
  - For voxels outside foreground: assign soft-tissue CT value
- **Output**: Single composite volume
- **Missing**: Definition of "soft-tissue CT value" (fixed HU? median? mode of background?)

---

## Resumption & Checkpointing

**Requirement**: Worker must detect and skip completed patients without re-processing.

**Missing specifics**:
- What marks a patient as "complete"? (e.g., presence of final output file? completion marker file?)
- If partial outputs exist (e.g., Phase 1 done, Phase 2 failed), should worker resume from Phase 2 or restart?
- Overwrite policy: if output files exist, overwrite or skip?
- Atomic write semantics: should intermediate outputs be written to temp location then moved?

---

## File Naming & Output Schema

**Output directory structure**: `<output_root>/<patient_id>/`

**Missing**:
- Exact output filenames for each phase (e.g., `grouped_masks.nii.gz`? `real_intensity_<group_name>.nii.gz`?)
- Should each grouped mask be a separate file or stacked in one volume?
- Naming convention for grouped masks (e.g., how to name the rib group output?)
- Should composite output be a single file or multiple files?

---

## Data Handling & Safety

**Constraints**:
- NIfTI I/O must preserve spatial metadata (affine, header)
- Mask operations must be binary (0/1) or clearly defined
- Memory efficiency: CT + multiple masks may be large; consider streaming or chunked I/O

**Missing**:
- Expected volume dimensions / memory footprint?
- Should worker validate input file integrity before processing?
- Error handling: fail fast or log and continue to next patient?

---

## Parallelization & Throughput

**Observed**: Multi-machine, multi-patient execution expected.

**Missing**:
- Patient discovery: how does worker get list of patients? (scan directory? config file? queue?)
- Locking mechanism: if multiple workers process same patient, how to prevent race conditions?
- Batch size recommendation?

---

## Risks & Constraints

1. **Irreversible writes**: If overwrite policy is not specified, worker could destroy existing outputs.
2. **Incomplete resumption logic**: Partial outputs without clear markers could cause re-processing or data corruption.
3. **Mask grouping ambiguity**: Without explicit mapping, worker may misgroup structures.
4. **Background value undefined**: Phase 3 soft-tissue assignment is underspecified; wrong choice could corrupt output.
5. **Memory pressure**: Large volumes + parallel workers could exhaust resources; no guidance on chunking.
6. **NIfTI metadata loss**: Careless I/O could strip spatial information.

---

## First Actions for Worker

1. **Validate inputs exist**: Check `<dataset_root>/ct/<patient_id>.nii.gz` and `<dataset_root>/mask/<patient_id>_total/` are readable.
2. **Check resumption state**: Determine if `<output_root>/<patient_id>/` already contains valid outputs; if so, skip or resume.
3. **List mask files**: Enumerate all files in mask directory; identify naming pattern.
4. **Load CT**: Read NIfTI header and volume; verify spatial metadata.
5. **Load masks**: Read all mask files; verify binary values and spatial alignment with CT.

---

```json
{
  "assumptions": [
    "All input CT files are valid NIfTI (.nii.gz) with consistent spatial dimensions per patient.",
    "All mask files in <dataset_root>/mask/<patient_id>_total/ are binary (0/1) and spatially aligned with corresponding CT.",
    "TotalSeg mask filenames follow a consistent naming convention (e.g., structure_name.nii.gz).",
    "Output directory <output_root>/<patient_id>/ can be created if it does not exist.",
    "Worker has read access to dataset_root and write access to output_root.",
    "NIfTI affine and header metadata should be preserved in all outputs."
  ],
  "risks": [
    "CRITICAL: Overwrite policy undefined—worker could destroy existing outputs if not specified.",
    "CRITICAL: Resumption marker undefined—worker may re-process or partially process patients, causing data inconsistency.",
    "Mask grouping rules not provided—worker may misidentify which masks belong to same anatomical group.",
    "Background value for soft-tissue fallback undefined—incorrect assignment could corrupt composite output.",
    "Memory exhaustion risk if volumes are large and multiple workers run on same machine without coordination.",
    "Race condition risk if multiple workers attempt to process same patient simultaneously without locking.",
    "NIfTI I/O library choice not specified—different libraries may handle metadata differently.",
    "Error handling strategy not defined—unclear whether to fail fast, log and continue, or retry."
  ],
  "open_questions": [
    "What is the exact mask grouping mapping? (e.g., is there a config file, or should worker infer from filename prefixes?)",
    "How should grouped masks be named in output? (e.g., 'rib.nii.gz', 'rib_combined.nii.gz'?)",
    "Should each grouped mask be output as a separate file or stacked into a single multi-channel volume?",
    "What value should be assigned to voxels outside the foreground mask in Phase 3? (fixed HU value? computed statistic?)",
    "What marks a patient as 'complete' for resumption purposes? (presence of specific file? completion marker?)",
    "If partial outputs exist, should worker resume from last completed phase or restart from scratch?",
    "Overwrite policy: should existing output files be overwritten, skipped, or moved to backup?",
    "Should intermediate outputs be written atomically (temp file + move) or directly?",
    "How does worker discover the list of patients to process? (directory scan? config file? queue system?)",
    "Is there a locking mechanism to prevent multiple workers from processing the same patient?",
    "What is the expected volume size and memory budget per patient?",
    "Should worker validate input file integrity (e.g., NIfTI header check) before processing?",
    "What is the error handling strategy? (fail fast, log and continue, retry with backoff?)",
    "Are there any constraints on NIfTI I/O library choice (e.g., nibabel, SimpleITK, ITK)?",
    "Should worker log processing time and throughput metrics?"
  ]
}
```