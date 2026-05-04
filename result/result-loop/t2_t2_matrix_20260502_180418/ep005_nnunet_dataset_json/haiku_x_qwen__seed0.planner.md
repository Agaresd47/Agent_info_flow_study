# Implementation Spec: nnU-Net v2 dataset.json Generator for Lung Lower Lobe Right Segmentation

## Overview
Generate a `dataset.json` file for nnU-Net v2 that describes a single-class lung lower lobe right segmentation task using DRR (Digital Reconstructed Radiograph) modality. The dataset follows nnU-Net v2 directory structure with training images/labels and test images already organized.

## Observed Facts
- Dataset root: `<dataset_root>/Dataset001_LungLobeRight/`
- Subdirectories present: `imagesTr/`, `labelsTr/`, `imagesTs/`
- Single foreground class: `lung_lower_lobe_right`
- Modality: DRR (not CT)
- Format: nnU-Net v2
- Request language: Chinese; output should be implementable in any language

## Constraints & Requirements

### 1. **Case ID Alignment Rule**
- Training images and labels must be paired by case identifier
- **Constraint**: Worker must establish and document the exact matching rule (e.g., `case_001_0000.nii.gz` ↔ `case_001.nii.gz`)
- **Constraint**: All cases in `labelsTr/` must have corresponding entries in `imagesTr/`; mismatches must be detected and reported

### 2. **File Suffix Handling**
- **Open Question**: What file extensions are present? (`.nii.gz`, `.nii`, `.mha`, `.dcm`?)
- **Constraint**: Worker must scan actual directory to determine suffix(es) and validate consistency
- **Constraint**: nnU-Net v2 expects specific suffix conventions; worker must not assume or normalize extensions without validation

### 3. **Test Set Inclusion in JSON**
- **Open Question**: Does nnU-Net v2 `dataset.json` include `imagesTs/` entries, or only training data?
- **Constraint**: If test set is included, clarify whether labels are expected (likely not for held-out test)
- **Constraint**: If test set is excluded from JSON, document this decision

### 4. **Path Representation in JSON**
- **Open Question**: Should paths in `dataset.json` be absolute, relative to dataset root, or relative to the JSON file location?
- **Constraint**: Worker must verify nnU-Net v2 parser expectations before writing paths
- **Constraint**: Paths must be consistent across all entries

### 5. **Schema Fields for nnU-Net v2**
- **Open Question**: Exact required and optional fields in `dataset.json` for v2 (e.g., `name`, `description`, `reference`, `license`, `release`, `tensorImageSize`, `modality`, `labels`, `numTraining`, `numTest`, `training`, `test`)
- **Constraint**: Worker must not invent fields; reference official nnU-Net v2 documentation or schema
- **Constraint**: Modality field must correctly represent DRR (not CT, MRI, etc.)

### 6. **Label Encoding**
- **Constraint**: Single foreground class `lung_lower_lobe_right` must map to label integer (typically `1`)
- **Constraint**: Background must be label `0`
- **Open Question**: Should the JSON include label metadata (name, color, etc.) and in what format?

### 7. **Write Safety**
- **Constraint**: If `dataset.json` already exists, define overwrite policy (fail, backup, replace)
- **Constraint**: Validate JSON syntax before writing to disk
- **Constraint**: Document any file permissions or directory creation needed

## First Actions for Worker

1. **Scan the actual directory structure** to determine:
   - Exact file extensions in `imagesTr/`, `labelsTr/`, `imagesTs/`
   - Number of training cases
   - Case naming pattern and how to extract case IDs
   - Whether all training labels have matching images

2. **Verify nnU-Net v2 schema** by:
   - Consulting official nnU-Net v2 documentation or reference `dataset.json` examples
   - Confirming required vs. optional fields
   - Confirming path format expectations

3. **Define the case matching algorithm**:
   - Extract case IDs from filenames
   - Validate 1:1 correspondence between `imagesTr/` and `labelsTr/`
   - Report any orphaned or mismatched files

4. **Generate the JSON structure** with:
   - Metadata (name, description, reference, license, release)
   - Modality: `["DRR"]`
   - Labels: `{"0": "background", "1": "lung_lower_lobe_right"}`
   - Training entries with image and label paths
   - Test entries (if applicable per schema)

5. **Validate and write** with error handling for malformed paths or missing files

---

```json
{
  "assumptions": [
    "Dataset root directory is accessible and contains exactly the three subdirectories mentioned (imagesTr, labelsTr, imagesTs)",
    "All training cases have both image and label files with matching case identifiers",
    "File extensions are consistent within each subdirectory",
    "Single foreground class maps to integer label 1; background is 0",
    "nnU-Net v2 is the target framework and its schema is authoritative"
  ],
  "risks": [
    "Mismatched case IDs between imagesTr and labelsTr will cause training failures; must validate before JSON generation",
    "Incorrect path format (absolute vs. relative) will cause nnU-Net v2 parser to fail; must verify schema expectations",
    "Unknown file extensions or mixed suffixes will break nnU-Net v2 preprocessing; must detect and report",
    "Overwriting existing dataset.json without backup could lose prior configuration; must define write policy",
    "DRR modality may require special preprocessing in nnU-Net v2; confirm modality string is recognized",
    "Test set handling is unclear; including or excluding imagesTs incorrectly will cause schema validation errors"
  ],
  "open_questions": [
    "What are the exact file extensions in imagesTr/, labelsTr/, and imagesTs/? (e.g., .nii.gz, .nii, .mha)",
    "What is the exact case ID extraction rule from filenames? (e.g., does 'case_001_0000.nii.gz' map to case ID 'case_001'?)",
    "Does nnU-Net v2 dataset.json include test set entries (imagesTs), or only training data?",
    "Should paths in dataset.json be absolute, relative to dataset root, or relative to the JSON file?",
    "What is the complete required schema for nnU-Net v2 dataset.json? (list all mandatory and optional fields)",
    "How should the DRR modality be represented in the modality field? (e.g., 'DRR', 'X-ray', or a specific nnU-Net v2 code)",
    "Should label metadata (e.g., color, display name) be included in the labels section, and in what format?",
    "If dataset.json already exists, should the worker overwrite, backup, or fail?",
    "Are there any nnU-Net v2-specific validation rules or constraints for single-class segmentation tasks?"
  ]
}
```