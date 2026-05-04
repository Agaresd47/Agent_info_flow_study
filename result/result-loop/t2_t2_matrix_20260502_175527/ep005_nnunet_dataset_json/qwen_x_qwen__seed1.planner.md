### Implementation Plan

#### Observed Facts:
- The dataset is structured according to nnU-Net v2 conventions.
- Dataset ID: `Dataset001_LungLobeRight`
- Directory structure includes:
  - `<dataset_root>/Dataset001_LungLobeRight/imagesTr/`
  - `<dataset_root>/Dataset001_LungLobeRight/labelsTr/`
  - `<dataset_root>/Dataset001_LungLobeRight/imagesTs/`
- The task is to generate a `dataset.json` file.
- Foreground class: `lung_lower_lobe_right`
- Modality: `DRR`

#### Assumptions:
- The directory structure is complete and consistent with nnU-Net v2 expectations.
- All training images and labels are located under `imagesTr/` and `labelsTr/`, respectively.
- Test images are located under `imagesTs/`.
- The modality key in `dataset.json` should be named `"modality"` and will contain a dictionary mapping modality names to their descriptions.
- The foreground class name (`lung_lower_lobe_right`) is used directly as the key in the `labels` dictionary.

#### Constraints:
- The script must not modify existing files unless explicitly instructed.
- The output `dataset.json` must be written to the root of the dataset folder.
- The script must not assume any specific naming convention beyond what's provided (e.g., image/label suffixes).
- No overwrite behavior is defined; if `dataset.json` already exists, the script should either fail or not proceed without confirmation.
- The schema version of `dataset.json` is assumed to match nnU-Net v2 requirements.

#### Open Questions:
- Should the script check for the existence of `imagesTr`, `labelsTr`, and `imagesTs` directories before proceeding?
- Is there a specific naming convention for image and label files (e.g., `.png`, `.nii.gz`)?
- What is the expected format for the `description` field in `dataset.json`?
- Are there any additional metadata fields required in `dataset.json` beyond those specified?
- How should the script handle cases where some files are missing or corrupted?

---

```json
{
  "assumptions": [
    "The directory structure is complete and consistent with nnU-Net v2 expectations.",
    "All training images and labels are located under imagesTr/ and labelsTr/, respectively.",
    "Test images are located under imagesTs/.",
    "The modality key in dataset.json should be named \"modality\" and will contain a dictionary mapping modality names to their descriptions.",
    "The foreground class name (lung_lower_lobe_right) is used directly as the key in the labels dictionary."
  ],
  "risks": [
    "Incorrectly generated dataset.json may cause pipeline failures during training or inference.",
    "Overwriting an existing dataset.json without confirmation could lead to loss of custom configurations.",
    "Missing or malformed image/label files might result in incomplete or invalid JSON output."
  ],
  "open_questions": [
    "Should the script check for the existence of imagesTr, labelsTr, and imagesTs directories before proceeding?",
    "Is there a specific naming convention for image and label files (e.g., .png, .nii.gz)?",
    "What is the expected format for the description field in dataset.json?",
    "Are there any additional metadata fields required in dataset.json beyond those specified?",
    "How should the script handle cases where some files are missing or corrupted?"
  ]
}
```