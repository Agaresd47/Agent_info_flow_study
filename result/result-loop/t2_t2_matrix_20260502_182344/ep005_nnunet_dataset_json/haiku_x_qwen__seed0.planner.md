# Planner v2: Corrections & Clarifications for nnU-Net v2 dataset.json Worker

## What Worker v1 Got Right

Worker v1 correctly identified:
- The need to scan actual directories before making assumptions
- The importance of case ID matching validation
- That path format, schema fields, and test set inclusion are unknowns that must be verified
- The risk of file extension inconsistency
- The need to validate JSON syntax before writing

## Critical Corrections & Gaps

### 1. **Case ID Matching: Clarify the Extraction Rule**
Worker v1 stated "extract case IDs from filenames" but did not specify *how*. The original request does not provide example filenames. 

**Correction**: Before writing any matching logic, the worker must:
- List 3–5 actual filenames from `imagesTr/` and `labelsTr/`
- Determine whether the naming follows nnU-Net v2 convention (e.g., `case_001_0000.nii.gz` for images, `case_001.nii.gz` for labels)
- Document the exact extraction rule (e.g., "strip `_0000` suffix and file extension to get case ID")
- **Do not assume** nnU-Net v2 uses the `_0000` suffix; verify from actual files

### 2. **nnU-Net v2 Schema: Consult Authoritative Source**
Worker v1 listed open questions about schema but did not specify *where* to find the answer.

**Correction**: The worker must:
- Check the official nnU-Net v2 repository (GitHub: `MIC-DKFZ/nnUNet`) for `dataset.json` schema documentation or examples
- Look for a reference `dataset.json` in the repo's test datasets or documentation
- If documentation is unavailable, inspect the nnU-Net v2 source code (e.g., `nnunetv2/dataset_conversion/generate_dataset_json.py`) to reverse-engineer the schema
- **Do not guess** field names or structure; cite the source

### 3. **Path Format: Verify Against nnU-Net v2 Parser**
Worker v1 correctly flagged this as unknown but did not specify how to verify.

**Correction**: The worker must:
- Check nnU-Net v2 documentation for whether paths should be relative or absolute
- If unclear, inspect the nnU-Net v2 data loading code to see how it resolves paths from `dataset.json`
- **Most likely**: paths are relative to the dataset root (e.g., `imagesTr/case_001_0000.nii.gz`), but this must be confirmed, not assumed
- Document the chosen format and the rationale

### 4. **Test Set Inclusion: Check nnU-Net v2 Behavior**
Worker v1 asked whether `imagesTs/` should be in the JSON but did not specify how to find the answer.

**Correction**: The worker must:
- Check official nnU-Net v2 examples or documentation for whether `test` or `imagesTs` entries appear in `dataset.json`
- If the schema includes a `test` field, determine whether it lists image paths only (no labels expected) or is omitted entirely
- **Most likely**: nnU-Net v2 includes a `test` field with image paths but no labels, but this must be verified
- If test set is excluded, document why and confirm this matches nnU-Net v2 expectations

### 5. **DRR Modality Representation: Verify Exact String**
Worker v1 noted that DRR modality must be "correctly represented" but did not specify what string to use.

**Correction**: The worker must:
- Check nnU-Net v2 documentation or examples for the exact modality string for DRR (e.g., is it `"DRR"`, `"X-ray"`, `"radiograph"`, or a numeric code?)
- If nnU-Net v2 does not have a predefined DRR modality, determine whether a custom string is acceptable or if a closest match (e.g., `"CT"` or `"X-ray"`) should be used
- **Do not invent** a modality string; use what nnU-Net v2 recognizes or explicitly document a custom choice

### 6. **File Extension Consistency: Scan and Report**
Worker v1 correctly identified the need to scan but did not specify the validation rule.

**Correction**: The worker must:
- List all unique file extensions found in `imagesTr/`, `labelsTr/`, and `imagesTs/`
- Verify that all files within each subdirectory use the *same* extension (e.g., all `.nii.gz`, not a mix)
- If extensions differ between subdirectories (e.g., images are `.nii.gz` but labels are `.nii`), document this and determine if nnU-Net v2 can handle it
- **Report any inconsistency** as a potential error before proceeding

