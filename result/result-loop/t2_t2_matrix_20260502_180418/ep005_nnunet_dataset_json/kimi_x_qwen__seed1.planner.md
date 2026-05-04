## Implementation Spec: nnU-Net v2 dataset.json Generator for Lung Lower Lobe Right Segmentation

### Observed Facts
- **Task**: Single-class semantic segmentation (lung_lower_lobe_right)
- **nnU-Net version**: v2 (explicitly stated)
- **Dataset directory**: `<dataset_root>/Dataset001_LungLobeRight/`
- **Subdirectories present**: `imagesTr/`, `labelsTr/`, `imagesTs/`
- **Modality**: DRR (Digital Reconstructed Radiograph, not CT)
- **Output required**: `dataset.json` file

### Required Schema Fields (nnU-Net v2)

The worker must populate these exact fields per nnU-Net v2 specification:

| Field | Type | Description | Status |
|-------|------|-------------|--------|
| `name` | string | Dataset name | Must derive from directory or be specified |
| `description` | string | Human-readable description | Required |
| `reference` | string | Data source reference | Required (can be empty string) |
| `licence` | string | License string | Required (can be empty string) |
| `release` | string | Release date/version | Required (can be empty string) |
| `tensorImageSize` | string | Spatial dimensions | `"2D"` or `"3D"` — **OPEN QUESTION** |
| `modality` | dict | {0: "DRR"} | Required; DRR is non-standard, verify v2 accepts arbitrary strings |
| `labels` | dict | {0: "background", 1: "lung_lower_lobe_right"} | Required |
| `numTraining` | int | Count of training cases | Derived from `imagesTr/` |
| `numTest` | int | Count of test cases | Derived from `imagesTs/` |
| `training` | list | List of dicts with `image`, `label` paths | Required |
| `test` | list | List of dicts with `image` paths | Required (can be empty list) |

### Case ID Alignment Rules

**Critical constraint**: nnU-Net v2 requires strict filename correspondence between images and labels.

**Training set alignment**:
- For each case ID `CASE_ID`, there must exist:
  - `imagesTr/CASE_ID_0000.{ext}` — the image file
  - `labelsTr/CASE_ID.{ext}` — the label file
- The `_0000` suffix is mandatory for images (channel identifier)
- Extensions must match between image and label for the same case

**Test set handling**:
- `imagesTs/` contains test images: `CASE_ID_0000.{ext}`
- Test images have **no corresponding labels** (by definition)
- Test cases must be listed in `dataset.json["test"]` with `image` field only

### Path Format in JSON

- Paths must be **relative to `dataset.json` location** (i.e., the `Dataset001_LungLobeRight/` directory)
- Format: `"./imagesTr/CASE_ID_0000.nii.gz"` or without leading `./` — **OPEN QUESTION: exact convention**
- Use forward slashes regardless of platform

### File Extension Handling

**OPEN QUESTIONS**:
- What file extension do the DRR images use? (`.nii.gz`, `.nii`, `.mha`, `.png`, `.jpg`?)
- Are images compressed NIfTI (`.nii.gz`) or another format?
- Does nnU-Net v2 accept non-NIfTI formats for DRR?

### Implementation Steps for Worker

1. **Discovery phase**: List all files in `imagesTr/`, `labelsTr/`, `imagesTs/` to determine extensions and validate naming
2. **Case ID extraction**: Parse filenames to extract base case IDs (strip `_0000` suffix and extension from images)
3. **Alignment validation**: Verify every training image has exactly one matching label; every training label has exactly one matching image
4. **Mismatches**: Report any orphaned images/labels as errors — do not silently skip
5. **JSON generation**: Populate schema with discovered cases
6. **Write location**: `Dataset001_LungLobeRight/dataset.json`

### Safety Constraints

| Constraint | Enforcement |
|------------|-------------|
| **No destructive writes** | If `dataset.json` already exists, worker must abort or prompt — **overwrite policy is OPEN QUESTION** |
| **Validation before write** | Verify all referenced files exist before generating JSON |
| **Empty directories** | If `imagesTr/` is empty, this is an error condition |
| **Case sensitivity** | Assume case-sensitive filesystem; preserve exact case from filenames |

