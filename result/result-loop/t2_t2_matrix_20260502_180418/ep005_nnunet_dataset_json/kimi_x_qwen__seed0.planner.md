## Spec: nnU-Net v2 dataset.json Generator for Lung Lower Lobe Right Segmentation

### Observed Facts
- Task: Generate nnU-Net v2 `dataset.json` configuration file
- Dataset name: `Dataset001_LungLobeRight`
- Dataset root: `<dataset_root>/Dataset001_LungLobeRight/` (placeholder, actual path not specified)
- Directory structure exists: `imagesTr/`, `labelsTr/`, `imagesTs/`
- Single foreground class: `lung_lower_lobe_right`
- Modality: DRR (Digitally Reconstructed Radiograph, not CT)
- nnU-Net version: v2 (explicitly stated)

### Required Output Schema (nnU-Net v2 dataset.json)

The worker must produce a JSON file conforming to nnU-Net v2 schema. Known required fields:
- `channel_names`: dict mapping channel index to modality name
- `labels`: dict mapping label IDs to class names (including background `0`)
- `numTraining`: integer count of training cases
- `file_ending`: suffix for image files (e.g., `.nii.gz`, `.png`, etc.)
- `overwrite_image_reader_writer`: optional, only if specific reader needed

Additional v2 fields that may be required or optional (verify against v2 docs):
- `regions_class_order`: for region-based training (not applicable here, single class)
- `training`: list of training samples with `image` and `label` paths (relative format TBD)
- `test`: list of test samples (format TBD, may be empty or omitted)

### Case ID Alignment Rules (To Be Determined)

| Aspect | Status | Notes |
|--------|--------|-------|
| Training image/label pairing | **OPEN** | Exact filename pattern unknown |
| Case ID extraction | **OPEN** | Whether IDs are derived from filenames or directory listings |
| Missing label handling | **OPEN** | Behavior if `imagesTr/` entry lacks `labelsTr/` counterpart |
| Extra label handling | **OPEN** | Behavior if `labelsTr/` has entry without matching image |

### Path and Filename Conventions (Critical Uncertainties)

| Item | Status | What Worker Must Know |
|------|--------|----------------------|
| `file_ending` value | **OPEN** | DRR format unspecified (`.nii.gz`? `.png`? `.mha`? `.dcm`?) |
| Image filename pattern | **OPEN** | e.g., `CASEID_0000.nii.gz`? `CASEID_DRR.nii.gz`? |
| Label filename pattern | **OPEN** | Must match case ID; exact suffix unknown |
| Channel index format | **OPEN** | DRR is 2D projection; nnU-Net expects 4D (N,C,H,W,[D]). Single channel = `_0000` suffix? |
| Relative path root | **OPEN** | Whether JSON paths are relative to `Dataset001_LungLobeRight/` or `nnUNet_raw/` |

### Test Set Inclusion

| Question | Status |
|----------|--------|
| Should `imagesTs/` populate `test` field in JSON? | **OPEN** |
| If yes, what metadata required per test case? | **OPEN** |
| Are test labels expected in `labelsTs/` (not mentioned)? | **OPEN** — `labelsTs/` not stated to exist |

### Safety and Idempotency Requirements

| Concern | Requirement |
|---------|-------------|
| Output location | Must write to `<dataset_root>/Dataset001_LungLobeRight/dataset.json` |
| Overwrite policy | **OPEN** — fail if exists? backup? clobber? |
| Validation | Should validate: all referenced images exist, labels exist, no orphaned files |
| Dry-run capability | **OPEN** — should script support preview mode? |

### First Actions for Worker

1. **Resolve open questions** (below) before writing generation logic
2. Verify nnU-Net v2 exact schema against official documentation — do not assume v1 compatibility
3. Implement case ID discovery: list `imagesTr/`, extract case IDs, verify `labelsTr/` counterparts
4. Construct `channel_names` as `{"0": "DRR"}` (single channel DRR)
5. Construct `labels` as `{"0": "background", "1": "lung_lower_lobe_right"}`
6. Write JSON with proper relative path formatting per v2 convention

---

```json
{
  "assumptions": [
    "nnU-Net v2 schema differs from v1; worker must consult v2 documentation not v1 defaults",
    "DRR as modality implies single-channel 2D data, but nnU-Net v2's expected file suffix and channel indexing (_0000 convention) still apply",
    "Dataset directory structure is already valid and populated; script only generates JSON metadata",
    "Single foreground class means binary segmentation (label values 0 and 1)",
    "Case IDs are extractable from filenames via consistent pattern"
  ],
  "risks": [
    "Wrong file_ending (e.g., .png vs .nii.gz) will cause nnU-Net preprocessing to fail silently or with cryptic errors",
    "Incorrect channel index suffix (_0000, _0001, etc.) will cause nnU-Net to misidentify modalities or fail",
    "Mismatched image/label case IDs will result in training samples with missing labels or vice versa",
    "Including test set in JSON when labelsTs/ doesn't exist may cause nnU-Net to expect labels that aren't there",
    "Overwriting existing dataset.json without backup could destroy manual corrections or previous valid config",
    "Relative path format in JSON must match nnU-Net v2's exact expectation (./imagesTr/CASEID_0000.nii.gz vs imagesTr/CASEID_0000.nii.gz vs CASEID_0000.nii.gz)"
  ],
  "open_questions": [
    "What is the actual value of <dataset_root> absolute path?",
    "What is the exact file extension of DRR images? (.nii.gz, .png, .mha, .dcm, etc.)",
    "What is the exact filename pattern for training images? (e.g., CASEID_0000.nii.gz, CASEID_DRR.nii.gz, CASEID.nii.gz)",
    "What is the exact filename pattern for training labels? (must match case ID; suffix may differ)",
    "Does nnU-Net v2 require 'training' and 'test' lists in dataset.json, or only counts and file_ending?",
    "Should imagesTs/ be included in the JSON 'test' field, and if so, with what path format?",
    "Does labelsTs/ exist? If not, should test set be listed in JSON at all?",
    "What is nnU-Net v2's exact expected path format in dataset.json entries? (relative to dataset folder, nnUNet_raw, or basename only?)",
    "What is the overwrite policy if dataset.json already exists? (fail, backup, clobber, prompt?)",
    "Should the script validate that every imagesTr/ entry has a corresponding labelsTr/ entry, and what action if mismatch found? (skip, warn, error?)",
    "Are there any DRR-specific reader/writer requirements that need 'overwrite_image_reader_writer' field?"
  ]
}
```