### 7. **Overwrite Policy: Define Explicitly**
Worker v1 mentioned defining a policy but did not specify what it should be.

**Correction**: The worker must:
- Define one of: (a) fail if `dataset.json` exists, (b) create a timestamped backup before overwriting, or (c) always overwrite
- **Recommended**: create a backup (e.g., `dataset.json.backup.<timestamp>`) before overwriting to preserve prior configuration
- Document the chosen policy in the generated JSON or in a log file

### 8. **Label Metadata: Check nnU-Net v2 Schema**
Worker v1 asked whether to include label metadata but did not specify the format.

**Correction**: The worker must:
- Check nnU-Net v2 examples to see whether the `labels` field is a simple dict (`{"0": "background", "1": "lung_lower_lobe_right"}`) or a nested structure with color, display name, etc.
- **Most likely**: nnU-Net v2 uses a simple dict, but this must be verified
- If metadata is supported, determine the exact field names and data types (e.g., is color a hex string, RGB tuple, or not supported?)

---

## Worker Next Focus (Priority Order)

1. **Obtain actual filenames** from the dataset directory (3–5 examples from each of `imagesTr/` and `labelsTr/`)
2. **Consult nnU-Net v2 official source** (GitHub repo, documentation, or reference `dataset.json` examples) to determine:
   - Complete schema (required and optional fields)
   - Path format expectations
   - Modality string for DRR
   - Whether test set is included
   - Label metadata format
3. **Scan the directory** to confirm file extensions and case ID matching rule
4. **Validate 1:1 correspondence** between training images and labels
5. **Define and document** the overwrite policy
6. **Generate the JSON** only after all unknowns are resolved

---

```json
{
  "corrected_constraints": [
    "Case ID extraction rule must be deduced from actual filenames in the dataset, not assumed; document the exact rule (e.g., 'remove _0000 suffix and extension').",
    "nnU-Net v2 schema must be verified from official documentation, GitHub repository, or reference examples; do not invent fields.",
    "Path format (absolute vs. relative) must be confirmed by checking nnU-Net v2 data loading code or documentation; most likely relative to dataset root, but must be verified.",
    "Test set inclusion in dataset.json must be confirmed from nnU-Net v2 schema; if included, clarify whether labels are expected (likely not).",
    "DRR modality string must match nnU-Net v2's recognized modality list; if not predefined, document the custom choice and rationale.",
    "File extensions must be consistent within each subdirectory (imagesTr, labelsTr, imagesTs); report any inconsistency as a potential error.",
    "Overwrite policy for existing dataset.json must be explicitly defined (fail, backup, or replace); recommended: create timestamped backup.",
    "Label metadata format must match nnU-Net v2 schema (likely simple dict, but must be verified); do not add unsupported fields.",
    "All training labels must have corresponding training images; validate 1:1 correspondence and report orphaned or mismatched files before generating JSON."
  ],
  "still_missing": [
    "Actual filenames from imagesTr/ and labelsTr/ directories (needed to deduce case ID extraction rule).",
    "Official nnU-Net v2 dataset.json schema documentation or reference examples (needed to confirm required/optional fields, path format, test set inclusion, modality strings, label metadata format).",
    "Confirmation of whether nnU-Net v2 recognizes 'DRR' as a modality or requires a different string (e.g., 'X-ray', 'radiograph', or numeric code).",
    "Exact file extensions used in each subdirectory (imagesTr/, labelsTr/, imagesTs/).",
    "Confirmation of whether test set entries (imagesTs) should be included in dataset.json and if so, whether labels are expected.",
    "Decision on overwrite policy for existing dataset.json (fail, backup, or replace).",
    "Confirmation of whether label metadata (color, display name, etc.) is supported in nnU-Net v2 and in what format."
  ],
  "worker_next_focus": [
    "Retrieve 3–5 actual filenames from imagesTr/ and labelsTr/ to determine the case ID extraction rule.",
    "Consult nnU-Net v2 GitHub repository (MIC-DKFZ/nnUNet) for official dataset.json schema, examples, or documentation.",
    "If documentation is sparse, inspect nnU-Net v2 source code (e.g., nnunetv2/dataset_conversion/generate_dataset_json.py) to reverse-engineer