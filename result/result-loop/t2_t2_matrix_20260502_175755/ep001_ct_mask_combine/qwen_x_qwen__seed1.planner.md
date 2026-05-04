### Implementation Plan for Worker

#### Observed Facts:
- Input dataset structure:
  - CT scans: `<dataset_root>/ct/<patient_id>.nii.gz`
  - Mask directories: `<dataset_root>/mask/<patient_id>_total/`
- Output directory structure: `<output_root>/<patient_id>/`
- Each patient has multiple mask files in their respective mask directory.
- The task involves combining masks of similar structures (e.g., `rib_left_*` and `rib_right_*`) into single binary masks.
- The resulting binary masks should be filled with CT intensity values to produce "real-intensity masks".
- Remaining voxels after foreground segmentation should be treated as soft tissue CT.

#### Assumptions:
- All `.nii.gz` files follow standard NIfTI format.
- Mask filenames within each patient's mask directory follow a consistent naming pattern where similar structures can be grouped (e.g., `rib_left_1`, `rib_left_2`, etc.).
- There exists a mapping or rule set to group related mask names into categories (e.g., all rib-related masks belong to one category).
- The worker will use a method to identify which masks belong together based on shared prefixes or suffixes.
- The CT scan and mask volumes have matching spatial dimensions and affine transformations.
- The output root directory already exists or can be created by the worker.
- The worker does not modify original input files; it writes outputs to the designated output location.

#### Constraints:
- Must support resuming from previous runs if interrupted.
- Must avoid overwriting existing outputs unless explicitly instructed.
- Must handle large datasets efficiently with speed prioritized.
- Must ensure that intermediate steps do not corrupt or lose data during processing.
- No destructive writes to input directories.
- Completion status must be tracked per patient to allow resumption.

#### Missing Information / Open Questions:
- Exact naming convention for grouping masks (e.g., how to determine that `rib_left_1`, `rib_left_2` belong to the same class).
- Whether there is a predefined list of structure categories or if they must be inferred from filenames.
- How to define the boundary between foreground structures and background (soft tissue) in step 3.
- What constitutes a "completion marker" for a processed patient (e.g., a specific file or flag).
- Whether the worker should overwrite existing outputs or skip already-completed patients.
- Specific requirements for handling mismatched dimensions or affine matrices between CT and mask files.
- Any schema versioning or metadata requirements for output files beyond basic NIfTI format.

```json
{
  "assumptions": [
    "All .nii.gz files follow standard NIfTI format.",
    "Mask filenames within each patient's mask directory follow a consistent naming pattern where similar structures can be grouped.",
    "There exists a mapping or rule set to group related mask names into categories.",
    "The CT scan and mask volumes have matching spatial dimensions and affine transformations.",
    "The output root directory already exists or can be created by the worker.",
    "The worker does not modify original input files; it writes outputs to the designated output location."
  ],
  "risks": [
    "Incorrect grouping of mask files may lead to incorrect merged masks.",
    "Mismatched spatial dimensions or affine matrices between CT and mask could cause misalignment errors.",
    "Failure to track completion status properly might result in redundant processing or skipped work.",
    "Overwriting existing output files without clear indication could lead to loss of prior work."
  ],
  "open_questions": [
    "What is the exact naming convention used to group related mask files?",
    "Is there a predefined list of structure categories or must they be inferred from filenames?",
    "How is the boundary defined between foreground structures and background (soft tissue)?",
    "What constitutes a 'completion marker' for a processed patient?",
    "Should the worker overwrite existing outputs or skip already-completed patients?",
    "Are there specific requirements for handling mismatched dimensions or affine matrices?",
    "Are there any schema versioning or metadata requirements for output files?"
  ]
}
```