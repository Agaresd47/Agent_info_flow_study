# Implementation Spec: nnU-Net v2 dataset.json Generator

## Observed Facts

- User has a dataset directory: `<dataset_root>/Dataset001_LungLobeRight/`
- Directory structure follows nnU-Net v2 convention with subdirectories: `imagesTr/`, `labelsTr/`, `imagesTs/`
- Single foreground class: `lung_lower_lobe_right`
- Imaging modality: DRR (Digital Radiography Reconstruction), not CT
- Task: right lower lobe lung segmentation
- Language context: request in Chinese; output should be usable by user

## Assumptions

1. **File naming convention**: Image and label files follow nnU-Net v2 naming (e.g., `case_0000_0000.nii.gz` for images, `case_0000.nii.gz` for labels)
2. **Single modality**: DRR images are single-channel (not multi-modal stacks)
3. **Label encoding**: Labels use integer value (e.g., 1 for foreground, 0 for background); exact value TBD
4. **No validation split**: Only `imagesTr/labelsTr/` and `imagesTs/` exist; no separate validation directory
5. **dataset.json location**: Output file should be written to `<dataset_root>/dataset.json`
6. **nnU-Net v2 schema compatibility**: Output must conform to nnU-Net v2's expected `dataset.json` structure

## Constraints & Risks

- **Irreversible action risk**: Writing `dataset.json` will be read by nnU-Net preprocessing; incorrect schema will cause silent failures or cryptic errors downstream
- **Modality specification**: DRR is non-standard for nnU-Net (typically CT/MRI); must verify whether modality string affects preprocessing (e.g., intensity normalization, resampling)
- **Label value ambiguity**: Worker must determine the integer label value used in `labelsTr/` files before hardcoding into JSON
- **File discovery**: Script must robustly scan `imagesTr/` and `labelsTr/` to count cases and infer file extensions; brittle glob patterns could miss files
- **No error recovery**: If dataset.json is malformed, user will discover it only after attempting nnU-Net training

## Open Questions

1. **Label integer value**: What integer value represents the foreground class in the label files? (e.g., 1, 255, or other?)
2. **File extension**: Are image/label files `.nii.gz`, `.nii`, or mixed? Should script auto-detect or require user specification?
3. **Channel dimension**: Are DRR images truly single-channel, or do they have multiple reconstructions stacked?
4. **Intensity range**: What is the expected intensity range for DRR images? (affects normalization hints in dataset.json)
5. **nnU-Net version confirmation**: Should script target nnU-Net v2 specifically, or support both v1 and v2?
6. **Case count validation**: Should script warn if `imagesTr/` and `labelsTr/` have mismatched case counts?

## First Actions for Worker

1. **Inspect sample files**: Read one image and one label file from the dataset to determine:
   - Actual file extension(s)
   - Label value(s) present in label files
   - Image shape and intensity range
2. **Define dataset.json schema**: Document the exact nnU-Net v2 `dataset.json` structure required (keys: `name`, `description`, `reference`, `license`, `release`, `modality`, `labels`, `numTraining`, `numTest`, `training`, `test`)
3. **Plan file discovery logic**: Decide on glob pattern or directory listing approach to robustly find all training cases
4. **Specify output location**: Confirm `<dataset_root>/dataset.json` is the correct write target
5. **Add validation checks**: Decide whether script should validate case count consistency and warn on mismatches

---

```json
{
  "assumptions": [
    "Image and label files follow nnU-Net v2 naming convention (case_XXXX_YYYY.nii.gz for images, case_XXXX.nii.gz for labels)",
    "DRR images are single-channel (2D or 3D reconstructions without multi-modal stacking)",
    "Labels use a single integer value to encode the foreground class (background = 0)",
    "dataset.json should be written to <dataset_root>/dataset.json",
    "nnU-Net v2 is the target framework; schema must match v2 expectations",
    "No separate validation split exists; only training and test splits"
  ],
  "risks": [
    "Malformed dataset.json will cause silent failures or cryptic errors during nnU-Net preprocessing; no immediate feedback to user",
    "DRR modality is non-standard for nnU-Net; preprocessing assumptions (normalization, resampling) may be incorrect",
    "Incorrect label integer value in JSON will cause all labels to be ignored or misinterpreted",
    "Brittle file discovery (glob patterns) may miss files with unexpected extensions or naming",
    "Mismatched case counts between imagesTr/ and labelsTr/ will not be caught without explicit validation",
    "Writing dataset.json is irreversible; incorrect schema cannot be auto-corrected by nnU-Net"
  ],
  "open_questions": [
    "What integer value represents the foreground class in labelsTr/ files?",
    "Are all files .nii.gz, or is there a mix of extensions? Should script auto-detect or require user input?",
    "What is the intensity range of DRR images? (affects normalization metadata in dataset.json)",
    "Are DRR images truly single-channel, or do they contain multiple reconstructions?",
    "Should the script validate that imagesTr/ and labelsTr/ contain the same number of cases?",
    "Does nnU-Net v2 require specific metadata fields for non-standard modalities like DRR?"
  ]
}
```