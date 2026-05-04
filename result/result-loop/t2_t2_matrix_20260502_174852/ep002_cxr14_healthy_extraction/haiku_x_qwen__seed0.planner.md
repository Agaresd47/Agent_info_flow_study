# Implementation Spec: NIH ChestX-ray14 Healthy Sample Extraction

## Observed Facts

- Input metadata: `<dataset_root>/Data_Entry_2017.csv`
- Input images: `<dataset_root>/image/` directory
- Output destinations: `<output_root>/healthy/` and `<output_root>/healthy_clean/`
- Two-stage filtering process with copy then move operations
- Pandas should be used for CSV reading
- Dataset language context: Chinese; medical imaging (chest X-rays)

## Task Breakdown

### Stage 1: Extract Healthy Patients
1. Load CSV metadata using pandas
2. Identify rows representing "healthy" patients (filter criteria TBD)
3. For each healthy patient record, locate corresponding image file(s) in `<dataset_root>/image/`
4. Copy all located images to `<output_root>/healthy/`
5. Preserve original filenames or document any renaming scheme

### Stage 2: Extract Single-Scan Healthy Patients
1. From Stage 1 results in `<output_root>/healthy/`, identify patients with exactly one scan
2. Move (not copy) those single-scan images to `<output_root>/healthy_clean/`
3. Document which images were moved vs. remain in `<output_root>/healthy/`

## Assumptions

- "Healthy" status is determinable from a single column or combination of columns in the CSV
- Image filenames or patient IDs in the CSV can be reliably matched to files in `<dataset_root>/image/`
- One row in CSV corresponds to one scan/image
- Output directories can be created if they do not exist
- File system permissions allow copy and move operations
- No deduplication or collision handling is needed beyond standard filesystem behavior

## Risks & Constraints

- **Irreversible operation**: Stage 2 uses `move`, not copy. Images removed from `<output_root>/healthy/` cannot be recovered without re-running Stage 1.
- **Data loss if paths are wrong**: Incorrect `<dataset_root>` or `<output_root>` values could cause files to be copied/moved to unintended locations.
- **Missing images**: CSV may reference image files that do not exist in the directory; worker must decide whether to skip, warn, or fail.
- **Duplicate filenames**: Multiple patients may have identically-named images; copy/move behavior under collision is undefined.
- **Scale**: Dataset size unknown; memory and disk I/O implications not specified.

## Open Questions

1. **"Healthy" definition**: Which CSV column(s) and value(s) indicate a healthy patient? (e.g., a "Finding" column with value "No Finding", or absence of disease labels?)
2. **Image-to-patient mapping**: Is the mapping one-to-one (one row = one image file) or one-to-many (one patient = multiple scans)?
3. **Filename matching logic**: How are patient IDs in the CSV matched to image filenames? (e.g., exact substring match, regex pattern, lookup table?)
4. **Single-scan criterion**: Does "single scan" mean one image file per patient, or one imaging session? How is this determined from the CSV?
5. **Collision handling**: If two patients have images with the same filename, how should conflicts be resolved?
6. **Logging/reporting**: Should the worker produce a summary report (e.g., count of healthy patients, count moved to clean set)?
7. **Existing output directories**: Should the worker overwrite, skip, or error if `<output_root>/healthy/` or `<output_root>/healthy_clean/` already exist?

## First Actions for Worker

1. Inspect `<dataset_root>/Data_Entry_2017.csv` schema (column names, sample rows, data types)
2. Inspect `<dataset_root>/image/` directory structure (file naming convention, total count)
3. Clarify the "healthy" filter criteria with stakeholder
4. Clarify the image-to-patient mapping strategy
5. Confirm output directory initialization behavior

---

```json
{
  "assumptions": [
    "One CSV row represents one scan/image",
    "Patient or image identifiers in CSV can be matched to filenames in image directory",
    "Output directories can be created if missing",
    "File system permissions allow copy and move operations",
    "No special handling needed for filename collisions beyond default filesystem behavior"
  ],
  "risks": [
    "Stage 2 move operation is irreversible; images removed from healthy/ cannot be recovered without re-running Stage 1",
    "Incorrect dataset_root or output_root paths could cause unintended file operations",
    "CSV may reference images that do not exist in the directory",
    "Dataset scale (memory, disk I/O) is unknown",
    "Multiple patients may have identically-named images, causing collision on copy/move"
  ],
  "open_questions": [
    "Which CSV column(s) and value(s) define a 'healthy' patient?",
    "Is the image-to-patient mapping one-to-one or one-to-many?",
    "What is the exact filename matching logic between CSV identifiers and image files?",
    "How is 'single scan' determined: one image file per patient, or one imaging session?",
    "How should filename collisions be handled during copy/move?",
    "Should a summary report be produced (counts, moved files list)?",
    "What should happen if output directories already exist (overwrite, skip, error)?"
  ]
}
```