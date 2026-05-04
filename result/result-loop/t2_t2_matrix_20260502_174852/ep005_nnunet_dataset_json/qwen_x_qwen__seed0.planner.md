### Implementation Spec: Generate `dataset.json` for nnU-Net v2 Dataset

#### Observed Facts:
- The dataset is structured under `<dataset_root>/Dataset001_LungLobeRight/`.
- The directory contains `imagesTr/`, `labelsTr/`, and `imagesTs/`.
- The task is to segment the **lung lower lobe right**.
- The modality is **DRR** (not CT).
- The dataset uses **nnU-Net v2** conventions.

#### Assumptions:
- The `imagesTr/` and `labelsTr/` directories contain matching image and label files (e.g., `.nii.gz`).
- The `imagesTs/` directory may be empty or contain test images; no action is required for it in this script.
- File names in `imagesTr/` and `labelsTr/` match exactly (e.g., `case_001.nii.gz` and `case_001_label.nii.gz`).
- The dataset ID (`Dataset001`) is fixed and corresponds to the folder name.
- The foreground class is named `lung_lower_lobe_right`.

#### Constraints:
- The generated `dataset.json` must conform to the nnU-Net v2 schema.
- The `modality` field must reflect `DRR`.
- The `labels` dictionary must map `0` to `background` and `1` to `lung_lower_lobe_right`.
- The `training` list must include all training cases with correct paths relative to the dataset root.
- No additional fields should be added unless required by the schema.

#### Risks:
- Incorrectly assuming file naming conventions can lead to mismatched image-label pairs.
- Omitting required keys in `dataset.json` will cause nnU-Net to fail during preprocessing.
- Using incorrect class mapping (e.g., `0` for foreground) will mislabel data during training.

#### Open Questions:
1. Are there any specific naming conventions for files in `imagesTr/` and `labelsTr/` beyond matching base names?
2. Is the `description` field required or can it be left as an empty string?
3. Should the `reference` or `licence` fields be included? If so, what values should they have?
4. Are there any expected metadata fields like `release` or `tensorImageSize` that must be included?

---

```json
{
  "assumptions": [
    "File names in imagesTr and labelsTr match exactly.",
    "The dataset ID is fixed as Dataset001.",
    "Only one foreground class is used: lung_lower_lobe_right.",
    "Modality is DRR."
  ],
  "risks": [
    "Mismatched image-label file names will cause incorrect pairing.",
    "Incorrect class mapping (e.g., 0 for foreground) will mislabel training data.",
    "Missing required keys in dataset.json will break nnU-Net pipeline."
  ],
  "open_questions": [
    "What are the exact naming conventions for image and label files?",
    "Is the description field required or can it be omitted?",
    "Should reference or licence fields be included?",
    "Are there any required metadata fields such as release or tensorImageSize?"
  ]
}
```