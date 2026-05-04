# Implementation Spec: nnU-Net v2 dataset.json Generator for DRR Lung Lobe Segmentation

## Observed Facts

- **Dataset location**: `<dataset_root>/Dataset001_LungLobeRight/` with subdirectories `imagesTr/`, `labelsTr/`, `imagesTs/`
- **nnU-Net version**: v2
- **Task**: Single-class foreground segmentation
- **Foreground label name**: `lung_lower_lobe_right`
- **Modality**: DRR (Digital Radiography Reconstruction), not CT
- **Language context**: Request in Chinese; output should be usable by nnU-Net pipeline

## Constraints & Requirements

1. **Schema compliance**: Output must conform to nnU-Net v2 `dataset.json` specification
2. **Single-class foreground**: Only one label class beyond background (label value typically 1)
3. **Modality specification**: DRR is a 2D projection modality; must be correctly declared in the JSON
4. **Directory structure**: Script must validate or assume the three subdirectories exist and contain paired image/label files
5. **File pairing logic**: Training images in `imagesTr/` must correspond to labels in `labelsTr/`; test images in `imagesTs/` have no labels

## Risks & Destructive Actions

- **No overwrite policy specified**: If `dataset.json` already exists at the target location, unclear whether to skip, overwrite, or error. This is a write-safety decision.
- **File naming convention unknown**: nnU-Net v2 expects specific naming patterns (e.g., `case_001_0000.nii.gz` for images, `case_001.nii.gz` for labels). Script must either enforce or validate these patterns.
- **Label value assumption**: Foreground label value (typically 1) is not explicitly stated; background is assumed to be 0.
- **Modality channel count**: DRR is typically single-channel (grayscale), but exact channel specification in JSON is not confirmed.
- **No validation of file integrity**: Script will not verify that label files contain only valid label values or that image/label pairs are spatially compatible.

## Open Questions

1. **Target output path**: Where should `dataset.json` be written? (e.g., `<dataset_root>/Dataset001_LungLobeRight/dataset.json`?)
2. **File naming pattern**: What are the exact file extensions and naming conventions in `imagesTr/`, `labelsTr/`, `imagesTs/`? (e.g., `.nii.gz`, `.nrrd`, `.mha`?)
3. **Foreground label integer value**: Should the foreground label be encoded as 1, or is a different integer specified?
4. **Channel metadata**: Should the JSON specify channel names or descriptions beyond the modality type?
5. **Overwrite behavior**: If `dataset.json` exists, should the script skip, overwrite, or prompt?
6. **File discovery method**: Should the script auto-discover all files in each directory, or require an explicit file list?
7. **Spacing/geometry metadata**: Should the script extract or infer voxel spacing, image dimensions, or other geometric properties from the image files themselves?
8. **License/description fields**: Are optional JSON fields like `"license"`, `"description"`, `"reference"` required or desired?

## First Actions for Worker

1. **Clarify file structure**: List or inspect one example file from each of `imagesTr/`, `labelsTr/`, `imagesTs/` to confirm naming pattern and format.
2. **Confirm target path**: Determine exact output location for `dataset.json`.
3. **Validate nnU-Net v2 schema**: Reference the official nnU-Net v2 documentation or a known valid `dataset.json` example to confirm all required and optional fields.
4. **Define write safety**: Decide on overwrite/skip/error behavior before implementation.
5. **Prototype file discovery**: Write a minimal file-listing function that matches the actual naming convention in the dataset directories.

---

```json
{
  "assumptions": [
    "Background label value is 0; foreground (lung_lower_lobe_right) is 1",
    "DRR images are single-channel (grayscale) 2D or 2D-stacked projections",
    "Files in imagesTr/ and labelsTr/ are paired by a consistent naming scheme",
    "imagesTs/ contains only images; no ground-truth labels are present",
    "nnU-Net v2 dataset.json schema is the target format (not v1 or custom variant)",
    "The dataset_root directory path is provided or discoverable at runtime"
  ],
  "risks": [
    "Write safety: No overwrite policy specified; script could silently overwrite existing dataset.json",
    "File naming: Unknown naming convention could cause incorrect pairing or discovery failures",
    "Schema version mismatch: If nnU-Net v2 schema differs from assumed structure, JSON will be invalid",
    "No file validation: Script will not verify label integrity, image-label spatial alignment, or data type correctness",
    "Modality encoding: DRR may require special handling in nnU-Net v2 that is not documented in the request",
    "Incomplete metadata: Voxel spacing, image dimensions, and other geometric properties are not specified; unclear if they should be auto-extracted or omitted"
  ],
  "open_questions": [
    "What is the exact file naming pattern and extension in imagesTr/, labelsTr/, and imagesTs/?",
    "Where should dataset.json be written (exact path)?",
    "What should happen if dataset.json already exists?",
    "What is the foreground label integer value (assumed 1)?",
    "Should the script extract voxel spacing or geometric metadata from image files?",
    "Are optional JSON fields (license, description, reference) required?",
    "Is DRR modality correctly specified as a single-channel 2D modality in nnU-Net v2, or does it require special handling?",
    "Should the script validate that all imagesTr/ files have corresponding labelsTr/ files?"
  ]
}
```