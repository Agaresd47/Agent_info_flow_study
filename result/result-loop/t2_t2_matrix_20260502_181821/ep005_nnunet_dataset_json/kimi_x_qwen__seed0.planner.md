## Implementation Spec: nnU-Net v2 dataset.json Generator for Lung Lower Lobe Right Segmentation

### Observed Facts
- **Task**: Single-class semantic segmentation (lung_lower_lobe_right)
- **nnU-Net version**: v2 (explicitly stated)
- **Dataset directory**: `<dataset_root>/Dataset001_LungLobeRight/`
- **Subdirectories present**: `imagesTr/`, `labelsTr/`, `imagesTs/`
- **Modality**: DRR (Digital Radiograph/Reconstructed Radiograph — explicitly **not CT**)
- **Output required**: `dataset.json` file

---

### Required Schema Fields (nnU-Net v2)

The worker must populate these mandatory fields per nnU-Net v2 specification:

| Field | Type | Description | Status |
|-------|------|-------------|--------|
| `name` | string | Dataset name | Derive from directory: `Dataset001_LungLobeRight` or `LungLobeRight`? |
| `description` | string | Human-readable description | Required, content unspecified |
| `reference` | string | Data source reference | Required, content unspecified |
| `licence` | string | License string | Required, content unspecified |
| `release` | string | Version/release date | Required, format unspecified |
| `tensorImageSize` | string | Spatial dimensions | `"2D"` or `"3D"`? **OPEN** — DRR is typically 2D projection |
| `modality` | object | `{case_id: modality_str}` | Must map all training cases to `"DRR"` |
| `labels` | object | `{label_id: label_name}` | Must include `"0": "background"`, `"1": "lung_lower_lobe_right"` |
| `numTraining` | int | Count of training cases | Derive from `imagesTr/` |
| `numTest` | int | Count of test cases | Derive from `imagesTs/` |
| `training` | list | List of `{"image": "...", "label": "..."}` | Paths relative to dataset root |
| `test` | list | List of `{"image": "..."}` | Paths relative to dataset root; **inclusion policy unclear** |

---

### Case ID Alignment Rules

**Training set alignment** (`imagesTr/` ↔ `labelsTr/`):
- Case ID is the filename **without modality suffix and without extension**
- nnU-Net v2 naming convention: `CASEID_0000.nii.gz` for images, `CASEID.nii.gz` for labels
- The `0000` suffix indicates modality channel 0 (single-modality DRR)
- **Alignment rule**: For each `CASEID_0000.nii.gz` in `imagesTr/`, expect `CASEID.nii.gz` in `labelsTr/`
- **Mismatch handling**: Unmatched cases → error, warning, or skip? **OPEN**

**Test set handling**:
- `imagesTs/` exists but no `labelsTs/` mentioned
- **Question**: Include test images in `dataset.json["test"]` array or omit entirely? **OPEN**
- nnU-Net v2 typically includes test images for inference; labels are omitted

---

### Path Conventions in JSON

| Element | Convention | Example |
|---------|-----------|---------|
| Image paths | `./imagesTr/CASEID_0000.nii.gz` | Relative to dataset root |
| Label paths | `./labelsTr/CASEID.nii.gz` | Relative to dataset root |
| Test image paths | `./imagesTs/CASEID_0000.nii.gz` | If included |

**Critical**: Paths must use forward slashes, include leading `./`, and preserve the `0000` channel suffix for images.

---

### File Extension Handling

- **Assumed extension**: `.nii.gz` (standard nnU-Net)
- **Verification required**: Confirm all files in `imagesTr/`, `labelsTr/`, `imagesTs/` share this extension
- **Action if mixed extensions**: Fail, or filter to `.nii.gz` only? **OPEN**

---

### DRR Modality Specifics

- DRR is **not** a standard nnU-Net modality code (unlike `"CT"`, `"MRI"`)
- nnU-Net v2 uses modality as string identifier; `"DRR"` is acceptable as custom string
- **Implication**: No intensity normalization preset exists for DRR; nnU-Net will use default z-score normalization
- **Tensor image size**: DRRs are 2D images. If dataset contains 2D DRRs, `tensorImageSize` should be `"2D"` — but confirm actual dimensionality. **OPEN**

---

### Write Safety & Idempotency

| Concern | Status | Required Action |
|---------|--------|---------------|
| Output path | `Dataset001_LungLobeRight/dataset.json` | Fixed relative to dataset root |
| Overwrite existing | **Unspecified** | **OPEN** — fail if exists, or clobber? |
| Partial write | Risk | Write to temp file, atomic rename |
| Validation | Required | Verify JSON is parseable and schema-compliant |

---

### First Actions for Worker

1. **Enumerate** `imagesTr/` → extract case IDs (strip `_0000.nii.gz`)
2. **Verify** each case ID exists in `labelsTr/` with `.nii.gz` extension
3. **Enumerate** `imagesTs/` → decide inclusion policy per open question
4. **Determine** `tensorImageSize` by loading one image and checking dimensions
5. **Collect** metadata strings (`description`, `reference`, `licence`, `release`) — these are **missing** and must be requested or defaulted with warning
6. **Write** JSON with atomic file operation
7. **Validate** output against nnU-Net v2 expected schema (no missing required fields)

---

```json
{
  "assumptions": [
    "File extension is .nii.gz for all images and labels",
    "Single-modality DRR uses channel suffix _0000 in image filenames",
    "Case ID alignment follows nnU-Net v2 convention: imagesTr/CASEID_0000.nii.gz pairs with labelsTr/CASEID.nii.gz",
    "DRR as modality string is accepted by nnU-Net v2 without preset normalization",
    "Dataset root path will be provided as argument or inferred from script location",
    "tensorImageSize is '2D' for DRR projections (to be verified by image inspection)"
  ],
  "risks": [
    "Mismatch between imagesTr and labelsTr case IDs causes incomplete or invalid dataset.json",
    "Missing required metadata fields (description, reference, licence, release) will produce invalid nnU-Net dataset",
    "Overwrite of existing dataset.json may destroy manual edits or prior configuration",
    "Incorrect tensorImageSize (2D vs 3D) will cause nnU-Net preprocessing failures",
    "Test set inclusion/exclusion policy affects downstream inference pipeline behavior",
    "Non-.nii.gz files in directories will break filename parsing assumptions"
  ],
  "open_questions": [
    "What is the overwrite policy if dataset.json already exists?",
    "Should test images from imagesTs/ be included in the 'test' array or omitted entirely?",
    "What are the exact values for description, reference, licence, and release metadata fields?",
    "Is the dataset strictly 2D DRRs, or are there 3D volumes (affecting tensorImageSize)?",
    "How should mismatched cases (image without label, or label without image) be handled: error, warning, or silent skip?",
    "Are there any non-.nii.gz files in the directories that should be ignored?",
    "Is the dataset root path provided as absolute path, relative path, or must be discovered?",
    "Should the script validate the generated JSON against nnU-Net v2's internal validator before completing?"
  ]
}
```