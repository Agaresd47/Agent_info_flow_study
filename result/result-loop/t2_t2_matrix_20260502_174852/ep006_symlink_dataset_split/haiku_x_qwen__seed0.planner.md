# Implementation Spec: nnU-Net Dataset Assembly with Symlink-Based Split

## Observed Facts

1. **Input Structure**: Source data organized by organ type, with patient-level and part-level granularity
   - DRR images: `CT_no_bed/<patient_id>.jpg`
   - Organ masks: `{Heart,Lung,Rib_clean,Spine,Bones}/<patient_id>_<suffix>/<part>.jpg`
   - Organ-part mapping defined in `organ_list.txt`

2. **Output Structure**: nnU-Net-style directory tree with train/test/validation splits
   - Split ratio: 8:1:1 (80% train, 10% test, 10% validation)
   - Output uses symlinks (not copies)

3. **Multi-part Organs**: Each organ can have multiple part files that must be grouped together per patient

4. **File Format**: Input images are `.jpg`; output structure implied but not specified

## Constraints & Risks

### Critical Constraints
- **Symlink Safety**: Symlinks must point to absolute or correctly-relative paths; broken links will silently fail in downstream nnU-Net processing
- **Patient ID Extraction**: Parsing `<patient_id>` from filenames must handle potential naming inconsistencies (e.g., `patient_001` vs `001`)
- **Part Aggregation**: Multiple part files per organ per patient must be linked individually, not merged
- **Deterministic Split**: Train/test/validation assignment must be reproducible (seed-based or sorted order)
- **No Overwrites**: Symlink creation must fail safely if target already exists

### Irreversible Actions
- Creating symlinks in output directory: if source paths are wrong, links will be broken and hard to debug
- Deleting or moving input files during processing: not mentioned but must be avoided

## Assumptions

1. `organ_list.txt` format: one organ per line, or structured as `organ: [part1, part2, ...]`
2. Patient IDs are unique and consistently formatted across all organ directories
3. All patients have entries in all organ directories (no sparse data)
4. Output directory structure (`train/`, `test/`, `validation/`) does not exist or is safe to populate
5. nnU-Net expects a specific subdirectory layout (e.g., `imagesTr/`, `labelsTr/`) — **not specified in request**
6. Symlinks are supported on the target filesystem

## Missing Information (Open Questions)

1. **`organ_list.txt` Format**: Exact schema for organ-to-part mapping
   - Is it a flat list of organs, or does it include part names?
   - Example line needed

2. **nnU-Net Output Schema**: What is the expected directory structure under `train/`, `test/`, `validation/`?
   - Should DRR images and masks be in separate subdirectories (e.g., `imagesTr/`, `labelsTr/`)?
   - Should each patient be a subdirectory, or are files named with patient ID?
   - How should multi-part masks be organized (separate files, concatenated, or one per part)?

3. **Patient ID Parsing**: 
   - Is `<patient_id>` always the prefix before the first underscore or file extension?
   - Are there edge cases (e.g., patient IDs containing underscores)?

4. **Split Determinism**:
   - Should the split be deterministic based on sorted patient IDs, or use a random seed?
   - If seed-based, what seed value?

5. **Symlink Targets**:
   - Should symlinks point to absolute paths or relative paths (e.g., `../../input_root/...`)?
   - What if input and output are on different filesystems?

6. **Error Handling**:
   - If a patient is missing from one organ directory, should the script skip that patient or fail?
   - If `organ_list.txt` references an organ not present in input, what should happen?

---

```json
{
  "assumptions": [
    "organ_list.txt contains a parseable mapping of organs to their part files",
    "Patient IDs are consistently formatted and uniquely identify individuals across all organ directories",
    "All patients have complete entries in all organ directories",
    "nnU-Net expects a standard directory layout (not specified; worker must clarify)",
    "Symlinks are supported on the target filesystem",
    "Split ratio 8:1:1 should be deterministic (sorted patient list or fixed seed)"
  ],
  "risks": [
    "Broken symlinks if source paths are incorrectly resolved or input files move after linking",
    "Silent failures in downstream nnU-Net if output directory structure does not match expected schema",
    "Patient ID parsing errors if naming conventions are inconsistent or contain edge cases",
    "Data loss if output directory is not validated before symlink creation",
    "Incomplete splits if some patients are missing from certain organ directories"
  ],
  "open_questions": [
    "What is the exact format and schema of organ_list.txt?",
    "What is the expected nnU-Net output directory structure (imagesTr/, labelsTr/, etc.)?",
    "How should multi-part masks per organ per patient be organized in the output?",
    "Should symlinks use absolute or relative paths, and how should cross-filesystem cases be handled?",
    "What is the deterministic seed or ordering for the 8:1:1 split?",
    "How should the script handle missing patients or organs (skip, fail, or warn)?"
  ]
}
```