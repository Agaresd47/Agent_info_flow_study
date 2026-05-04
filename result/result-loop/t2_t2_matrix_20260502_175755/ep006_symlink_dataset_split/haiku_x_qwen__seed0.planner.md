# Implementation Spec: nnU-Net Dataset Assembly with Symlink-Based Split

## Overview
Assemble a multi-organ medical imaging dataset from pre-processed DRR images and organ-specific masks, split into train/test/validation sets (8:1:1 ratio), and organize via symlinks into nnU-Net directory structure.

---

## Input Contract

### Source Directory Structure
```
<input_root>/
├── CT_no_bed/
│   └── <patient_id>.jpg                    (DRR image)
├── Heart/
│   └── <patient_id>_heart/
│       └── <part>.jpg                      (one or more parts)
├── Lung/
│   └── <patient_id>_total/
│       └── <part>.jpg
├── Rib_clean/
│   └── <patient_id>_total/
│       └── <part>.jpg
├── Spine/
│   └── <patient_id>_total/
│       └── <part>.jpg
├── Bones/
│   └── <patient_id>_total/
│       └── <part>.jpg
└── organ_list.txt                          (organ→part mapping)
```

### organ_list.txt Format
- **Location:** `<input_root>/organ_list.txt`
- **Content:** Defines which parts belong to each organ (exact schema not specified)
- **Usage:** Enables multi-part aggregation per organ per patient

### Patient ID Extraction
- Patient IDs are derived from filenames in `CT_no_bed/` (stem before `.jpg`)
- Organ subdirectories use naming convention: `<patient_id>_<organ_suffix>` or `<patient_id>_total`
- **Open question:** Exact matching rule between `CT_no_bed/<patient_id>.jpg` and organ subdirectory names

---

## Output Contract

### Directory Structure (nnU-Net Style)
```
<output_root>/
├── train/
│   ├── imagesTr/
│   │   └── <case_id>_0000.jpg              (DRR image)
│   └── labelsTr/
│       └── <case_id>.nii.gz                (or other format?)
├── test/
│   ├── imagesTs/
│   │   └── <case_id>_0000.jpg
│   └── labelsTs/
│       └── <case_id>.nii.gz
└── validation/
    ├── imagesVal/
    │   └── <case_id>_0000.jpg
    └── labelsVal/
        └── <case_id>.nii.gz
```

### Case ID Naming
- **Open question:** How to map `<patient_id>` to `<case_id>` (e.g., zero-padded, sequential, or preserved as-is)?

### Label Organization
- **Open question:** How are multi-part masks combined per organ?
  - Stacked channels?
  - Separate files per part?
  - Merged into single segmentation volume?
- **Open question:** Output format for labels (`.nii.gz`, `.npy`, `.jpg`, etc.)?

---

## Split Logic

### Ratio
- Train: 80% (8 parts)
- Test: 10% (1 part)
- Validation: 10% (1 part)

### Randomization
- **Open question:** Is a fixed random seed required for reproducibility?
- **Open question:** Should split be stratified by any attribute (e.g., organ coverage)?

### Patient-Level vs. Sample-Level
- **Assumption:** Split is at patient level (all images/masks for one patient go to same split)
- **Open question:** If a patient has multiple organs, do all organs go to the same split?

---

## Symlink Strategy

### Symlink vs. Copy
- **Constraint:** Use symlinks, not file copies
- **Assumption:** Symlinks point from output structure back to `<input_root>` originals
- **Open question:** Relative or absolute symlink paths?
- **Open question:** Symlink target for multi-part masks (single link per organ, or per part)?

### Write Safety
- **Open question:** If output directories already exist, should the worker:
  - Fail with error?
  - Remove and recreate?
  - Skip existing symlinks?
  - Validate and merge?

---

## Data Validation & Error Handling

### Missing Data
- **Open question:** If a patient has a DRR image but no masks for any organ, should it be:
  - Skipped?
  - Included with empty labels?
  - Treated as error?
- **Open question:** If a patient has masks but no DRR image, should it be skipped or error?

### Organ Coverage
- **Open question:** Must every patient have masks for all organs, or is partial coverage allowed?

### File Integrity
- **Open question:** Should the worker validate that symlink targets exist before creating links?

---

## First Actions for Worker

1. **Enumerate patients:** Scan `<input_root>/CT_no_bed/` to extract all unique `<patient_id>` values.
2. **Load organ mapping:** Parse `<input_root>/organ_list.txt` to understand organ→part relationships.
3. **Validate input coverage:** For each patient, verify presence of DRR image and organ mask directories.
4. **Perform split:** Partition patient list into train/test/validation (8:1:1) using specified randomization method.
5. **Create output structure:** Initialize `<output_root>/{train,test,validation}/{imagesTr,labelsTr,imagesTs,labelsTs,imagesVal,labelsVal}` directories.
6. **Generate symlinks:** For each patient in each split, create symlinks from output structure to input files.
7. **Log completion:** Record which patients went to which split and any skipped/errored cases.

---

## Constraints & Risks

| Constraint | Impact |
|-----------|--------|
| Symlinks only (no copies) | Disk space efficient but requires stable input path; broken links if input moves |
| 8:1:1 split ratio | Must handle rounding for small datasets (e.g., 10 patients → 8/1/1) |
| Multi-part organ masks | Aggregation logic must be deterministic and documented |
| nnU-Net naming convention | Case IDs and channel suffixes (`_0000`) are strict |
| organ_list.txt dependency | Worker cannot proceed without valid mapping file |

### Risks
- **Symlink breakage:** If input root is moved/deleted, all output symlinks become invalid.
- **Incomplete patient data:** Partial organ coverage could create asymmetric datasets.
- **Naming collisions:** If case ID derivation is not unique, symlinks may overwrite.
- **Split reproducibility:** Without fixed seed, splits may differ across runs.

---

```json
{
  "assumptions": [
    "Split is at patient level (all data for one patient goes to same split)",
    "Patient IDs are uniquely extractable from CT_no_bed/ filenames",
    "organ_list.txt exists and is parseable",
    "Symlinks should point from output back to input_root originals",
    "nnU-Net directory structure uses standard naming (imagesTr, labelsTr, imagesTs, labelsTs, imagesVal, labelsVal)",
    "DRR images are the only input images (one per patient, channel 0000)"
  ],
  "risks": [
    "Symlink targets become invalid if input_root is moved or deleted",
    "No specification for handling patients with partial organ coverage",
    "Rounding behavior for 8:1:1 split on non-divisible patient counts is undefined",
    "Multi-part mask aggregation logic not specified (stacking, merging, separate files?)",
    "Output label format not specified (.nii.gz, .npy, .jpg, etc.)",
    "No write-safety policy defined (overwrite, skip, error on existing output?)",
    "Case ID derivation from patient ID not specified (could cause collisions)",
    "Symlink path style (relative vs. absolute) not specified"
  ],
  "open_questions": [
    "What is the exact schema and location of organ_list.txt?",
    "How should multi-part masks per organ be combined into a single label file?",
    "What is the output format for labels (NIfTI, NumPy, JPEG, etc.)?",
    "How should patient IDs be mapped to case IDs for nnU-Net naming?",
    "Should symlinks be relative or absolute paths?",
    "Is a fixed random seed required for reproducible splits?",
    "What should happen if a patient has DRR but no organ masks, or vice versa?",
    "What is the rounding rule for 8:1:1 split when patient count is not divisible by 10?",
    "Should the worker validate symlink targets exist before creating links?",
    "What is the policy if output directories already exist (fail, overwrite, skip, merge)?"
  ]
}
```