### **Worker Implementation Spec**

#### **Observed Facts**
- Input data is organized into two directories:
  - `<dataset_root>/ct/` contains `.nii.gz` files named by `<patient_id>`.
  - `<dataset_root>/mask/<patient_id>_total/` contains multiple structure masks (e.g., `rib_left_1`, `rib_right_1`, etc.) for each patient.
- Output should be written under `<output_root>/<patient_id>/`.
- Each patient's CT and mask files are expected to exist in their respective locations.

---

#### **Assumptions**
1. All structure masks within a patient’s mask directory are named with consistent prefixes (e.g., `rib_left_*`, `rib_right_*`) indicating groupings.
2. The structure masks are binary (i.e., values are either 0 or 1).
3. The CT image and all structure masks have matching spatial dimensions and affine transforms.
4. The output directory structure will be created if it does not already exist.
5. The worker can read `.nii.gz` files using standard medical imaging libraries like `nibabel`.

---

#### **Constraints**
1. The worker must support resuming from partial progress — i.e., skip already-completed patients or steps.
2. The worker must handle crashes gracefully without corrupting existing outputs.
3. The worker must process one patient at a time to avoid memory issues.
4. The worker must not overwrite existing outputs unless explicitly instructed to do so.
5. The worker must ensure that the final real-intensity mask and soft tissue CT are saved in the correct format and location.

---

#### **Risks / Unsafe Choices**
1. **Overwriting existing outputs**: If a previous run failed mid-process, re-running without checking for prior output could lead to incorrect results.
2. **Incorrect grouping of structures**: Misidentifying which masks belong together may result in incorrect merged masks.
3. **Mismatched spatial alignment**: If CT and mask images do not align properly, intensity filling will produce invalid results.
4. **Memory usage during processing**: Large volumes of data may cause out-of-memory errors; batched or streaming operations are preferred.

---

#### **Open Questions**
1. What naming convention defines groups of structures? For example, how are `rib_left_*` and `rib_right_*` identified as belonging to the same category?
2. Are there any known exceptions or special cases in mask naming that require custom handling?
3. Is there a specific naming pattern or metadata file that maps structure names to categories (e.g., `rib_left_1`, `rib_left_2` → `rib`)?
4. Should the worker validate that all required input files exist before starting, or proceed with error reporting per patient?

---

```json
{
  "assumptions": [
    "Structure masks are named consistently with group identifiers.",
    "CT and mask images are aligned in space and resolution.",
    "Output directories are created automatically if missing.",
    "The worker uses standard tools for reading `.nii.gz` files."
  ],
  "risks": [
    "Overwriting previously generated outputs due to lack of resume logic.",
    "Incorrect merging of structure masks due to misidentified groupings.",
    "Misalignment between CT and mask leading to invalid intensity fills.",
    "Memory overflow when processing large volumes."
  ],
  "open_questions": [
    "How are structure masks grouped (e.g., via prefix)?",
    "Are there exceptions to the naming convention?",
    "Is there a mapping file or metadata to define structure categories?",
    "Should the worker check for existence of inputs before processing?"
  ]
}
```