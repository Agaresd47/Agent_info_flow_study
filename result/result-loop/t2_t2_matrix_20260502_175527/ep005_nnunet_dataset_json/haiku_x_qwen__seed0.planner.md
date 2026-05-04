# Implementation Spec: nnU-Net v2 dataset.json Generator

## Observed Facts

- **Dataset location**: `<dataset_root>/Dataset001_LungLobeRight/` with subdirectories `imagesTr/`, `labelsTr/`, `imagesTs/`
- **Task**: Right lower lobe lung segmentation
- **Modality**: DRR (Digital Radiography Reconstruction), not CT
- **Label class**: Single foreground class named `lung_lower_lobe_right`
- **nnU-Net version**: v2
- **Output required**: `dataset.json` file

## Assumptions

1. The user will provide the exact filesystem path to `<dataset_root>` at runtime (or script will accept it as a parameter)
2. Training images in `imagesTr/` and corresponding labels in `labelsTr/` are already paired by filename convention
3. Test images in `imagesTs/` exist but do not require corresponding labels in the script
4. The dataset.json schema follows nnU-Net v2 specification (not v1)
5. File extensions are consistent within each directory (e.g., all `.nii.gz` or all `.nii`)
6. No existing `dataset.json` is present, or overwriting is acceptable

## Constraints & Risks

- **Schema version mismatch**: nnU-Net v2 dataset.json schema differs from v1; using wrong schema will cause pipeline failure
- **Modality specification**: DRR is non-standard for nnU-Net (typically CT/MRI); must verify whether modality field accepts arbitrary strings or requires predefined enum values
- **Label integer mapping**: The foreground class `lung_lower_lobe_right` must map to a specific integer label (typically 1 for single-class segmentation); background is typically 0
- **File discovery**: Script must robustly discover all training/test images without hardcoding filenames
- **Write safety**: No specification of whether to overwrite existing `dataset.json` or fail if present
- **Validation**: No specification of whether to validate file counts, image dimensions, or label consistency before writing

## Open Questions

1. **Dataset.json schema location**: Which exact nnU-Net v2 documentation or reference implementation defines the required schema fields (e.g., `channel_names`, `labels`, `numTraining`, `file_ending`)?
2. **File extension pattern**: What file extensions should the script search for in `imagesTr/`, `labelsTr/`, `imagesTs/`? (e.g., `.nii.gz`, `.nii`, `.mha`)
3. **Label integer value**: Should `lung_lower_lobe_right` map to label integer `1`, or is a different value required?
4. **Modality field value**: Does nnU-Net v2 accept `"DRR"` as a modality string, or must it be mapped to a standard value?
5. **Channel/modality count**: How many imaging channels/modalities per image? (Single DRR image = 1 channel, or multiple?)
6. **Output path**: Should `dataset.json` be written to `<dataset_root>/` or to `<dataset_root>/Dataset001_LungLobeRight/`?
7. **Overwrite behavior**: If `dataset.json` already exists, should the script fail, warn, or silently overwrite?
8. **Validation requirements**: Should the script validate that every training image has a corresponding label, or only report counts?
9. **Image metadata**: Should the script inspect image headers (dimensions, spacing) and include in dataset.json, or only list filenames?

---

```json
{
  "assumptions": [
    "User will provide or script will accept the dataset root path as a parameter",
    "Training and test images are already organized in the specified directory structure",
    "File naming convention allows pairing of images and labels by filename",
    "nnU-Net v2 dataset.json schema is the target (not v1)",
    "Single foreground class maps to integer label 1; background is 0",
    "Overwriting an existing dataset.json is acceptable"
  ],
  "risks": [
    "Using wrong dataset.json schema version will cause nnU-Net pipeline failure",
    "DRR modality may not be recognized by nnU-Net; modality field value is unspecified",
    "No validation of file pairing or image consistency before writing",
    "No specification of write-safety policy (overwrite vs. fail-if-exists)",
    "File extension discovery pattern is not specified; script may miss or misidentify files",
    "Label integer mapping for 'lung_lower_lobe_right' is not explicitly defined"
  ],
  "open_questions": [
    "Which nnU-Net v2 reference defines the exact dataset.json schema and required fields?",
    "What file extensions should be searched for in imagesTr/, labelsTr/, imagesTs/?",
    "What integer value should 'lung_lower_lobe_right' map to in the labels section?",
    "Is 'DRR' an acceptable modality string in nnU-Net v2, or must it be mapped differently?",
    "How many imaging channels per image (single DRR or multiple)?",
    "Should dataset.json be written to dataset_root/ or Dataset001_LungLobeRight/?",
    "What should happen if dataset.json already exists?",
    "Should the script validate image-label pairing and report mismatches?",
    "Should the script inspect image headers for metadata (dimensions, spacing)?"
  ]
}
```