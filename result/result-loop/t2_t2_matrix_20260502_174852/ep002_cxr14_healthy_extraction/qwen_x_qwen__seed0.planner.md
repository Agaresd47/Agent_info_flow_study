### Implementation Plan

#### Observed Facts:
- The dataset is NIH ChestX-ray14.
- Metadata is stored in a CSV file: `<dataset_root>/Data_Entry_2017.csv`.
- Images are located in a directory: `<dataset_root>/images/`.
- The goal is to extract images labeled as "healthy" for two purposes:
  1. Copy all healthy patient images to `<output_root>/healthy/`.
  2. Move only those with single scans (i.e., one image per patient) to `<output_root>/healthy_clean/`.

#### Assumptions:
- The CSV contains columns such as `PatientID`, `Image Index`, and labels indicating health status.
- Labels are encoded in a way that allows identification of "healthy" cases (e.g., a column like `Finding Labels`).
- Each row corresponds to an individual image entry.
- There exists a mechanism to determine if a patient has multiple scans (e.g., via grouping by `PatientID`).
- The output directories (`<output_root>/healthy/` and `<output_root>/healthy_clean/`) will be created if they don't exist.

#### Constraints:
- Only images associated with patients labeled as "healthy" should be considered.
- A patient's image(s) must be copied/moved based on their scan count.
- No data corruption or loss should occur during copying/moving operations.
- All paths must be validated before use to prevent accidental overwrites or misplacements.

#### Risks:
- Incorrectly identifying "healthy" patients due to ambiguous label formats.
- Misinterpreting multi-scan vs. single-scan patients leading to incorrect filtering.
- Failure to handle missing or malformed entries in the CSV.
- Unsafe file system operations if paths are not properly sanitized.

#### Open Questions:
- What specific column(s) in the CSV indicate whether a case is "healthy"? 
- How exactly is the "single scan" condition defined? Is it simply one image per `PatientID`?
- Are there any special handling requirements for duplicate filenames or existing files in output directories?

---

```json
{
  "assumptions": [
    "The CSV contains columns including 'PatientID', 'Image Index', and 'Finding Labels'.",
    "Label encoding indicates 'healthy' status through a specific string or flag.",
    "Each row represents a unique image entry.",
    "A patient with only one image entry is considered to have a single scan."
  ],
  "risks": [
    "Misinterpretation of label values may lead to incorrect selection of healthy samples.",
    "Incorrect grouping logic could misclassify patients with multiple scans.",
    "File system errors during copy/move operations might result in partial or failed transfers.",
    "Unsanitized paths could cause unintended behavior or security issues."
  ],
  "open_questions": [
    "Which column(s) in the CSV define the health status?",
    "How is the single-scan condition determined (e.g., number of rows per PatientID)?",
    "Should existing files in output directories be overwritten or skipped?"
  ]
}
```