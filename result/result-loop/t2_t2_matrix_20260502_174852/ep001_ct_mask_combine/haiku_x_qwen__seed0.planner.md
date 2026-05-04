# Implementation Spec: CT Mask Combination and Intensity Filling Pipeline

## Observed Facts

- Input CT files: `<dataset_root>/ct/<patient_id>.nii.gz` (one per patient)
- Input mask files: `<dataset_root>/mask/<patient_id>_total/` (multiple structures from TotalSeg)
- Output destination: `<output_root>/<patient_id>/`
- Required outputs: combined masks, real-intensity masks, soft-tissue fallback
- Constraint: must support resumption after mid-pipeline failure
- Constraint: multi-machine parallelization expected; speed prioritized

## High-Level Workflow

1. **Discover** patient IDs from available CT files
2. **For each patient** (independently, resumable):
   - Load CT volume
   - Load all individual structure masks from `mask/<patient_id>_total/`
   - Group masks by anatomical category (e.g., rib_left_*, rib_right_* → rib)
   - Combine masks within each group (binary union)
   - Extract CT intensities within each combined mask region
   - Create foreground mask (union of all structures)
   - Generate soft-tissue fallback (non-foreground voxels)
   - Write outputs to `<output_root>/<patient_id>/`
3. **Track completion** per patient to enable resumption

## Key Constraints & Risks

| Constraint | Impact |
|-----------|--------|
| **Mask grouping rules undefined** | Worker must clarify which structures map to which anatomical categories (e.g., is `rib_left_1` grouped with `rib_left_2`? What about `rib_right_*`?) |
| **Mask file naming/format unknown** | Worker must verify actual filenames and format (NIfTI, binary vs. labeled, data type) in `mask/<patient_id>_total/` |
| **"Real-intensity mask" semantics unclear** | Does this mean: (a) a mask volume where voxels inside the mask retain CT intensity and outside are 0/NaN? (b) a separate intensity map? (c) something else? |
| **Soft-tissue fallback definition** | What intensity value or processing should non-foreground voxels receive? Should they be clipped, normalized, or passed through as-is? |
| **Resumption marker strategy** | How to detect if a patient was already processed? (e.g., check for sentinel file, check output directory completeness, timestamp comparison?) |
| **Multi-machine coordination** | How to prevent two workers from processing the same patient simultaneously? (e.g., lock file, database flag, work queue) |
| **Memory constraints** | Are CT volumes small enough to load entirely into memory, or must streaming/chunking be used? |
| **Output file naming** | What should the output files be named? (e.g., `combined_rib.nii.gz`, `intensity_rib.nii.gz`, `foreground.nii.gz`, `softtissue.nii.gz`?) |

## Open Questions

1. **Mask grouping logic**: Provide explicit mapping of TotalSeg structure names to anatomical categories (e.g., regex patterns or lookup table).
2. **Mask file format**: Confirm file extension, data type (uint8, uint16, float32?), and whether masks are binary or labeled.
3. **Real-intensity mask output format**: Clarify whether output should be a single volume per structure or a multi-channel volume.
4. **Soft-tissue handling**: Define how to populate non-foreground voxels (preserve original CT? set to constant? apply windowing?).
5. **Resumption strategy**: Specify the marker/check to determine if a patient is already complete.
6. **Concurrency control**: Specify mechanism for multi-machine safety (file locks, external queue, etc.).
7. **Patient discovery**: Should worker scan `<dataset_root>/ct/` for all `.nii.gz` files, or is a patient list provided?
8. **Error handling**: What should happen if a patient's CT or mask files are missing or corrupted?

## First Actions for Worker

1. **Validate inputs**: List all patient IDs found in `<dataset_root>/ct/` and confirm at least one has corresponding masks in `<dataset_root>/mask/`.
2. **Inspect one example**: Load a sample CT and examine one mask file to confirm format, shape, and data type.
3. **Clarify unknowns**: Ask for answers to all open questions above before proceeding.
4. **Design resumption**: Propose a resumption strategy (e.g., per-patient completion marker) and get approval.
5. **Prototype single patient**: Implement and test the full pipeline on one patient before scaling.

---

```json
{
  "assumptions": [
    "All CT files are valid NIfTI format (.nii.gz)",
    "All mask files are in the same directory per patient",
    "Mask files are binary (0/1) or can be thresholded to binary",
    "Patient IDs are extractable from CT filenames (stem before .nii.gz)",
    "Output directory can be created if it does not exist",
    "Worker has read/write access to dataset_root and output_root"
  ],
  "risks": [
    "CRITICAL: Mask grouping rules not provided; worker may group incorrectly or incompletely",
    "CRITICAL: Real-intensity mask semantics ambiguous; output format may not match expectations",
    "CRITICAL: No concurrency control specified; multi-machine runs risk duplicate processing or data corruption",
    "HIGH: Resumption strategy undefined; worker may re-process or skip patients unpredictably",
    "HIGH: Memory usage unbounded; large CT volumes may cause OOM on resource-constrained machines",
    "MEDIUM: Soft-tissue fallback behavior not specified; output may be unusable",
    "MEDIUM: No error recovery defined; partial failures may leave incomplete outputs"
  ],
  "open_questions": [
    "What is the exact mapping from TotalSeg structure names to anatomical categories?",
    "What file format and data type are the mask files?",
    "What should 'real-intensity mask' contain: CT intensities inside mask, zeros outside?",
    "How should soft-tissue (non-foreground) voxels be populated in output?",
    "What is the resumption marker: completion file, output directory check, or external flag?",
    "How should multi-machine concurrency be controlled?",
    "Should patient list be discovered by scanning CT directory or provided externally?",
    "What should happen if CT or mask files are missing or corrupted for a patient?"
  ]
}
```