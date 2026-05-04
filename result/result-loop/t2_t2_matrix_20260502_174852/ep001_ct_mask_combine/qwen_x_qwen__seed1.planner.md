### Implementation Plan for CT/Mask Processing Worker

#### Observed Facts:
- Input data is organized into two directories:
  - `<dataset_root>/ct/` contains `.nii.gz` files named by patient ID.
  - `<dataset_root>/mask/<patient_id>_total/` contains structure masks (e.g., `rib_left_1`, `rib_right_1`, etc.) for each patient.
- Output should be written under `<output_root>/<patient_id>/`.
- Each patient's processing involves combining multiple masks of the same type into a single binary mask.
- The resulting binary mask should be filled with CT intensity values to produce a "real-intensity mask".
- Remaining voxels (background) should be treated as soft tissue CT.

---

#### Assumptions:
- All `.nii.gz` files in `<dataset_root>/ct/` correspond to valid patient IDs.
- Structure masks within `<dataset_root>/mask/<patient_id>_total/` follow consistent naming conventions like `rib_left_*`, `rib_right_*`.
- Mask names can be grouped by prefix (e.g., all `rib_left_*` and `rib_right_*` belong to the same category).
- The number of structure masks per patient varies; some may have zero or more structures.
- The CT image and mask images are aligned spatially and have matching dimensions.
- The output directory structure will be created if it does not exist.
- The worker will process one patient at a time and support resuming after crashes.

---

#### Risks & Constraints:
- **Crash Resilience**: If the worker crashes during processing, it must resume from where it left off without reprocessing completed patients.
- **File System Errors**: File I/O operations might fail due to disk full, permission issues, or corrupted files.
- **Memory Usage**: Large CT/mask volumes could cause memory overflow unless handled carefully.
- **Naming Ambiguity**: Mask names may not always cleanly group into categories (e.g., `rib_left_1`, `rib_left_2`, `rib_right_1`, etc.), which could lead to incorrect grouping unless logic is robust.
- **Missing Data**: Some patients may lack corresponding CT or mask files — these cases must be skipped or logged appropriately.
- **Output Overwrites**: Existing outputs in `<output_root>/<patient_id>/` should not be overwritten unless explicitly intended.

---

#### Open Questions:
1. What is the expected format of the final output files? (e.g., `.nii.gz`, `.npz`, or other formats?)
2. Are there specific rules for how to combine masks (e.g., union of all masks in a class)?
3. How should the "soft tissue CT" be represented in the output? Should it be a copy of the original CT or a modified version?
4. Is there a known list of structure types (e.g., ribs, lungs, etc.) that we should expect, or should they be inferred dynamically?
5. Should the worker log progress or errors to a file for debugging?

---

```json
{
  "assumptions": [
    "All .nii.gz files in <dataset_root>/ct/ correspond to valid patient IDs.",
    "Structure masks within <dataset_root>/mask/<patient_id>_total/ follow consistent naming conventions like rib_left_*, rib_right_*.",
    "Mask names can be grouped by prefix (e.g., all rib_left_* and rib_right_* belong to the same category).",
    "The CT image and mask images are aligned spatially and have matching dimensions.",
    "The output directory structure will be created if it does not exist.",
    "The worker processes one patient at a time and supports resuming after crashes."
  ],
  "risks": [
    "If the worker crashes during processing, it must resume from where it left off without reprocessing completed patients.",
    "File I/O operations might fail due to disk full, permission issues, or corrupted files.",
    "Large CT/mask volumes could cause memory overflow unless handled carefully.",
    "Mask names may not always cleanly group into categories, leading to incorrect grouping unless logic is robust.",
    "Some patients may lack corresponding CT or mask files — these cases must be skipped or logged appropriately.",
    "Existing outputs in <output_root>/<patient_id>/ should not be overwritten unless explicitly intended."
  ],
  "open_questions": [
    "What is the expected format of the final output files? (e.g., .nii.gz, .npz, or other formats?)",
    "Are there specific rules for how to combine masks (e.g., union of all masks in a class)?",
    "How should the 'soft tissue CT' be represented in the output? Should it be a copy of the original CT or a modified version?",
    "Is there a known list of structure types (e.g., ribs, lungs, etc.) that we should expect, or should they be inferred dynamically?",
    "Should the worker log progress or errors to a file for debugging?"
  ]
}
```