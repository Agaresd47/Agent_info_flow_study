## Spec: nnU-Net v2 dataset.json Generator for Lung Lower Lobe Right Segmentation

### Observed Facts
- **Task**: Single-class semantic segmentation (lung_lower_lobe_right)
- **nnU-Net version**: v2 (explicitly stated)
- **Dataset directory**: `<dataset_root>/Dataset001_LungLobeRight/`
- **Subdirectories present**: `imagesTr/`, `labelsTr/`, `imagesTs/`
- **Modality**: DRR (Digital Reconstructed Radiograph) — not CT
- **Naming convention**: Not specified; must be inferred or confirmed

---

### Required Output Schema (nnU-Net v2 dataset.json)

The worker must produce a JSON file with these fields per nnU-Net v2 specification:

| Field | Type | Description | Status |
|-------|------|-------------|--------|
| `name` | string | Dataset name | Derive from directory: `"Dataset001_LungLobeRight"` |
| `description` | string | Human-readable description | Required; content unspecified |
| `reference` | string | Citation or source | Required; content unspecified |
| `licence` | string | License string | Required; content unspecified |
| `release` | string | Version or date | Required; content unspecified |
| `tensorImageSize` | string | Spatial dimensions | `"2D"` or `"3D"` — **OPEN** (DRR is 2D projection, but nnU-Net expects volumetric; confirm) |
| `modality` | dict | `{ "0": "DRR" }` | Fixed per request |
| `labels` | dict | `{ "background": 0, "lung_lower_lobe_right": 1 }` | Fixed per request |
| `numTraining` | int | Count of training cases | Derive from `imagesTr/` |
| `numTest` | int | Count of test cases | Derive from `imagesTs/` |
| `training` | list | List of `{ "image": "./imagesTr/...", "label": "./labelsTr/..." }` | **Path format critical** — see below |
| `test` | list | List of `{ "image": "./imagesTs/..." }` | Empty list `[]` if no test images, or populated — see open questions |

---

### Critical Path and Naming Conventions

#### Case ID Alignment Rule
- Training case pairing: For each case ID `XXX`, `imagesTr/XXX_0000.nii.gz` must pair with `labelsTr/XXX.nii.gz`
- The `_0000` suffix is **modality channel index** (single modality → always `_0000`)
- Label files **omit the channel suffix**

#### File Extension Handling
- **OPEN**: Confirm expected extension (`.nii.gz` vs `.nii` vs `.mha` vs `.png` for DRR)
- nnU-Net v2 strongly prefers `.nii.gz` for 3D; DRR as 2D may use `.png` or `.nii.gz`

#### Path Format in JSON
- nnU-Net v2 requires **relative paths starting with `./`**
- Format: `"./imagesTr/case_001_0000.nii.gz"` (not absolute paths, no leading `Dataset001_LungLobeRight/`)

#### Test Set Inclusion
- `imagesTs/` exists → must decide if test cases appear in `test` field
- **OPEN**: Does user want test images listed in `test` field, or left empty for later inference?

---

### First Actions for Worker

1. **Enumerate directory contents**: List `imagesTr/`, `labelsTr/`, `imagesTs/` to discover actual filenames and extensions
2. **Validate pairing**: Verify every `imagesTr/*_0000.*` has matching `labelsTr/*.*` (same case ID)
3. **Detect orphans**: Unpaired images or labels → error or warning policy needed
4. **Confirm extension**: Use observed extension consistently; error if mixed
5. **Write to**: `<dataset_root>/Dataset001_LungLobeRight/dataset.json`

---

### Safety Constraints

| Constraint | Enforcement |
|------------|-------------|
| **No destructive writes** | If `dataset.json` exists, halt or require explicit overwrite flag — **policy unspecified** |
| **Atomic write** | Write to temp file, then rename |
| **Validation** | After write, attempt `json.load()` and verify required fields present |
| **Case sensitivity** | Assume case-sensitive filesystem; preserve exact case from filenames |

---

### Missing Information (Open Questions)

```json
{
  "assumptions": [
    "Dataset directory name 'Dataset001_LungLobeRight' should be used as the 'name' field in dataset.json",
    "Single modality (DRR) maps to channel index 0, hence training images use suffix '_0000'",
    "Label files omit the channel suffix entirely (e.g., 'case_001.nii.gz' not 'case_001_0000.nii.gz')",
    "Relative paths in JSON must start with './' and use forward slashes",
    "DRR as 2D projection may require 'tensorImageSize': '2D' but nnU-Net v2 typically expects volumetric data"
  ],
  "risks": [
    "If file extension is not .nii.gz, nnU-Net v2 may fail to load images",
    "If test set images are listed in 'test' field but lack labels, downstream training scripts may behave unexpectedly",
    "Existing dataset.json overwrite could destroy manual edits or previous metadata",
    "Case ID mismatch between imagesTr and labelsTr (e.g., extra underscore, different naming) will break training",
    "DRR modality may not be recognized by nnU-Net v2's default intensity normalization; may require custom preprocessing"
  ],
  "open_questions": [
    "What is the exact file extension for images and labels? (.nii.gz, .nii, .mha, .png, .jpg?)",
    "Should 'tensorImageSize' be '2D' or '3D'? DRR is 2D projection but nnU-Net v2 is designed for 3D volumetric segmentation",
    "Should test images from imagesTs/ be populated in the 'test' field of dataset.json, or left as empty list []?",
    "What are the required values for 'description', 'reference', 'licence', and 'release' fields?",
    "What is the overwrite policy if dataset.json already exists?",
    "Should the script validate that label files contain only values {0, 1} for single-class segmentation?",
    "Are there any case naming conventions beyond 'case_id_0000.ext' / 'case_id.ext'? (e.g., numeric padding, prefixes)",
    "Does nnU-Net v2 support DRR natively, or does it require conversion to pseudo-3D (e.g., single-slice volume)?"
  ]
}
```