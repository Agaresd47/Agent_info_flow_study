### Implementation Plan for Dataset Splitting and Symlink Creation

#### Observed Facts:
- Input data is organized under `<input_root>/` with subdirectories for each organ (e.g., `Heart`, `Lung`, etc.).
- Each organ has its own subdirectory structure where patient IDs and parts are used as directory/file names.
- The DRR images are stored directly in `CT_no_bed/` with `.jpg` extension.
- Organ-specific masks are stored in corresponding organ directories using a nested structure like `<patient_id>_<organ_name>/<part>.jpg`.
- A file named `organ_list.txt` exists which defines the mapping between organs and their respective parts.

#### Assumptions:
- All organ directories contain consistent naming conventions for patient IDs and parts.
- The `organ_list.txt` file contains valid organ names and lists of associated parts in a format that can be parsed line-by-line.
- There are no duplicate patient IDs across different organs.
- The number of patients per organ is sufficient to allow for an 8:1:1 split without loss of data integrity.
- The worker will have read access to all input files and write access to the output root directory.

#### Constraints:
- The splitting ratio must be exactly 8:1:1 for train/test/validation sets.
- Symbolic links must be created in the correct structure under `<output_root>` following nnU-Net conventions.
- Part mappings defined in `organ_list.txt` must be respected during symlink creation.
- No modification or copying of original files should occur; only symbolic links are allowed.

#### Risks:
- Incorrect parsing of `organ_list.txt` could lead to wrong part-to-organ mappings.
- If any organ lacks sufficient samples for the desired split, it may result in uneven distribution or incomplete splits.
- Failure to validate that symbolic links point to existing source files might cause runtime errors when using the dataset.
- Improper handling of path separators or special characters in filenames could break the symlink creation process.

#### Open Questions:
1. What is the exact format of `organ_list.txt`? Is it a simple list of organ names, or does it include key-value pairs mapping organs to parts?
2. Are there any expected edge cases such as missing organ masks for certain patients or corrupted image files?
3. Should the worker handle cases where some organs do not have corresponding part files?
4. How should the worker deal with potential conflicts if multiple organs reference the same part name?

```json
{
  "assumptions": [
    "All organ directories follow consistent naming conventions.",
    "The organ_list.txt file is structured in a way that allows line-by-line parsing.",
    "There are no duplicate patient IDs across different organs.",
    "The number of patients per organ supports the required 8:1:1 split.",
    "Worker has necessary read/write permissions on input/output locations."
  ],
  "risks": [
    "Incorrect parsing of organ_list.txt leading to wrong mappings.",
    "Insufficient sample size per organ causing imbalanced splits.",
    "Symbolic link pointing to non-existent source files.",
    "Path separator or character issues breaking symlink creation."
  ],
  "open_questions": [
    "What is the exact format of organ_list.txt?",
    "Are there any expected edge cases like missing organ masks or corrupted images?",
    "How should the worker handle organs without corresponding part files?",
    "How to manage potential conflicts from shared part names among organs?"
  ]
}
```