### Risks Requiring Explicit Handling

- **DRR modality non-standard**: nnU-Net v2's modality field typically expects standard strings like `"CT"`, `"MRI"`. Using `"DRR"` may require verification or fallback handling.
- **2D vs 3D ambiguity**: DRRs are 2D projections, but nnU-Net v2 may expect 3D volumes. The `tensorImageSize` field and network configuration implications are unclear.
- **File format mismatch**: If DRRs are stored as 2D images (PNG/JPG) rather than NIfTI, nnU-Net v2's data loading may fail.
- **Channel dimension**: Single-modality DRR should use `_0000` suffix, but multi-channel DRR variants would require `_0001`, etc. — assume single channel unless discovered otherwise.

### Open Questions (Must Be Resolved)

1. What is the exact file extension of the DRR images and labels? (`.nii.gz`, `.nii`, `.png`, etc.)
2. Are the DRR images 2D or 3D volumes? This affects `tensorImageSize` and nnU-Net configuration.
3. Does nnU-Net v2 accept arbitrary modality strings like `"DRR"`, or must it be mapped to a standard type?
4. What is the exact path format convention — with or without leading `./`?
5. What is the overwrite policy if `dataset.json` already exists?
6. Are there any cases with multiple channels (requiring `_0001`, `_0002` suffixes)?
7. Is there a specific `name` field format required, or can it be derived from directory name `Dataset001_LungLobeRight`?
8. Should `dataset.json` include pretty-printing/indentation, or compact format?

```json
{
  "assumptions": [
    "Dataset directory structure follows strict nnU-Net v2 convention with imagesTr/, labelsTr/, imagesTs/ subdirectories",
    "All training images use single-channel naming with _0000 suffix",
    "File extensions are consistent across all images and labels within the dataset",
    "Case IDs contain no underscore characters that would conflict with the _0000 channel suffix parsing",
    "DRR modality can be represented as string 'DRR' in the modality dictionary",
    "Test set imagesTs/ should be included in dataset.json even without labels",
    "Worker has read access to all subdirectories and write access to dataset root"
  ],
  "risks": [
    "DRR is non-standard modality: nnU-Net v2 may reject or misinterpret 'DRR' string, causing preprocessing/training failures",
    "2D DRR images may conflict with nnU-Net v2's default 3D assumptions, requiring explicit 2D configuration",
    "Non-NIfTI file formats (PNG, JPG) may not be compatible with nnU-Net v2's default image reader",
    "Silent case ID misalignment (missing _0000 suffix, extra underscores) will cause training data loading failures",
    "Existing dataset.json overwrite could destroy manual corrections or metadata",
    "Empty or malformed imagesTs/ directory may cause numTest mismatch with actual listed cases",
    "Case-sensitive filesystems may cause 'Case_001' vs 'case_001' mismatches between images and labels"
  ],
  "open_questions": [
    "What is the exact file extension of DRR images and labels? (.nii.gz, .nii, .png, .jpg, .mha?)",
    "Are DRR images 2D or 3D? This determines tensorImageSize value and nnU-Net plan configuration",
    "Does nnU-Net v2 accept arbitrary modality strings, or must 'DRR' be mapped to a standard type like 'CT' or 'XR'?",
    "What is the canonical path format in dataset.json — './imagesTr/...' or 'imagesTr/...' (without leading dot-slash)?",
    "What is the overwrite policy if dataset.json already exists — abort, backup, or clobber?",
    "Are there multi-channel cases requiring _0001, _0002 suffixes beyond _0000?",
    "Should the 'name' field exactly match the directory name 'Dataset001_LungLobeRight' or use a cleaned variant?",
    "What indentation/formatting is required for the output JSON?",
    "Are labels stored as binary masks (0/1) or with additional background class already encoded?",
    "Is there a required 'regions' or 'regions_class_order' field for single-class tasks in v2?"
  ]
}
```