# Implementation Spec: nnU-Net v2 dataset.json Generator for Lung Lower Lobe Right Segmentation

## Overview
Generate a valid `dataset.json` file for nnU-Net v2 that describes a single-class lung lower lobe right segmentation task using DRR (Digital Reconstructed Radiograph) modality. The script must align training images and labels by case ID and produce output conforming to nnU-Net v2 schema.

---

## Observed Facts

1. **Directory structure provided:**
   - `<dataset_root>/Dataset001_LungLobeRight/imagesTr/`
   - `<dataset_root>/Dataset001_LungLobeRight/labelsTr/`
   - `<dataset_root>/Dataset001_LungLobeRight/imagesTs/`

2. **Segmentation target:** Single foreground class named `lung_lower_lobe_right`

3. **Modality:** DRR (not CT)

4. **nnU-Net version:** v2 (not v1)

5. **Output requirement:** `dataset.json` file

---

## Implementation Constraints

### Schema & Metadata
- Must produce valid nnU-Net v2 `dataset.json` structure
- Must include all required top-level fields for v2 (exact field list is an open question)
- Must declare modality as DRR in the appropriate schema location
- Must declare exactly one foreground label with name `lung_lower_lobe_right`

### Case ID Alignment
- Training images and labels must be paired by matching case identifiers
- **Pairing rule:** Extract case ID from filename in `imagesTr/` and find corresponding file in `labelsTr/` with same case ID
- **Mismatch handling:** If a training image has no corresponding label (or vice versa), document this and decide whether to skip, error, or warn (see open questions)

### File Discovery & Naming
- **Image file selector:** Scan `imagesTr/` for all files matching a pattern (pattern TBD—see open questions)
- **Label file selector:** Scan `labelsTr/` for all files matching a pattern (pattern TBD)
- **Test set handling:** Determine whether `imagesTs/` entries should appear in `dataset.json` or be excluded (see open questions)
- **File suffix handling:** Preserve or normalize file extensions (e.g., `.nii.gz`, `.nii`, `.mha`)—decision required (see open questions)

### Path Representation in JSON
- Paths in `dataset.json` must be either:
  - Absolute filesystem paths, or
  - Relative to dataset root, or
  - Relative to `dataset.json` location
- **Decision required:** Which convention does nnU-Net v2 expect? (see open questions)

### Write Safety
- **Overwrite policy:** If `dataset.json` already exists at target location, should the script overwrite, skip, or error? (see open questions)
- **Validation:** Should the script validate the generated JSON against an nnU-Net v2 schema before writing?

---

## Assumptions

1. All files in `imagesTr/` and `labelsTr/` are valid and readable
2. Case IDs can be reliably extracted from filenames using a consistent delimiter or pattern
3. Each training image has exactly one corresponding label file
4. The dataset root path is provided as a command-line argument or environment variable
5. nnU-Net v2 is installed or its schema documentation is accessible
6. DRR modality is a valid entry in nnU-Net v2's modality enum
7. No preprocessing (resampling, normalization) is required in the JSON generation step

---

## Risks & Constraints

| Risk | Mitigation |
|------|-----------|
| **Misaligned case IDs** | Implement strict pairing validation; report unpaired files before writing JSON |
| **Inconsistent file extensions** | Decide on extension normalization rule upfront; document in script |
| **Path representation mismatch** | Verify path format against nnU-Net v2 source or documentation before implementation |
| **Schema version drift** | Hardcode expected v2 schema fields; fail loudly if required fields are missing |
| **Destructive overwrite** | Implement safe-write pattern (write to temp file, then atomic rename) or require explicit `--force` flag |
| **Empty or malformed filenames** | Skip files that cannot yield a valid case ID; log skipped files |

---

## First Actions for Worker

