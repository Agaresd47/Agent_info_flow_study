### Implementation Plan

#### Observed Facts:
- Input data is organized under `<input_root>/` with subdirectories for each organ (e.g., `Heart`, `Lung`, etc.).
- Each organ has its own subdirectory structure where patient IDs and parts are used as directory/file names.
- The DRR image files are named `<patient_id>.jpg` and located directly under `CT_no_bed/`.
- Organ-specific masks are stored in subdirectories like `<organ>/<patient_id>_<organ>/<part>.jpg`.
- A file `organ_list.txt` exists to define which parts belong to which organs (multi-to-many mapping).
- Output should follow nnU-Net directory conventions: `<output_root>/{train,test,validation}/...`
- Data split ratio is 8:1:1 for train/test/validation.

---

#### Assumptions:
- All organ directories contain consistent naming patterns for patient IDs and parts.
- The `organ_list.txt` file contains valid organ-part mappings in a format that can be parsed line-by-line.
- Patient IDs in all organ directories match those in `CT_no_bed/`.
- No duplicate or malformed entries exist in input data.
- Symbolic links will be created using standard OS tools (`ln -s`) without additional tooling.

---

#### Constraints:
- Must preserve original file integrity; no modification of source files allowed.
- Splitting must be deterministic based on seed (already provided as 0).
- Symbolic link creation must be safe and avoid overwriting existing links.
- Directory structures must conform exactly to nnU-Net expectations after linking.
- Mapping from organ → part must support many-to-many relationships as defined in `organ_list.txt`.

---

#### Risks:
- Incorrect parsing of `organ_list.txt` could lead to wrong associations between organs and parts.
- Inconsistent naming across organ directories may cause missing or incorrect symbolic links.
- If `organ_list.txt` does not list all parts for an organ, some parts might be omitted during linking.
- Hardcoded ratios (8:1:1) assume sufficient number of patients; insufficient data could result in empty splits.

---

#### Open Questions:
1. What is the exact format of `organ_list.txt`? Is it one organ per line with space-separated parts?
2. Should the worker validate that every patient ID in `CT_no_bed/` has corresponding entries in all organ directories?
3. Are there any special characters or encoding issues in patient IDs or part names that require sanitization?
4. How should the worker handle cases where a patient lacks certain organs or parts?

---

```json
{
  "assumptions": [
    "All organ directories follow consistent naming patterns.",
    "The organ-list file defines multi-to-many mappings via line-based syntax.",
    "Patient IDs in all organ directories match those in CT_no_bed.",
    "No duplicate or malformed entries exist in input data.",
    "Symbolic links will be created using standard OS tools."
  ],
  "risks": [
    "Incorrect parsing of organ_list.txt may misassign parts to organs.",
    "Inconsistent naming across organ directories may break symbolic link creation.",
    "Missing or incomplete organ/part data in input may lead to incomplete output.",
    "Hardcoded 8:1:1 split assumes enough patients; small datasets may produce empty splits."
  ],
  "open_questions": [
    "What is the exact format of organ_list.txt?",
    "Should validation ensure all organ directories have matching patient IDs?",
    "Are there special characters or encoding concerns in patient IDs or part names?",
    "How should missing organ/part data be handled?"
  ]
}
```