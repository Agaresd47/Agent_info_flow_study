### Implementation Plan

#### Observed Facts:
- Dataset root: `<dataset_root>/Dataset001_LungLobeRight/`
- Training image directory: `imagesTr/`
- Training label directory: `labelsTr/`
- Test image directory: `imagesTs/`
- Modality: DRR (not CT)
- Foreground class: `lung_lower_lobe_right`
- Using nnU-Net v2

#### Assumptions:
- The dataset follows nnU-Net v2 directory structure.
- All training images and labels have corresponding filenames (e.g., `case001_0000.nii.gz` and `case001.nii.gz`).
- File extensions for images and labels are `.nii.gz`.
- Test set files are named consistently with training set files.
- The `dataset.json` will be generated in the same dataset folder (`Dataset001_LungLobeRight/`).

#### Constraints:
- Case IDs must align between images and labels based on filename prefixes (e.g., `case001`).
- Only training cases should be included in the `training` field of `dataset.json`.
- Test cases should be listed under the `test` field if they exist.
- Schema fields must conform to nnU-Net v2 specification.

#### Open Questions:
1. **Schema Field Details**: What are the exact required and optional fields in the nnU-Net v2 `dataset.json` schema? Are there specific rules for `description`, `reference`, `licence`, `release`, etc.?
2. **Path Handling**: Should relative paths be used or absolute paths? If relative, what is the base path context expected by nnU-Net?
3. **File Extension Handling**: Is it guaranteed that all files in `imagesTr/` and `labelsTr/` have `.nii.gz` extension? What about test set files in `imagesTs/`?
4. **Test Set Inclusion**: Is the presence of `imagesTs/` sufficient to include test cases in `dataset.json`? Should we check for matching label files in `labelsTs/`?
5. **Case ID Alignment Rule**: How strictly must the case ID match between image and label files? For example, does `case001_0000.nii.gz` imply `case001.nii.gz`?

---

```json
{
  "assumptions": [
    "The dataset follows nnU-Net v2 directory structure.",
    "Training images and labels have corresponding filenames with consistent prefixes.",
    "All files use .nii.gz extension.",
    "Test set files are named consistently with training set files.",
    "The dataset.json will be placed in the dataset root directory."
  ],
  "risks": [
    "Mismatched case IDs between images and labels could lead to incorrect mapping.",
    "Incorrect handling of file extensions may cause runtime errors.",
    "Including test cases without verifying their existence in both image and label directories can result in incomplete metadata."
  ],
  "open_questions": [
    "What are the exact required and optional fields in the nnU-Net v2 dataset.json schema?",
    "Should relative or absolute paths be used in the JSON, and what is the expected base path context?",
    "Are all files in imagesTr/ and labelsTr/ guaranteed to have .nii.gz extension?",
    "Is the presence of imagesTs/ sufficient to include test cases in dataset.json, and should we verify labelsTs/ too?",
    "How strictly must the case ID match between image and label files?"
  ]
}
```