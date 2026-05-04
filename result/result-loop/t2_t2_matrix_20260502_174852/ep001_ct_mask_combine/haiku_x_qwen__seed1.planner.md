# Implementation Spec: CT Mask Combination and Intensity Filling Pipeline

## Observed Facts

- Input CT scans: `<dataset_root>/ct/<patient_id>.nii.gz` (NIfTI format)
- Input masks: `<dataset_root>/mask/<patient_id>_total/` containing TotalSeg output structures
- Output destination: `<output_root>/<patient_id>/`
- Processing must support resumption after crashes
- Multi-machine parallel execution required
- Speed is a priority constraint

## High-Level Processing Steps

1. **Mask Grouping & Combination**: Merge related structure masks (e.g., `rib_left_*` + `rib_right_*` → single binary mask)
2. **Real-Intensity Masking**: Extract CT intensity values within combined mask regions
3. **Foreground/Background Separation**: Combine all structures as foreground; treat remaining voxels as soft tissue; output modified CT
4. **Crash Recovery**: Enable resumption of partially completed patients

---

## Critical Assumptions

- TotalSeg output masks are binary (0/1 or boolean) in NIfTI format
- Mask filenames follow a consistent naming convention (e.g., `<structure_name>.nii.gz`)
- Structure grouping rules (e.g., which masks belong to "rib" category) are predefined or provided separately
- CT and mask volumes share identical spatial dimensions and coordinate systems
- "Soft tissue CT output" means: preserve original CT intensity where no structure mask exists; replace with a defined value (or original intensity) where structures exist
- Output format is NIfTI (.nii.gz)
- Patient IDs are consistent across CT, mask, and output directories

---

## Explicit Constraints & Risks

### Irreversible Actions
- **Risk**: Overwriting output files without validation could lose intermediate results
- **Mitigation Required**: Implement atomic writes (write to temp file, then rename) or checkpoint markers

### Crash Recovery
- **Risk**: Unclear what constitutes "completion" for a patient (which outputs must exist?)
- **Mitigation Required**: Define explicit completion markers (e.g., a `.done` file or manifest) before resuming
- **Risk**: Partial mask combinations or intensity fills could corrupt downstream processing
- **Mitigation Required**: Validate output integrity before marking patient as complete

### Memory & Performance
- **Risk**: Loading full 3D volumes into memory may exceed available RAM for large datasets
- **Mitigation Required**: Specify memory budget and chunking strategy (if needed)
- **Risk**: I/O bottleneck when reading many small mask files per patient
- **Mitigation Required**: Consider pre-staging or batch I/O patterns

### Spatial Alignment
- **Risk**: Mask and CT may have different origins, spacing, or orientations
- **Mitigation Required**: Verify and document resampling/alignment requirements

---

## Missing Information (Blocking Questions)

1. **Mask Grouping Rules**: 
   - What is the complete mapping of structure names to grouping categories?
   - Is this mapping static or configurable per run?
   - How should unmapped structures be handled?

2. **Real-Intensity Mask Definition**:
   - Should output preserve original CT intensity, or apply a transformation?
   - What value should be used for background (non-mask) regions in the "real-intensity mask"?

3. **Soft Tissue Output**:
   - Should background voxels (outside all structures) retain original CT intensity or be set to a specific value?
   - Is this a separate output file or a modification of the CT?

4. **Completion & Resumption**:
   - What files must exist in `<output_root>/<patient_id>/` to mark a patient as "done"?
   - If a patient is partially complete, which steps should be skipped on re-run?

5. **Error Handling**:
   - Should a single patient's failure halt the entire batch, or continue to next patient?
   - What constitutes a fatal error vs. a recoverable warning?

6. **Output Schema**:
   - Expected filenames for combined masks, real-intensity masks, and soft-tissue CT?
   - Should metadata (e.g., structure names, grouping info) be stored alongside outputs?

7. **Scale & Performance**:
   - Typical patient count, volume size (voxels), and available compute resources?
   - Target throughput (patients/hour)?

---

## First Implementation Actions

1. **Define and document** the structure grouping mapping (static config file or database)
2. **Create a patient state machine** with explicit states: `pending`, `masks_combined`, `intensity_filled`, `complete`, `failed`
3. **Implement atomic checkpoint writing** (write to temp, rename on success)
4. **Build a resumption check** that inspects `<output_root>/<patient_id>/` and skips completed steps
5. **Validate spatial alignment** between CT and masks before processing; log mismatches
6. **Implement per-patient error logging** with patient ID and step name for debugging

---

```json
{
  "assumptions": [
    "TotalSeg masks are binary NIfTI files with consistent naming convention",
    "CT and mask volumes have identical spatial dimensions and coordinate systems",
    "Structure grouping rules are static and predefined (not learned from data)",
    "Output format is NIfTI (.nii.gz)",
    "Patient IDs are consistent across input and output directories",
    "Crash recovery requires explicit completion markers, not implicit file presence"
  ],
  "risks": [
    "Overwriting outputs without atomic writes could corrupt intermediate results on crash",
    "Unclear completion criteria could cause re-processing of partial results or skipping of incomplete steps",
    "Memory exhaustion if full 3D volumes loaded without chunking strategy",
    "Spatial misalignment between CT and masks could produce invalid outputs silently",
    "I/O bottleneck from reading many small mask files per patient in parallel",
    "Unmapped structure names could be silently ignored or cause failures"
  ],
  "open_questions": [
    "What is the complete structure-to-group mapping (e.g., which masks → 'rib' category)?",
    "How should unmapped structures be handled?",
    "What value should background voxels have in 'real-intensity mask' and 'soft-tissue CT' outputs?",
    "What files must exist in output directory to mark a patient as complete?",
    "On resumption, which steps should be skipped if partial outputs exist?",
    "Should single-patient failures halt the batch or continue to next patient?",
    "Expected volume sizes, patient counts, and target throughput for performance tuning?",
    "Should spatial alignment (resampling/registration) be performed, or assumed pre-aligned?"
  ]
}
```