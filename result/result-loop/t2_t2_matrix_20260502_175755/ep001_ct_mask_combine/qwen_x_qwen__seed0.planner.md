### Concrete Implementation Spec for Worker

#### Observed Facts:
- Input CT files are located at `<dataset_root>/ct/<patient_id>.nii.gz`.
- Input mask directories are located at `<dataset_root>/mask/<patient_id>_total/`.
- Output should be written to `<output_root>/<patient_id>/`.
- Each patient has multiple structure masks under their respective total segmentation directory.
- The task involves combining similar structures (e.g., `rib_left_*` and `rib_right_*`) into single binary masks.
- The resulting binary masks should be filled with corresponding CT intensities to produce "real-intensity masks".
- A foreground mask combining all structures and a background ("soft tissue") CT output are required.

#### Assumptions:
- All input `.nii.gz` files follow standard NIfTI format.
- Structure names within the mask directory follow a consistent naming pattern such as `rib_left_1`, `rib_right_1`, etc.
- The worker can identify which masks belong to the same structure based on shared prefixes (e.g., `rib_left_*` and `rib_right_*`).
- Mask filenames do not contain special characters that could interfere with filesystem operations.
- The CT image and mask images have matching spatial dimensions and affine transformations.
- There is no predefined schema for how to group structures; grouping logic must be inferred from filename patterns.
- No specific naming convention exists for the final output files beyond the requirement to place them in `<output_root>/<patient_id>/`.

#### Constraints:
- Must support resuming from previous runs if interrupted.
- Must avoid overwriting existing outputs unless explicitly instructed.
- Must handle large volumes of patients efficiently.
- Must ensure correctness of merging multiple masks per structure type.
- Must preserve original CT intensity values when filling the real-intensity masks.

#### Missing Information / Open Questions:
- What is the exact naming convention used for different structures? For example, how are left/right pairs identified?
- Are there any reserved or special filenames in the mask directories that should be ignored?
- Is there a defined list of structure types to combine, or should the worker infer these from the available files?
- Should the worker check for alignment between CT and mask images before processing?
- How should the worker determine whether a run has already completed for a given patient?
- Does the worker need to validate that all expected inputs exist before starting?
- What is the expected behavior if a mask file cannot be read or processed due to corruption?

```json
{
  "assumptions": [
    "All input .nii.gz files follow standard NIfTI format.",
    "Structure names within the mask directory follow a consistent naming pattern such as rib_left_1, rib_right_1, etc.",
    "The worker can identify which masks belong to the same structure based on shared prefixes.",
    "Mask filenames do not contain special characters that could interfere with filesystem operations.",
    "The CT image and mask images have matching spatial dimensions and affine transformations.",
    "There is no predefined schema for how to group structures; grouping logic must be inferred from filename patterns.",
    "No specific naming convention exists for the final output files beyond placing them in <output_root>/<patient_id>/."
  ],
  "risks": [
    "Incorrectly identifying structure groups may lead to incorrect merged masks.",
    "Failure to align CT and mask images could result in misaligned output.",
    "Overwriting existing outputs without proper checks might cause data loss.",
    "Crash during processing without checkpointing may require reprocessing entire patient set."
  ],
  "open_questions": [
    "What is the exact naming convention used for different structures?",
    "Are there any reserved or special filenames in the mask directories that should be ignored?",
    "Is there a defined list of structure types to combine, or should the worker infer these from the available files?",
    "Should the worker check for alignment between CT and mask images before processing?",
    "How should the worker determine whether a run has already completed for a given patient?",
    "Does the worker need to validate that all expected inputs exist before starting?",
    "What is the expected behavior if a mask file cannot be read or processed due to corruption?"
  ]
}
```