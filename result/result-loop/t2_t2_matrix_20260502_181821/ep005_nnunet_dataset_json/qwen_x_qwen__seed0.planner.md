### Implementation Plan

#### Observed Facts:
- Dataset directory structure: `<dataset_root>/Dataset001_LungLobeRight/`
- Subdirectories: `imagesTr/`, `labelsTr/`, `imagesTs/`
- Task: lung right lower lobe segmentation (single-class foreground)
- Modality: DRR (not CT)
- Using nnU-Net v2

#### Assumptions:
- All training image and label files have matching base names (e.g., `case001_0000.nii.gz` and `case001.nii.gz`)
- File extensions are `.nii.gz` for both images and labels
- Test set (`imagesTs/`) will be included in the generated `dataset.json`
- The dataset ID is `Dataset001_LungLobeRight`

#### Constraints:
- The script must generate a valid `dataset.json` according to nnU-Net v2 schema
- Case IDs must align between images and labels based on filename prefix
- Paths in `dataset.json` should be relative to the dataset root
- No destructive writes or overwrites unless explicitly allowed (not specified)

#### Open Questions:
1. **Schema Field Details**: What are the exact required fields in the `dataset.json` schema for nnU-Net v2? Specifically, what are the expected keys under `"training"` and `"test"`?
2. **Path Handling**: Should paths in `dataset.json` use forward slashes `/` or platform-specific separators?
3. **File Extension Handling**: Are there any specific rules about how to handle file extensions beyond `.nii.gz`?
4. **Test Set Inclusion**: Is the test set (`imagesTs/`) intended to be listed in the `"test"` key of `dataset.json`? Or should it be omitted?
5. **Case ID Alignment Rule**: How strictly must filenames match between images and labels? For example, if an image is named `case001_0000.nii.gz`, does the corresponding label have to be `case001.nii.gz`?

---

```json
{
  "assumptions": [
    "All training image and label files have matching base names.",
    "File extensions are .nii.gz for both images and labels.",
    "Test set (imagesTs/) will be included in the generated dataset.json.",
    "The dataset ID is Dataset001_LungLobeRight."
  ],
  "risks": [
    "Incorrect alignment of case IDs between images and labels may lead to mislabeled training data.",
    "Improper handling of paths could cause runtime errors when loading data.",
    "Including incorrect or malformed entries in dataset.json can break nnU-Net workflows."
  ],
  "open_questions": [
    "What are the exact required fields in the dataset.json schema for nnU-Net v2?",
    "Should paths in dataset.json use forward slashes or platform-specific separators?",
    "Are there specific rules for handling file extensions beyond .nii.gz?",
    "Is the test set intended to be listed in the \"test\" key of dataset.json?",
    "How strictly must filenames match between images and labels?"
  ]
}
```