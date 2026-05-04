# Implementation Spec: CT Mask Combine & Intensity Fill Pipeline

## Overview
Build a multi-patient data preprocessing pipeline that:
1. Groups TotalSeg masks by anatomical structure class
2. Generates intensity-filled masks from CT volumes
3. Produces composite foreground masks and soft-tissue fallback outputs
4. Supports resumption after failure
5. Optimizes for throughput across multiple machines

---

## Observed Facts

- **Input structure:**
  - CT volumes: `<dataset_root>/ct/<patient_id>.nii.gz`
  - Masks: `<dataset_root>/mask/<patient_id>_total/` (multiple files, TotalSeg output)
  
- **Output location:** `<output_root>/<patient_id>/`

- **Processing requirements:**
  - Merge masks by anatomical class (e.g., `rib_left_*` + `rib_right_*` → single `rib` mask)
  - Fill merged masks with CT intensity values ("real-intensity mask")
  - Combine all structures as foreground; remaining voxels treated as soft tissue
  - Must support crash recovery and multi-machine parallelization

---

## Assumptions

1. **File format:** All CT and mask files are NIfTI (.nii.gz) with matching spatial geometry
2. **Mask naming:** TotalSeg output follows a consistent naming convention (e.g., `<patient_id>_total/<structure_name>.nii.gz`)
3. **Grouping logic:** Structure class grouping is deterministic and can be derived from structure name prefixes (e.g., `rib_left_*`, `rib_right_*`)
4. **Intensity semantics:** "Fill with CT intensity" means copy voxel values from CT where mask is nonzero
5. **Soft tissue default:** Voxels outside all masks should receive a fixed soft-tissue HU value (not specified)
6. **Output format:** Output files are NIfTI (.nii.gz) with same geometry as input CT
7. **Patient ID extraction:** Patient IDs are consistently formatted and extractable from directory/file names

---

## Constraints

- **Write safety:** No specification for overwrite behavior (append, skip, replace, error on collision)
- **Resumption marker:** No explicit completion flag or checkpoint format defined
- **Parallelization:** No locking mechanism specified for multi-machine writes to shared `<output_root>`
- **Memory:** No guidance on handling large 3D volumes or batch processing strategy
- **Mask merging:** No specification for handling overlapping masks (union, max, first-wins)
- **Soft tissue value:** HU value for background voxels not provided

---

## Missing Information (Open Questions)

1. **Mask grouping rules:**
   - What is the exact mapping from individual mask names to structure classes?
   - Is this a fixed hardcoded list, a config file, or derived from name patterns?
   - How are ambiguous or unmapped masks handled?

2. **Intensity fill semantics:**
   - Should intensity be copied directly, or normalized/clipped to a range?
   - What happens at mask boundaries (interpolation, nearest-neighbor)?

3. **Soft tissue fallback:**
   - What HU value should be assigned to background voxels?
   - Should this be a global constant or per-patient?

4. **Resumption & checkpointing:**
   - What marks a patient as "complete"? (e.g., presence of final output file, metadata file, timestamp)
   - If a patient is partially processed, which intermediate outputs should be preserved vs. re-run?
   - Should incomplete outputs be deleted before retry?

5. **Multi-machine safety:**
   - Is `<output_root>` on shared storage (NFS, S3) or local?
   - How should concurrent writes be handled (file locking, atomic rename, per-machine subdirs)?
   - Should patient assignments be pre-distributed or dynamically claimed?

6. **Output file naming & structure:**
   - What are the exact output filenames for: merged masks, intensity masks, foreground mask, soft-tissue output?
   - Should all outputs go in `<output_root>/<patient_id>/` or in separate subdirectories?

7. **Error handling:**
   - What should happen if CT and mask geometries don't match?
   - What if a patient has no masks or no CT?
   - Should errors be logged and skipped, or halt the pipeline?

8. **Patient enumeration:**
   - How is the list of patient IDs determined? (scan directories, config file, database query)
   - Are there any filtering criteria (e.g., only certain patient ID patterns)?

---

## Recommended First Actions

1. **Clarify mask grouping:** Obtain or define the structure class mapping (e.g., JSON config with patterns or explicit lists)
2. **Define completion marker:** Choose a simple, atomic indicator (e.g., presence of `<output_root>/<patient_id>/.done` file)
3. **Specify soft-tissue HU:** Confirm the background intensity value
4. **Confirm output schema:** List exact filenames and directory layout for all outputs
5. **Resolve write safety:** Decide on overwrite policy and multi-machine coordination strategy

---

```json
{
  "assumptions": [
    "All CT and mask files are NIfTI (.nii.gz) with matching spatial geometry",
    "TotalSeg output follows a consistent naming convention in <patient_id>_total/ directories",
    "Structure class grouping is deterministic from name prefixes (e.g., rib_left_*, rib_right_*)",
    "Intensity fill means copying CT voxel values where mask is nonzero",
    "Soft tissue voxels are those outside all merged masks",
    "Output files are NIfTI (.nii.gz) with same geometry as input CT",
    "Patient IDs are consistently formatted and extractable from directory names"
  ],
  "risks": [
    "No overwrite policy specified; concurrent writes to same patient output could corrupt data",
    "No completion marker defined; unclear how to detect partial failures and resume safely",
    "Mask merging strategy undefined (union vs. max vs. first-wins); overlapping masks may produce incorrect results",
    "Background HU value not specified; soft-tissue output may be invalid",
    "No locking mechanism for multi-machine access to shared output directory",
    "Geometry mismatch between CT and masks not handled; could cause silent data corruption",
    "Memory constraints not specified; large volumes could cause OOM on worker machines"
  ],
  "open_questions": [
    "What is the exact mapping from individual TotalSeg mask names to structure classes?",
    "Is mask grouping hardcoded, config-driven, or pattern-based?",
    "What HU value should be assigned to background (soft-tissue) voxels?",
    "What marks a patient as successfully processed (file presence, metadata, timestamp)?",
    "If a patient is partially processed, which outputs should be preserved vs. re-run?",
    "Is <output_root> on shared storage or local per-machine?",
    "How should concurrent writes from multiple machines be coordinated?",
    "What are the exact output filenames for merged masks, intensity masks, foreground, and soft-tissue outputs?",
    "Should all outputs go in <output_root>/<patient_id>/ or in separate subdirectories?",
    "How is the patient list enumerated (directory scan, config, database)?",
    "What should happen if CT and mask geometries don't match?",
    "What should happen if a patient has no masks or no CT file?"
  ]
}
```