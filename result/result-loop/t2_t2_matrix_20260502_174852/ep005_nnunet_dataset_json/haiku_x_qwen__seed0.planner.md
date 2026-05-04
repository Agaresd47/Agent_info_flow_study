# Implementation Spec: nnU-Net v2 dataset.json Generator

## Observed Facts

- User has nnU-Net v2 directory structure already in place at `<dataset_root>/Dataset001_LungLobeRight/`
- Three subdirectories exist: `imagesTr/`, `labelsTr/`, `imagesTs/`
- Task: binary segmentation (single foreground class)
- Foreground label name: `lung_lower_lobe_right`
- Imaging modality: DRR (Digital Radiography Reconstruction), not CT
- Output required: `dataset.json` file in nnU-Net v2 format

## Assumptions

1. `dataset.json` should be placed at `<dataset_root>/Dataset001_LungLobeRight/dataset.json`
2. Training images and labels are paired by filename (e.g., `image_001.nii.gz` ↔ `image_001.nii.gz`)
3. Test images have no corresponding labels in `imagesTs/`
4. All images use standard medical imaging file extensions (`.nii.gz`, `.nii`, or `.mha`)
5. The dataset.json schema follows nnU-Net v2 specification with fields: `name`, `description`, `reference`, `licence`, `release`, `modality`, `labels`, `numTraining`, `numTest`, `training`, `test`
6. Modality field should accept "DRR" as a valid string value
7. Label integer mapping: background=0, `lung_lower_lobe_right`=1

## Constraints & Risks

⚠️ **Irreversible/Unsafe Actions:**
- Do not overwrite existing `dataset.json` without explicit user confirmation
- Do not modify image or label files during discovery

⚠️ **Critical Constraints:**
- File discovery must be robust to mixed extensions (`.nii.gz` vs `.nii`)
- Must handle cases where `imagesTs/` exists but is empty
- Label integer assignment (1 for foreground) is fixed; do not infer from file content
- DRR modality may require special handling in downstream nnU-Net preprocessing; document this assumption

⚠️ **Data Integrity:**
- Verify that every training image has a corresponding label before writing JSON
- Report mismatches (orphaned images or labels) before proceeding

## Open Questions

1. **Dataset root path**: Should the script accept `<dataset_root>` as a command-line argument, environment variable, or hardcoded path?
2. **File discovery**: Should the script scan directories or require a manifest file?
3. **Metadata fields**: What values should populate `name`, `description`, `reference`, `licence`, `release`? (User provided only the class name and modality.)
4. **DRR preprocessing**: Are there known nnU-Net v2 configuration changes needed for DRR vs. CT? Should the script document this?
5. **Validation**: Should the script validate image dimensions, spacing, or data types, or only check file existence?
6. **Output location**: Confirm the exact path where `dataset.json` should be written.

## First Actions for Worker

1. **Clarify inputs**: Confirm dataset root path and whether metadata (name, description, etc.) should be user-provided or auto-generated.
2. **Design file discovery**: Decide on scanning strategy (recursive glob, sorted listing) and extension handling.
3. **Define schema template**: Reference nnU-Net v2 official documentation to confirm exact `dataset.json` structure and field requirements.
4. **Plan validation**: Outline checks for file pairing and report format for mismatches.
5. **Document DRR handling**: Note any special considerations for DRR modality in comments/output.

---

```json
{
  "assumptions": [
    "dataset.json will be placed at <dataset_root>/Dataset001_LungLobeRight/dataset.json",
    "Training images and labels are paired by filename stem",
    "All images use standard medical imaging extensions (.nii.gz, .nii, or .mha)",
    "Label mapping: background=0, lung_lower_lobe_right=1",
    "imagesTs/ may be empty or contain unpaired test images",
    "nnU-Net v2 dataset.json schema includes: name, description, reference, licence, release, modality, labels, numTraining, numTest, training, test"
  ],
  "risks": [
    "Overwriting existing dataset.json without confirmation",
    "Mismatched training image-label pairs causing silent failures",
    "Mixed file extensions requiring robust discovery logic",
    "DRR modality may have undocumented preprocessing implications in nnU-Net v2",
    "Empty or malformed metadata fields could cause downstream pipeline errors"
  ],
  "open_questions": [
    "Is dataset root path a CLI argument, environment variable, or hardcoded?",
    "Should metadata fields (name, description, reference, licence, release) be user-provided or auto-generated?",
    "What validation should be performed on images (dimensions, spacing, data type)?",
    "Are there known nnU-Net v2 configuration changes required for DRR modality?",
    "Should the script report detailed mismatch diagnostics or fail silently?"
  ]
}
```