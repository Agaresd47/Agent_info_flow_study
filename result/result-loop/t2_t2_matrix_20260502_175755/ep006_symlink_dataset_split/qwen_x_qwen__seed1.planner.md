### Implementation Plan for Dataset Splitting and Symlink Generation

#### Observed Facts:
- Input directory structure includes DRR images (`CT_no_bed/`) and organ-specific subdirectories with part-level segmentation masks.
- Organ names are fixed (e.g., `Heart`, `Lung`, etc.), and each organ has its own subdirectory under which patient IDs and parts are stored.
- Each organ's part list is defined in a file named `organ_list.txt`.
- Output should follow the nnU-Net dataset format with train/test/validation splits.
- The split ratio is 8:1:1.

#### Assumptions:
- All input files have consistent naming patterns: `<patient_id>.jpg` for DRRs and `<patient_id>_<organ>/<part>.jpg` for masks.
- The `organ_list.txt` contains one organ per line, and for each organ, there is a corresponding list of parts (one per line) in a file named `<organ>_parts.txt`.
- The `organ_list.txt` file exists at the root of the input directory.
- There are no duplicate patient IDs across organs.
- The worker will be run in an environment where symbolic links can be created without issues.
- No additional metadata or annotations beyond what’s described are required.

#### Constraints:
- The worker must not modify or delete original files.
- Symbolic links must be used to avoid copying large image files.
- The output directories must be structured according to nnU-Net conventions:
  - `<output_root>/imagesTr`, `<output_root>/imagesTs`, `<output_root>/imagesVl`
  - `<output_root>/labelsTr`, `<output_root>/labelsTs`, `<output_root>/labelsVl`
- The worker must ensure that all organ/part mappings are respected during symlink creation.
- The splitting logic must preserve patient-level consistency (i.e., if a patient goes into test, all their organ parts go into test).

#### Missing Information / Open Questions:
- Is there a specific naming convention for the `organ_list.txt` file? (It was mentioned but not fully specified.)
- Are there any special handling rules for patients with missing organs or parts?
- Should the worker validate that all expected organ/part combinations exist for every patient?
- What is the expected behavior when a patient ID appears in multiple organs but not all?
- How should the worker handle cases where some organ directories are empty or missing?
- Is there a requirement for a completion marker or checkpoint mechanism to prevent reprocessing?

---

```json
{
  "assumptions": [
    "All input files follow consistent naming patterns.",
    "The `organ_list.txt` file exists and lists valid organ names.",
    "Each organ has a corresponding `<organ>_parts.txt` file listing parts.",
    "No duplicate patient IDs exist across organs.",
    "Symbolic links can be safely created in the target environment."
  ],
  "risks": [
    "Incorrect mapping between organs and parts due to misnamed or missing part files.",
    "Failure to maintain patient-level consistency during train/test/validation split.",
    "Overwriting existing symlinks or directories without clear indication of intent."
  ],
  "open_questions": [
    "Is the `organ_list.txt` file located at the root of the input directory?",
    "Should the worker validate presence of all organ/part combinations for each patient?",
    "What is the expected behavior for patients with missing organs or parts?",
    "Are there any special handling rules for empty or missing organ directories?",
    "Is there a requirement for a completion marker or checkpoint mechanism?"
  ]
}
```