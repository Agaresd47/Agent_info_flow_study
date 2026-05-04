### Implementation Spec: CT Mask Processing Worker

#### Overview
This worker processes a batch of patients' CT scans and corresponding segmentation masks to generate:
1. Merged binary masks per anatomical structure (e.g., all ribs combined into one).
2. Real-intensity masks where each voxel's intensity is taken from the original CT scan within the mask region.
3. A soft tissue CT image with background filled using the remaining voxels not covered by foreground structures.

The process must support resuming after crashes and prioritize speed for large-scale execution.

---

### Key Implementation Categories

#### 1. **Mask Merging Logic**
- **Mathematical Semantics**: Binary OR operation across all masks belonging to the same anatomical class.
  - Example: For `rib_left_*` and `rib_right_*`, perform bitwise OR on all such masks to form a single `rib` mask.
- **Structure File Selection**:
  - Input directory: `<dataset_root>/mask/<patient_id>_total/`
  - Files are named according to a pattern like `rib_left_1.nii.gz`, `rib_right_2.nii.gz`.
  - Grouping logic must be based on prefix/suffix matching (e.g., `rib_left_*` and `rib_right_*` belong to `rib`).
  - Missing or malformed files should be skipped without error unless explicitly required.
- **Missing Information**:
  - Exact naming convention for grouping (e.g., how to identify which files belong together).
  - Whether there are special cases or exceptions to groupings (e.g., asymmetrical structures).

#### 2. **Real-Intensity Mask Generation**
- **CT Source**: Use the corresponding `.nii.gz` file at `<dataset_root>/ct/<patient_id>.nii.gz`.
- **Fill Operation**:
  - Replace values inside the merged binary mask with intensities from the CT scan.
  - Voxels outside the mask remain unchanged or are set to zero if needed.
- **Background Handling**:
  - Background fill value for real-intensity masks is undefined in the prompt.
  - Must define whether unused regions should be masked out or left as-is.
- **Missing Information**:
  - Definition of background fill behavior for real-intensity masks.

#### 3. **Soft Tissue CT Output**
- **Foreground Coverage**:
  - All merged structures are treated as foreground.
- **Background Fill**:
  - Remaining voxels (not part of any foreground structure) are filled with soft tissue CT values.
  - The definition of “soft tissue” is ambiguous; it may refer to a specific range or threshold.
- **Missing Information**:
  - How to determine what constitutes “soft tissue” in the CT scan.
  - Whether to use a fixed value or dynamic fill based on CT histogram.

#### 4. **Resume Capability**
- **Completion Marker**:
  - Each patient’s output folder (`<output_root>/<patient_id>/`) should contain a marker file indicating completion.
  - Suggested name: `.completed` or similar.
- **Resumption Policy**:
  - Skip processing if the marker exists.
  - If partial outputs exist, decide whether to overwrite or abort.
- **Missing Information**:
  - Exact format of the completion marker (file name, content, etc.).
  - Overwrite policy for existing outputs during resume.

#### 5. **Output Directory Structure**
- Output root: `<output_root>/<patient_id>/`
- Expected outputs:
  - Merged binary masks (e.g., `rib.nii.gz`)
  - Real-intensity masks (e.g., `rib_real.nii.gz`)
  - Soft tissue CT (e.g., `soft_tissue.nii.gz`)
- **Missing Information**:
  - Naming convention for output files beyond basic structure.
  - Whether to compress outputs or leave them uncompressed.

---

### Assumptions

- All input files follow consistent naming conventions within their respective directories.
- The number of structures per category is known or can be inferred from file names.
- CT and mask volumes have matching spatial resolution and orientation.
- No destructive writes occur unless explicitly allowed by design.
- The worker will run in an environment where multiple processes can safely access shared storage.

---

### Risks

- Incorrect grouping of mask files due to ambiguous naming patterns could lead to incorrect merging.
- Inconsistent handling of background fills might produce inconsistent results across runs.
- Lack of clear overwrite/resume policies may cause data loss or redundant computation.
- Failure to detect incomplete or corrupted intermediate outputs may result in incorrect final state.

---

### Open Questions

1. What is the exact naming convention used to group mask files into anatomical categories?
2. Should real-intensity masks have a defined background fill value? If so, what is it?
3. How is “soft tissue” defined in the context of the CT scan? Is it a fixed value or derived from the data?
4. What is the expected format and location of the completion marker file?
5. Is there a specific overwrite policy for existing outputs when resuming?
6. Are there any reserved or special characters in the patient IDs that require sanitization?

```json
{
  "assumptions": [
    "All input files follow consistent naming conventions within their respective directories.",
    "The number of structures per category is known or can be inferred from file names.",
    "CT and mask volumes have matching spatial resolution and orientation.",
    "No destructive writes occur unless explicitly allowed by design.",
    "The worker will run in an environment where multiple processes can safely access shared storage."
  ],
  "risks": [
    "Incorrect grouping of mask files due to ambiguous naming patterns could lead to incorrect merging.",
    "Inconsistent handling of background fills might produce inconsistent results across runs.",
    "Lack of clear overwrite/resume policies may cause data loss or redundant computation.",
    "Failure to detect incomplete or corrupted intermediate outputs may result in incorrect final state."
  ],
  "open_questions": [
    "What is the exact naming convention used to group mask files into anatomical categories?",
    "Should real-intensity masks have a defined background fill value? If so, what is it?",
    "How is \"soft tissue\" defined in the context of the CT scan? Is it a fixed value or derived from the data?",
    "What is the expected format and location of the completion marker file?",
    "Is there a specific overwrite policy for existing outputs when resuming?",
    "Are there any reserved or special characters in the patient IDs that require sanitization?"
  ]
}
```