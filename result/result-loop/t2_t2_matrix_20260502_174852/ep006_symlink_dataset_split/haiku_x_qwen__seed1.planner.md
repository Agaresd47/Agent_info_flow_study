# Implementation Spec: nnU-Net Dataset Assembly with Symlink-Based Organ-Part Mapping

## Observed Facts

- **Input structure**: Flat directory tree with organ folders containing patient-specific subdirectories and part files (`.jpg` format)
- **Output requirement**: Split dataset into `train/test/validation` subdirectories following 8:1:1 ratio
- **Linking strategy**: Use symbolic links (not copies) to assemble output structure
- **Multi-part organs**: Each organ has multiple parts; mapping defined in `organ_list.txt`
- **Language context**: Request in Chinese; file naming uses underscores and patient IDs as identifiers

## Constraints (Non-Negotiable)

1. **Symlink-only output**: No file copying; all output references must be symbolic links to source files
2. **Split ratio**: Exactly 8:1:1 (train:test:validation) — clarify rounding behavior for non-divisible patient counts
3. **Part-level granularity**: Individual part files (not whole organs) are the atomic unit being linked
4. **Source immutability**: Input directory must not be modified
5. **Deterministic splitting**: Seed or patient ID ordering must be reproducible across runs

## Assumptions

- `organ_list.txt` exists at `<input_root>/organ_list.txt` and defines the complete organ→part mapping
- Format of `organ_list.txt` is line-delimited or JSON; exact schema not specified
- Patient IDs are extractable from filenames (e.g., `<patient_id>` in `<patient_id>.jpg` and `<patient_id>_<organ>/<part>.jpg`)
- All patients have entries in all organ folders (no missing organs per patient)
- Output directory structure should mirror nnU-Net convention (e.g., `imagesTr/`, `imagesTs/`, `imagesVal/` or similar); exact naming not provided
- Symlinks are relative or absolute; preference not stated

## Risks & Irreversible Actions

1. **Symlink target validity**: If source files are moved/deleted after symlink creation, links break silently
   - *Mitigation*: Document that input directory must remain stable; consider absolute symlinks
2. **Patient ID collision**: If multiple patients share the same ID across organs, split logic may produce incorrect groupings
   - *Mitigation*: Validate patient ID uniqueness before splitting
3. **Incomplete part files**: If a patient lacks expected parts in `organ_list.txt`, symlink creation will fail
   - *Mitigation*: Define error handling (skip patient, warn, or fail-fast)
4. **Output directory conflicts**: If `<output_root>` already exists with conflicting structure, symlinks may overwrite or fail
   - *Mitigation*: Require explicit `--force` flag or backup strategy
5. **Split reproducibility**: Random seed for train/test/validation assignment must be logged or deterministic
   - *Mitigation*: Use fixed seed or patient ID hash for reproducibility

## Missing Information (Blocking Questions)

1. **`organ_list.txt` format**: Is it CSV, JSON, plain text? What is the exact schema (organ name → list of part names)?
2. **nnU-Net output directory naming**: Should output follow `imagesTr/`, `imagesTs/`, `imagesVal/` or `train/test/validation`? Should there be a `labels/` parallel structure?
3. **Filename transformation**: Should output symlinks preserve source filenames, or should they be renamed to nnU-Net convention (e.g., `<patient_id>_<organ>_<part>_0000.nii.gz`)?
4. **Patient ID extraction logic**: Is the patient ID always the first token before `_` or `.`? Are there edge cases (e.g., multi-part patient IDs)?
5. **Rounding behavior**: For 8:1:1 split on N patients, how should remainders be handled? (e.g., 10 patients → 8/1/1 or 7/2/1?)
6. **Symlink type**: Relative or absolute paths? Should symlinks be validated after creation?
7. **Error handling**: Should the script fail on first error, log warnings and continue, or provide a dry-run mode?
8. **Existing output**: Should the script overwrite, skip, or error if `<output_root>` already contains data?

## First Actions for Worker

1. **Validate inputs**: Confirm `<input_root>` exists, all organ folders present, and `organ_list.txt` is readable
2. **Parse `organ_list.txt`**: Load organ→part mapping into memory; validate against actual filesystem
3. **Extract patient roster**: Scan all organ folders to build a deduplicated set of patient IDs
4. **Deterministic split**: Assign each patient to train/test/validation using a fixed seed or sorted patient ID hash
5. **Create output skeleton**: Build `<output_root>/{train,test,validation}/` directory structure
6. **Generate symlinks**: For each patient in each split, create symlinks for all organ parts per `organ_list.txt`
7. **Validation pass**: Verify all symlinks are valid and point to existing source files

---

```json
{
  "assumptions": [
    "organ_list.txt exists at input_root and defines complete organ→part mapping",
    "Patient IDs are consistently extractable from filenames using underscore/dot delimiters",
    "All patients have entries in all organ folders (no missing organs)",
    "Output directory structure follows nnU-Net convention (exact naming TBD)",
    "Symlinks can be relative or absolute (preference not specified)",
    "Input directory remains stable after symlink creation"
  ],
  "risks": [
    "Symlinks break if source files are moved/deleted post-creation",
    "Patient ID collisions across organs could cause incorrect split assignments",
    "Incomplete part files for a patient will cause symlink creation to fail",
    "Output directory conflicts may silently overwrite or fail without explicit handling",
    "Split reproducibility depends on fixed seed; random assignment is non-deterministic",
    "Rounding behavior for 8:1:1 split on non-divisible patient counts is undefined"
  ],
  "open_questions": [
    "What is the exact format and schema of organ_list.txt?",
    "Should output follow nnU-Net naming (imagesTr/imagesTs/imagesVal) or train/test/validation?",
    "Should output filenames be transformed to nnU-Net convention or preserve source names?",
    "How should patient IDs be extracted from filenames (first token before _ or .)?",
    "How should remainders be handled in 8:1:1 split (e.g., 10 patients)?",
    "Should symlinks be relative or absolute paths?",
    "What is the error handling strategy (fail-fast, log-and-continue, dry-run)?",
    "Should the script overwrite, skip, or error if output_root already exists?"
  ]
}
```