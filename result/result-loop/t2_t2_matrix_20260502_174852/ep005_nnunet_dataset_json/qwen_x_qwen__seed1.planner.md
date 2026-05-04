### Implementation Plan: Generate `dataset.json` for nnU-Net v2 Dataset

#### Observed Facts:
- The dataset is structured under `<dataset_root>/Dataset001_LungLobeRight/`.
- The directory contains `imagesTr/`, `labelsTr/`, and `imagesTs/`.
- The task is to generate a `dataset.json` file for a single-class foreground: `lung_lower_lobe_right`.
- The modality is DRR (not CT).

---

#### Assumptions:
- The `imagesTr/` and `labelsTr/` directories contain corresponding image and label files (e.g., `.png`, `.nii.gz`) with matching filenames.
- The `imagesTs/` directory may be empty or contain test images; it will be handled accordingly.
- File extensions for images and labels are consistent within their respective directories.
- The `dataset.json` will follow the nnU-Net v2 schema for dataset configuration.

---

#### Risks & Constraints:
- Incorrectly mapping image and label files can lead to misalignment during training.
- If `imagesTs/` is not used, it should be omitted or left empty in the JSON.
- The `modality` field must be set to `"DRR"` as specified.
- The `labels` dictionary must map `0` to `"background"` and `1` to `"lung_lower_lobe_right"`.
- Any deviation from nnU-Net v2 schema may cause pipeline failures.

---

#### Open Questions:
1. What are the exact file extensions for images and labels in `imagesTr/` and `labelsTr/`?
2. Are there any additional metadata fields required in `dataset.json` beyond what is implied by the prompt?
3. Should `training` and `test` keys in `dataset.json` include all available data, or only `imagesTr/` and `imagesTs/` respectively?

---

```json
{
  "assumptions": [
    "Images and labels in `imagesTr/` and `labelsTr/` have matching filenames and consistent extensions.",
    "The `imagesTs/` directory exists but may be empty.",
    "The modality is strictly defined as \"DRR\".",
    "Only one foreground class (`lung_lower_lobe_right`) is present."
  ],
  "risks": [
    "Misalignment between image and label files due to mismatched filenames or extensions.",
    "Incorrectly populating `training` or `test` entries in `dataset.json` if file structure is not fully known.",
    "Failure to comply with nnU-Net v2 schema for `dataset.json`."
  ],
  "open_questions": [
    "What are the file extensions for images and labels?",
    "Are additional metadata fields required in `dataset.json`?",
    "Should `test` key include contents of `imagesTs/` even if empty?"
  ]
}
```