# Implementation Spec: NIH ChestX-ray14 Healthy Sample Extraction

## Observed Facts

- Input metadata: CSV file at `<dataset_root>/Data_Entry_2017.csv`
- Input images: Directory at `<dataset_root>/image/`
- Output destinations: `<output_root>/healthy/` and `<output_root>/healthy_clean/`
- Two-stage filtering process with explicit output directories
- Preference stated for pandas to read CSV

## Implementation Approach

### Stage 1: Identify and Copy Healthy Samples
1. Load `Data_Entry_2017.csv` using pandas
2. Filter rows where the patient health status indicates "healthy" (exact column name and value TBD)
3. For each healthy patient record, locate corresponding image file(s) in `<dataset_root>/image/`
4. Copy (not move) all located images to `<output_root>/healthy/`
5. Log source-to-destination mappings for traceability

### Stage 2: Filter for Single-Scan Healthy Patients
1. From Stage 1 results, identify patients with exactly one scan record
2. Move (not copy) those single-scan patient images to `<output_root>/healthy_clean/`
3. Preserve original filenames or document any renaming logic

---

## Assumptions

- The CSV contains a column or field that explicitly marks patient health status as "healthy" or equivalent
- Image filenames or patient IDs in the CSV can be reliably matched to files in `<dataset_root>/image/`
- A "single scan" is determinable from the CSV metadata (e.g., one row per patient, or a scan count column)
- Output directories (`<output_root>/healthy/` and `<output_root>/healthy_clean/`) do not exist or can be safely created
- File I/O permissions allow both copy and move operations
- Duplicate filenames across patients are not expected, or collision handling is acceptable

## Risks & Constraints

- **Irreversible action**: Stage 2 uses `move` rather than `copy`. If Stage 2 filtering logic is incorrect, images cannot be recovered from `<output_root>/healthy_clean/` without re-running Stage 1.
- **Data loss if directories exist**: Creating output directories without checking for existing files may overwrite data.
- **CSV schema unknown**: Without seeing the actual CSV structure, filtering logic cannot be validated. Misidentified "healthy" column will silently produce wrong results.
- **Image-to-patient mapping ambiguity**: If multiple images share similar names or if patient IDs are not unique keys, copy/move operations may fail or produce duplicates.
- **Disk space**: No validation that `<output_root>` has sufficient space for copies before Stage 1 begins.
- **Partial failure recovery**: If the process fails mid-Stage 2, some images will be in `<output_root>/healthy/` and others in `<output_root>/healthy_clean/`, creating an inconsistent state.

## Open Questions

1. **CSV Schema**: What is the exact column name and value(s) that indicate a "healthy" patient? (e.g., `Finding_Labels`, `Disease_Status`, or a binary flag?)
2. **Single-scan definition**: How is "single scan" determined? Is it one row per patient in the CSV, or is there a scan count column?
3. **Image filename mapping**: How do patient identifiers in the CSV map to image filenames? (e.g., patient ID → `<patient_id>.png`, or is there a separate filename column?)
4. **Handling missing images**: If a CSV record references an image that doesn't exist in `<dataset_root>/image/`, should the process skip, warn, or fail?
5. **Output directory pre-existence**: Should the worker create output directories, or do they already exist? Should existing files be overwritten, skipped, or cause an error?
6. **Logging/reporting**: What level of detail should be logged? (e.g., count of healthy patients, count of single-scan patients, list of copied/moved files?)

---

```json
{
  "assumptions": [
    "CSV contains a column identifying patient health status as 'healthy'",
    "Patient identifiers in CSV can be reliably matched to image filenames",
    "Single-scan status is determinable from CSV metadata",
    "Output directories can be safely created or already exist",
    "File I/O permissions allow copy and move operations",
    "No significant filename collisions across patients"
  ],
  "risks": [
    "Stage 2 move operation is irreversible; incorrect filtering logic causes data loss",
    "Unknown CSV schema may lead to silent filtering errors",
    "Insufficient disk space could fail Stage 1 mid-operation",
    "Partial failure leaves inconsistent state across output directories",
    "Image-to-patient mapping ambiguity may cause missed or duplicate files",
    "Pre-existing output files may be overwritten without warning"
  ],
  "open_questions": [
    "What is the exact CSV column name and value indicating 'healthy' status?",
    "How is 'single scan' defined in the CSV structure?",
    "What is the mapping rule between patient IDs and image filenames?",
    "How should missing images (referenced in CSV but absent from disk) be handled?",
    "Should output directories be created fresh, or do they pre-exist?",
    "What logging and reporting detail is required?"
  ]
}
```