1. **Retrieve nnU-Net v2 schema documentation** for `dataset.json` structure (official repo or source code)
2. **Define case ID extraction logic:** Specify the filename pattern and delimiter used to extract case IDs (e.g., `case_001_0000.nii.gz` → case ID `001`)
3. **Implement file discovery:** Scan `imagesTr/` and `labelsTr/` directories; collect all files and their extracted case IDs
4. **Validate pairing:** Cross-check that every image case ID has a corresponding label case ID; log any mismatches
5. **Construct JSON payload:** Build the dataset.json structure with all required v2 fields, including modality, labels, and file references
6. **Write with safety:** Use atomic write (temp + rename) or conditional overwrite logic
7. **Test on provided directory structure:** Verify output is valid JSON and conforms to v2 schema

---

## Open Questions

1. **nnU-Net v2 dataset.json schema:** What are the exact required top-level fields? (e.g., `name`, `description`, `reference`, `license`, `release`, `modality`, `labels`, `numTraining`, `numTest`, `training`, `test`)

2. **Modality field format:** How should DRR be represented? Is it a string key (e.g., `"DRR"`) or a numeric code? Does nnU-Net v2 have a predefined enum?

3. **Label schema:** Should the single foreground class be represented as `{"1": "lung_lower_lobe_right"}` or another format? Is label `0` (background) implicit or explicit?

4. **Case ID extraction pattern:** What filename convention is used in `imagesTr/` and `labelsTr/`? (e.g., `case_001_0000.nii.gz`, `LungLobeRight_001.nii.gz`, etc.)

5. **Multi-channel images:** Does DRR data use a single channel or multiple channels? If multiple, how are channels encoded in filenames (e.g., `_0000`, `_0001` suffixes)?

6. **Test set in JSON:** Should `imagesTs/` entries be included in the `dataset.json` under a `"test"` key, or should the JSON only describe training data?

7. **Path format in JSON:** Should file paths be absolute, relative to dataset root, or relative to the JSON file location?

8. **File extension handling:** Should extensions be preserved as-is, normalized to a single format, or stripped from the JSON?

9. **Unpaired files:** If an image in `imagesTr/` has no corresponding label in `labelsTr/`, should the script skip it, error, or warn and continue?

10. **Overwrite behavior:** If `dataset.json` already exists, should the script overwrite, skip, or require a `--force` flag?

11. **Validation:** Should the generated JSON be validated against an nnU-Net v2 schema before writing? If so, where is the schema located?

---

```json
{
  "assumptions": [
    "All files in imagesTr/ and labelsTr/ are readable and valid",
    "Case IDs can be reliably extracted from filenames using a consistent pattern",
    "Each training image has exactly one corresponding label file",
    "DRR is a valid modality in nnU-Net v2",
    "No preprocessing is required during JSON generation",
    "nnU-Net v2 schema documentation is accessible"
  ],
  "risks": [
    "Misaligned case IDs between images and labels will produce invalid training pairs",
    "Inconsistent file extension handling may cause nnU-Net v2 to fail file discovery",
    "Incorrect path format in JSON will prevent nnU-Net v2 from locating files",
    "Overwriting existing dataset.json without warning is destructive and irreversible",
    "Schema version mismatch (v1 vs v2) will cause silent failures or runtime errors",
    "Unpaired files (image without label or vice versa) will corrupt training data"
  ],
  "open_questions": [
    "What are the exact required top-level fields in nnU-Net v2 dataset.json?",
    "How should DRR modality be represented in the schema (string, enum, numeric code)?",
    "What is the expected label schema format for a single foreground class?",
    "What filename convention is used in imagesTr/ and labelsTr/ for case ID extraction?",
    "Are multi-channel images used, and if so, how are channels encoded in filenames?",
    "Should imagesTs/ entries be included in dataset.json or excluded?",
    "Should file paths in JSON be absolute, relative to dataset root, or relative to JSON location?",
    "Should file extensions be preserved, normalized, or stripped in the JSON?",
    "How should unpaired files (image without label) be handled?",
    "What is the overwrite policy if dataset.json already exists?",
    "Should the generated JSON be validated against an nnU-Net v2 schema before writing?"
  ]
}
```