# Implementation Spec: CT Mask Combine Worker

## Overview
Process medical imaging data per patient: combine TotalSeg structure masks by category, fill with CT intensity values, and generate derived outputs. Support resumable multi-patient batch processing with speed priority.

---

## 1. Input Data Contract

### CT Images
- **Location**: `<dataset_root>/ct/<patient_id>.nii.gz`
- **Format**: NIfTI compressed
- **Assumption**: One file per patient; file exists and is readable

### Mask Files
- **Location**: `<dataset_root>/mask/<patient_id>_total/`
- **Format**: Individual `.nii.gz` files, one per TotalSeg structure
- **Naming**: Structure names embedded in filenames (exact pattern not specified)
- **Assumption**: All masks are co-registered to the corresponding CT image

---

## 2. Mask Combination Logic

### Mathematical Semantics (UNSPECIFIED)
The request mentions "combining" masks (e.g., `rib_left_*` + `rib_right_*` → single `rib` mask) but does not specify:
- **Union vs. Intersection**: Should overlapping voxels be included (union) or only doubly-masked (intersection)?
- **Priority/Ordering**: If structures overlap, which takes precedence?
- **Output Value**: Binary (0/1) or preserve source labels?

**Current assumption**: Binary union (any voxel masked in any source structure → 1 in combined mask).

### Structure Grouping Rules (UNSPECIFIED)
- **Grouping criteria**: How are individual structures mapped to categories (e.g., which files match `rib_left_*`)?
- **Grouping list**: Is there a predefined taxonomy, or should it be inferred from filename patterns?
- **Fallback**: What happens to structures that don't match any group?

**Current assumption**: Grouping is deterministic and provided externally (not inferred here).

---

## 3. Real-Intensity Mask Generation

### Definition (PARTIALLY SPECIFIED)
- **Input**: Combined binary mask + original CT image
- **Output**: 3D volume where masked voxels contain CT intensity, unmasked voxels contain a fill value
- **Fill value for unmasked voxels**: Not specified (e.g., 0, -1024, NaN, or background CT value?)

**Current assumption**: Unmasked voxels set to 0 (or specify as open question).

---

## 4. Soft-Tissue CT Output

### Definition (PARTIALLY SPECIFIED)
- **Input**: All structures combined as foreground + original CT
- **Output**: CT image where foreground voxels are replaced with soft-tissue intensity, background preserved
- **Soft-tissue intensity value**: Not specified (e.g., fixed HU value, mean of unmasked CT, or per-structure?)
- **Background fill**: How are non-foreground voxels handled? (preserve original CT, set to 0, set to air HU?)

**Current assumption**: Foreground voxels set to a fixed soft-tissue HU value (e.g., 40); background preserved from original CT.

---

## 5. Output Structure

### Directory Layout
```
<output_root>/<patient_id>/
  ├── <category_1>_mask.nii.gz          (binary combined mask)
  ├── <category_1>_real_intensity.nii.gz (intensity-filled mask)
  ├── <category_2>_mask.nii.gz
  ├── <category_2>_real_intensity.nii.gz
  ├── ...
  ├── foreground_mask.nii.gz             (union of all structures)
  ├── soft_tissue_ct.nii.gz              (CT with foreground replaced)
  └── completion_marker.txt              (or equivalent)
```

**Assumption**: One output file per category + two aggregate outputs.

---

## 6. Resumability & Completion Tracking

### Completion Marker (UNSPECIFIED)
- **Format**: How is "patient successfully processed" recorded? (e.g., sentinel file, JSON metadata, database entry?)
- **Location**: In `<output_root>/<patient_id>/` or elsewhere?
- **Atomicity**: Should marker be written only after all outputs are valid?

**Current assumption**: Completion marker is a file (e.g., `.done` or `completion_marker.txt`) written last, after all outputs.

### Resume Logic (UNSPECIFIED)
- **Partial state**: If some outputs exist but marker is absent, should they be recomputed or reused?
- **Overwrite policy**: If outputs exist and marker exists, skip patient or recompute?

**Current assumption**: Check for completion marker; if present, skip. If absent, recompute all outputs for that patient.

