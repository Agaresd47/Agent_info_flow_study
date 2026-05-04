### Concrete Implementation Spec

#### Observed Facts:
- Input directory structure includes DRR images (`CT_no_bed/`) and organ-specific subdirectories (e.g., `Heart/`, `Lung/`, etc.), each containing patient-specific subfolders with part-level `.jpg` files.
- Organ names are mapped to their respective part lists via a file named `organ_list.txt`.
- Output should follow nnU-Net directory conventions with `{train,test,validation}` splits.
- Split ratio is 8:1:1 for train/test/validation.

#### Assumptions:
- All organ directories have consistent naming patterns: `<organ_name>/<patient_id>_<organ_name>/<part>.jpg`.
- The `organ_list.txt` contains one organ per line, and each organ maps to a list of parts (one part per line).
- Each patient ID appears consistently across all organ directories.
- The worker will use symbolic links to avoid copying data.
- No existing output directories exist at the start; if they do, behavior is undefined unless otherwise specified.
- File extensions are strictly `.jpg`.

#### Constraints:
- Symbolic links must be used to link input files into the appropriate output structure.
- The split must respect patient-level consistency — no partial patients in multiple splits.
- The mapping from organ to part must be respected exactly as defined in `organ_list.txt`.
- The worker must not modify or delete any input files.
- The worker must not overwrite existing output files or directories without explicit instruction (not provided).

#### Missing Information / Open Questions:
- Is there a specific naming convention for the `organ_list.txt`? (e.g., does it contain headers, comments, or special formatting?)
- Should the worker validate that all organ directories contain the same set of patient IDs?
- Are there any reserved or special characters in patient IDs that require escaping or handling?
- What is the expected format of the `organ_list.txt`? (e.g., tab-separated, space-separated, or newline-delimited?)
- How should the worker handle cases where a patient has missing organs or parts?
- Is there a requirement for a completion marker or checkpoint mechanism to resume from a previous run?
- Should the worker enforce deterministic shuffling based on seed or allow arbitrary ordering?

---

```json
{
  "assumptions": [
    "All organ directories follow consistent naming patterns.",
    "The organ_list.txt defines organ-to-part mappings with one part per line.",
    "Each patient ID exists uniformly across all organ directories.",
    "Symbolic links are used to avoid data duplication.",
    "No existing output directories exist at the start.",
    "File extensions are strictly .jpg."
  ],
  "risks": [
    "Inconsistent patient IDs across organ directories may lead to incomplete or incorrect splits.",
    "Improper handling of symbolic links could result in broken links or incorrect data access.",
    "Misinterpretation of organ_list.txt format may cause incorrect mapping of organs to parts.",
    "Failure to maintain patient-level consistency during splitting can break dataset integrity."
  ],
  "open_questions": [
    "What is the exact format of organ_list.txt?",
    "Should the worker validate uniformity of patient IDs across organ directories?",
    "Are there special characters in patient IDs requiring escaping?",
    "How should missing organs/parts be handled?",
    "Is a completion marker or checkpoint mechanism required?",
    "Is deterministic shuffling enforced or allowed?"
  ]
}
```