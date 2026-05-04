### Implementation Plan: `dataset.json` Generation Script for nnU-Net v2

#### Observed Facts:
- Dataset name: `Dataset001_LungLobeRight`
- Directory structure:
  - `<dataset_root>/Dataset001_LungLobeRight/imagesTr/`
  - `<dataset_root>/Dataset001_LungLobeRight/labelsTr/`
  - `<dataset_root>/Dataset001_LungLobeRight/imagesTs/`
- Task: lung right lower lobe segmentation (single-class foreground)
- Modality: DRR (not CT)
- Schema version: nnU-Net v2

---

#### Assumptions:
- All training image files in `imagesTr/` have corresponding label files in `labelsTr/`, named identically except for extension.
- Test images in `imagesTs/` are not included in the generated `dataset.json`.
- File extensions for images and labels are consistent and known (e.g., `.png`, `.nii.gz`).
- The `case_id` is derived from the filename without extension.
- The `training` key in `dataset.json` contains only entries from `imagesTr/`.

---

#### Constraints:
- The script must **not** modify or delete existing files.
- The script must **not** assume default values for schema fields unless they are clearly defined in nnU-Net v2 documentation.
- The script must **not** hardcode paths; all paths must be relative to the dataset root or configurable via input.
- The script must **not** include test cases (`imagesTs`) in the `training` list.

---

#### Risks:
- Incorrect alignment between image and label filenames may lead to mismatched entries.
- If file extensions differ between images and labels, the script will fail silently or produce invalid mappings.
- If `imagesTr` and `labelsTr` contain different numbers of files, the script should raise an error or skip unmatched pairs.
- If `dataset.json` already exists, overwriting it without confirmation could cause data loss.

---

#### Open Questions:
1. What are the exact schema fields required in the `dataset.json` for nnU-Net v2?  
   *(e.g., `name`, `description`, `reference`, `licence`, `release`, `tensorImageSize`, `modality`, `labels`, `training`, `test`)*
2. What is the expected file extension for images and labels in `imagesTr/` and `labelsTr/`?
3. Should the script validate that each image has a matching label file, and how should it handle mismatches?
4. Is there a specific naming convention for `case_id` beyond removing the file extension?
5. Are there any reserved or special characters in filenames that require escaping or handling?
6. Should the script generate a completion marker or log file after successful execution?

---

```json
{
  "assumptions": [
    "All training image files in imagesTr/ have corresponding label files in labelsTr/ with identical names except for extension.",
    "Test images in imagesTs/ are not included in the generated dataset.json.",
    "The case_id is derived from the filename without extension.",
    "File extensions for images and labels are consistent and known."
  ],
  "risks": [
    "Incorrect alignment between image and label filenames may result in mismatched entries.",
    "Mismatched or unknown file extensions may cause silent failures or invalid mappings.",
    "Overwriting an existing dataset.json without confirmation may lead to data loss.",
    "Unmatched files in imagesTr vs labelsTr may go unnoticed if not validated."
  ],
  "open_questions": [
    "What are the exact schema fields required in the dataset.json for nnU-Net v2?",
    "What is the expected file extension for images and labels in imagesTr/ and labelsTr/?",
    "Should the script validate that each image has a matching label file, and how should it handle mismatches?",
    "Is there a specific naming convention for case_id beyond removing the file extension?",
    "Are there any reserved or special characters in filenames that require escaping or handling?",
    "Should the script generate a completion marker or log file after successful execution?"
  ]
}
```