---

## 7. Constraints & Safety

### Write Safety
- **Destructive writes**: Outputs may overwrite existing files; no backup specified.
- **Partial failure**: If processing fails mid-patient, incomplete outputs remain; resumability depends on marker logic.

### Performance
- **Speed priority**: Implies parallel processing across patients; no concurrency model specified (threading, multiprocessing, distributed).
- **Memory**: No constraints on CT/mask size; assume in-memory processing.

### Data Integrity
- **Mask-CT alignment**: Assumes masks and CT share identical spatial dimensions and affine; no validation specified.
- **Missing structures**: If a structure file is missing, should processing fail or skip that structure?

---

## 8. First Actions for Worker

1. **Validate inputs**: Confirm CT file exists and is readable; list all mask files in `<patient_id>_total/`.
2. **Load structure grouping rules**: Obtain or infer the mapping from individual structure names to categories.
3. **Load CT and masks**: Read NIfTI files; verify spatial alignment.
4. **Check completion marker**: If present, skip patient; otherwise, proceed.
5. **Combine masks by category**: Apply union logic per group; output binary masks.
6. **Generate real-intensity masks**: Fill masked voxels with CT intensity; unmasked voxels with fill value.
7. **Generate soft-tissue CT**: Replace foreground with soft-tissue HU; preserve background.
8. **Write all outputs**: Save to `<output_root>/<patient_id>/`.
9. **Write completion marker**: Final step; signals successful processing.

---

## 9. Open Questions

See JSON block below.

---

```json
{
  "assumptions": [
    "One CT file per patient in <dataset_root>/ct/<patient_id>.nii.gz",
    "All masks for a patient are in <dataset_root>/mask/<patient_id>_total/ and are co-registered to the CT",
    "Mask combination uses binary union (any voxel masked in any source structure → 1)",
    "Unmasked voxels in real-intensity mask are set to 0",
    "Soft-tissue CT uses a fixed HU value (e.g., 40) for foreground; background preserved from original CT",
    "Completion is tracked via a sentinel file in <output_root>/<patient_id>/",
    "If completion marker exists, patient is skipped; otherwise, all outputs are recomputed",
    "Processing is per-patient; no cross-patient dependencies"
  ],
  "risks": [
    "Mask-CT spatial mismatch: no validation that masks and CT share dimensions/affine; misalignment will produce incorrect outputs",
    "Partial failure: incomplete outputs remain on disk if processing crashes; resumability depends entirely on marker logic",
    "Missing structure files: behavior undefined if a structure file is missing; could fail silently or crash",
    "Overwrite policy: existing outputs are overwritten without backup; no rollback mechanism",
    "Memory: no constraints on CT/mask size; large datasets may exhaust memory",
    "Concurrency: no model specified for parallel processing; race conditions possible if multiple workers process same patient",
    "Fill values: unspecified fill values (unmasked voxels, soft-tissue HU) may produce clinically incorrect outputs"
  ],
  "open_questions": [
    "What is the exact filename pattern for individual structure masks? (e.g., <structure_name>.nii.gz, <patient_id>_<structure_name>.nii.gz?)",
    "How is the mapping from individual structures to categories defined? (e.g., hardcoded list, external config file, regex patterns?)",
    "For mask combination, should overlapping voxels use union, intersection, or priority-based selection?",
    "What fill value should unmasked voxels have in real-intensity masks? (0, -1024, NaN, or background CT value?)",
    "What is the target HU value for soft-tissue replacement in soft-tissue CT output?",
    "How should background voxels (not in any structure) be handled in soft-tissue CT? (preserve original CT, set to air HU, or other?)",
    "What format/location should the completion marker use? (file path, content, metadata?)",
    "If a structure file is missing, should processing fail, skip that structure, or use a default mask?",
    "Should outputs be written atomically (all-or-nothing) or incrementally?",
    "Is there a predefined list of expected categories, or should the worker infer categories from filenames?",
    "What is the concurrency model for multi-patient processing? (threading, multiprocessing, distributed?)",
    "Are there memory or time limits per patient?"
  ]
}
```