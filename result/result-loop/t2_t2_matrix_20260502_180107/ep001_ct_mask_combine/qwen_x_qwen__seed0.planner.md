### Implementation Plan for CT/Mask Preprocessing Worker

#### 1. **Mask Merging Logic**
- **Mathematical Semantics**:  
  For each structure type (e.g., `rib_left_*`, `rib_right_*`), combine all corresponding masks using a logical OR operation. This results in a binary mask where a voxel is 1 if it belongs to any of the structures in that group.

- **Structure File Selection**:
  - Files under `<dataset_root>/mask/<patient_id>_total/` are assumed to be named with a consistent prefix indicating their anatomical class (e.g., `rib_left_1.nii.gz`, `rib_right_2.nii.gz`).
  - The worker must parse filenames to extract structure types and group them accordingly.
  - No specific naming convention is provided; thus, how to determine which files belong to which structure group is **missing**.

#### 2. **Real-Intensity Mask Generation**
- **CT Data Integration**:
  - Use the CT image at `<dataset_root>/ct/<patient_id>.nii.gz`.
  - Replace values inside the foreground mask (from step 1) with the corresponding intensity values from the CT scan.
  - Voxels outside the foreground mask should be set to a background fill value (see below).

- **Background Fill Value**:
  - The fill value used for non-foreground voxels in real-intensity masks is **missing**.

#### 3. **Soft Tissue CT Output**
- **Foreground Definition**:
  - All merged structure masks are treated as foreground.
  - Remaining voxels (i.e., those not part of any structure) are considered soft tissue.

- **Background Fill Value**:
  - The fill value used for soft tissue CT output is **missing**.

#### 4. **Resume Capability**
- **Completion Marker**:
  - A mechanism to track whether a patient's processing has been completed is required.
  - No explicit marker format is defined; possible approaches include:
    - Writing a `.done` file per patient.
    - Using a metadata log or database entry.
  - Whether such a marker exists or needs to be created is **missing**.

- **Recovery Strategy**:
  - If a crash occurs mid-processing, the worker should check for existing outputs and skip already processed patients.
  - If partial output exists, it must not be overwritten unless explicitly allowed — no overwrite policy is specified.

#### 5. **Output Directory Structure**
- Output will be written to `<output_root>/<patient_id>/`.
- Each patient’s directory may contain:
  - Merged structure masks.
  - Real-intensity masks per structure.
  - Soft tissue CT image.

---

```json
{
  "assumptions": [
    "Each patient has exactly one CT file and one mask folder named <patient_id>_total.",
    "Mask files within a patient's mask folder follow a naming pattern that allows grouping by structure type.",
    "The CT and mask images have matching spatial resolution and orientation.",
    "All mask files are in NIfTI format (.nii.gz)."
  ],
  "risks": [
    "Incorrectly identifying structure groups due to ambiguous filename patterns could lead to wrong merges.",
    "Overwriting existing outputs without proper resume logic might cause data loss.",
    "Using incorrect background fill values can distort downstream analysis."
  ],
  "open_questions": [
    "How are structure types determined from filenames? Is there a known mapping or regex pattern?",
    "What is the expected background fill value for real-intensity masks?",
    "What is the expected background fill value for soft tissue CT output?",
    "Is there a specific completion marker or flag file used to indicate successful processing?",
    "Should the worker overwrite existing outputs or skip if they exist?"
  ]
}
```