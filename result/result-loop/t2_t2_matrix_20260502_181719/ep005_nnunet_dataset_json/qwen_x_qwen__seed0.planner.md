### Implementation Plan

#### Observed Facts:
- Dataset root: `<dataset_root>/Dataset001_LungLobeRight`
- Training images: `imagesTr/` directory
- Training labels: `labelsTr/` directory
- Test images: `imagesTs/` directory
- File format: `.nii.gz`
- Naming convention: `case_XXX_0000.nii.gz` for images, `case_XXX.nii.gz` for labels
- Single foreground class: `lung_lower_lobe_right`
- Modality: DRR (not CT)
- Using nnU-Net v2 schema

#### Assumptions:
- All training image files have corresponding label files with matching base names (`case_XXX_0000.nii.gz` → `case_XXX.nii.gz`)
- Test set images are named consistently with training set naming rules
- The `imagesTr`, `labelsTr`, and `imagesTs` directories contain only relevant files (no stray or duplicate files)
- The worker will scan all `.nii.gz` files in each directory to build the dataset JSON
- No additional metadata beyond what's required by nnU-Net v2 schema is needed

#### Constraints:
- Case IDs must be aligned between images and labels based on filename prefix (e.g., `case_001_0000.nii.gz` matches `case_001.nii.gz`)
- Only files ending in `.nii.gz` should be considered
- The test set must be included in the JSON if present
- Paths in the JSON must reflect the actual structure under the dataset root
- Schema version is strictly nnU-Net v2; no backward compatibility assumed

#### Risks:
- Incorrect alignment of case IDs between images and labels could lead to mislabeled data during training
- Including non-matching test cases may cause pipeline failures
- Overwriting existing `dataset.json` without confirmation could result in loss of manual edits
- Misinterpretation of schema fields can break downstream processing

#### Open Questions:
1. **Schema Field Definitions**: What are the exact required and optional fields in the nnU-Net v2 `dataset.json` schema? Are there specific validation rules for these fields?
2. **Path Handling**: Should relative paths be used inside the JSON, or absolute paths? If relative, how should they be defined relative to the dataset root?
3. **Test Set Inclusion**: Is there a requirement to distinguish test cases from training cases in the JSON structure, or is inclusion sufficient?
4. **File Selector Semantics**: How should the script handle multiple `.nii.gz` files per case (e.g., if both `case_001_0000.nii.gz` and `case_001_0001.nii.gz` exist)?
5. **Completion Marker Policy**: Is there a mechanism to avoid reprocessing an already-generated `dataset.json`?
6. **Overwrite Policy**: Should the script overwrite an existing `dataset.json` silently, or warn before doing so?

---

```json
{
  "assumptions": [
    "All training image files have corresponding label files with matching base names.",
    "Test set images are named consistently with training set naming rules.",
    "The worker will scan all .nii.gz files in each directory to build the dataset JSON.",
    "No additional metadata beyond what's required by nnU-Net v2 schema is needed."
  ],
  "risks": [
    "Incorrect alignment of case IDs between images and labels could lead to mislabeled data during training.",
    "Including non-matching test cases may cause pipeline failures.",
    "Overwriting existing dataset.json without confirmation could result in loss of manual edits.",
    "Misinterpretation of schema fields can break downstream processing."
  ],
  "open_questions": [
    "What are the exact required and optional fields in the nnU-Net v2 dataset.json schema?",
    "Should relative paths be used inside the JSON, or absolute paths? If relative, how should they be defined?",
    "Is there a requirement to distinguish test cases from training cases in the JSON structure?",
    "How should the script handle multiple .nii.gz files per case?",
    "Is there a mechanism to avoid reprocessing an already-generated dataset.json?",
    "Should the script overwrite an existing dataset.json silently, or warn before doing so?"
  ]
}
```