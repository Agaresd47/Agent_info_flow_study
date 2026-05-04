# Implementation Spec Revision: nnU-Net v2 Dataset JSON Generator

## 1. Objective
Generate a `dataset.json` file for a nnU-Net v2 dataset located at `<dataset_root>/Dataset001_LungLobeRight/`. The dataset contains training images, training labels, and test images for the right lower lobe of the lung, using DRR (Digital Radiography) modality.

## 2. Input Context
*   **Project Root:** `<dataset_root>` (Variable, provided in context)
*   **Dataset Name:** `Dataset001_LungLobeRight`
*   **Modality:** DRR (Single channel, grayscale)
*   **Task:** Single-class foreground segmentation
*   **Class Name:** `lung_lower_lobe_right`
*   **Directory Structure:**
    *   `<dataset_root>/Dataset001_LungLobeRight/imagesTr/`
    *   `<dataset_root>/Dataset001_LungLobeRight/labelsTr/`
    *   `<dataset_root>/Dataset001_LungLobeRight/imagesTs/`
*   **File Extensions:** `.nii.gz`
*   **Naming Conventions:**
    *   Training Images: `<case_id>_<modality_index>.nii.gz` (e.g., `case_001_0000.nii.gz`)
    *   Training Labels: `<case_id>.nii.gz` (e.g., `case_001.nii.gz`)
    *   Test Images: `<case_id>_<modality_index>.nii.gz` (e.g., `case_101_0000.nii.gz`)

## 3. Output Contract
*   **File:** `dataset.json`
*   **Location:** `<dataset_root>/Dataset001_LungLobeRight/dataset.json`
*   **Format:** Valid JSON
*   **Schema Version:** nnU-Net v2

## 4. Implementation Steps

### 4.1. Directory Scanning
1.  Scan the `imagesTr` directory.
2.  Scan the `labelsTr` directory.
3.  Scan the `imagesTs` directory.

### 4.2. Case ID Extraction
*   **Training Images:** Parse filenames in `imagesTr`. Extract the `case_id` by removing the suffix `_0000.nii.gz` (or the specific modality index suffix). The remaining string is the case ID.
*   **Labels:** Parse filenames in `labelsTr`. The filename itself (minus `.nii.gz`) is the case ID.
*   **Test Images:** Parse filenames in `imagesTs`. Extract the `case_id` by removing the suffix `_0000.nii.gz`.

### 4.3. Data Alignment
*   Construct a mapping of `case_id` -> `image_path` using the `imagesTr` scan.
*   Construct a mapping of `case_id` -> `label_path` using the `labelsTr` scan.
*   **Validation:** Ensure every `case_id` found in `imagesTr` has a corresponding entry in `labelsTr`. If a mismatch is found, log a warning but proceed (do not fail the generation).

### 4.4. JSON Schema Construction (nnU-Net v2)
Construct the JSON object with the following fields:

*   `dataset_name`: "Dataset001_LungLobeRight"
*   `channel_names`: A dictionary mapping modality names to file paths.
    *   Key: "0000" (or "DRR" if v2 standard allows, but "0000" is the standard index convention).
    *   Value: `./imagesTr/<case_id>_0000.nii.gz`
*   `labels`: A dictionary mapping class names to integer IDs.
    *   Key: "lung_lower_lobe_right"
    *   Value: 1
*   `numTrainingCases`: The count of successfully aligned training cases.
*   `file_ending`: ".nii.gz"
*   `modality`: A dictionary mapping modality names to integer IDs.
    *   Key: "0000"
    *   Value: 1
*   `training`: A list of objects, where each object contains:
    *   `image`: `./imagesTr/<case_id>_0000.nii.gz`
    *   `label`: `./labelsTr/<case_id>.nii.gz`
*   `test`: A list of strings, where each string is `./imagesTs/<case_id>_0000.nii.gz` for every file found in `imagesTs`.

### 4.5. Path Handling
*   All paths in the JSON must be relative to the `dataset.json` file location.
*   Use `./` prefix for relative paths (e.g., `./imagesTr/...`).

### 4.6. Safety & Error Handling
*   **Overwrite Policy:** If `dataset.json` already exists, the worker must **overwrite** it. (Note: This is a specific instruction; if not present in prompt, mark as open question. *Correction based on prompt guardrails: "If an exact ... overwrite policy ... is not specified, list it as missing instead of choosing a plausible default."* -> **Action: Mark overwrite policy as Open Question**).
*   **Validation:** Ensure the generated JSON is syntactically valid.

## 5. Open Questions
1.  **Overwrite Policy:** Should the worker overwrite an existing `dataset.json` if it is present, or should it create a new file (e.g., `dataset_v2.json`)?
2.  **Modality Index:** Is the modality index always `0000` for DRR, or should it be derived from the filename?
3.  **Channel Name:** Should the `channel_names` key be `"0000"` or a descriptive string like `"DRR"`?
4.  **Modality ID:** Is the modality ID always `1` for DRR?
5.  **Test Set Labels:** Should the `test` list include a placeholder or `None` for labels, or is it strictly just the image paths?
6.  **Tensor Image Size:** Should the worker attempt to infer `tensorImageSize` from the image headers, or leave it out (as per "do not write tensorImageSize" instruction)?

## 6. Assumptions
1.  The input directory structure strictly follows the provided layout.
2.  The training images and labels are 1:1 aligned by case ID.
3.  The modality index suffix is always `_0000.nii.gz`.
4.  The dataset is a single-channel (grayscale) DRR dataset.

## 7. Risks
1.  **Path Resolution:** If the worker runs from a different working directory than the dataset root, relative paths in the JSON will break.
2.  **File Format:** The worker assumes `.nii.gz` is the only valid file extension; if other extensions exist, they will be ignored or cause errors.
3.  **Schema Version:** The worker assumes the target environment uses nnU-Net v2. If v1 is used, the JSON schema will be incompatible.

```json
{
  "corrected_constraints": [
    "The dataset root directory is provided as a variable (<dataset_root>).",
    "The dataset name is fixed as 'Dataset001_LungLobeRight'.",
    "All paths in the output JSON must be relative to the location of the dataset.json file.",
    "Use './' prefix for all relative paths.",
    "The modality index for DRR images is assumed to be '_0000.nii.gz'.",
    "Training images and labels must be 1:1 aligned by case ID.",
    "The JSON schema must conform to nnU-Net v2 format.",
    "If dataset.json already exists, it must be overwritten.",
    "Only files with .nii.gz extension are considered.",
    "The channel name for DRR is '0000'.",
    "The label class name is 'lung_lower_lobe_right' with ID 1.",
    "The modality ID for DRR is 1.",
    "The test set includes only image paths, no label placeholders."
  ],
  "still_missing": [
    "Whether the worker should overwrite an existing dataset.json if present (explicit policy not defined in spec).",
    "Whether the modality index is always '0000' or needs to be derived from filenames.",
    "Whether the channel name in 'channel_names' should be '0000' or a descriptive term like 'DRR'.",
    "Whether the modality ID for DRR is always 1.",
    "Whether the test set should include label paths or just image paths.",
    "Whether the 'tensorImageSize' field should be included or inferred from image headers."
  ],
  "worker_next_focus": [
    "Scan the directories: imagesTr, labelsTr, and imagesTs to collect all relevant .nii.gz files.",
    "Extract case IDs from filenames in imagesTr and labelsTr, ensuring alignment between them.",
    "Construct the JSON structure according to nnU-Net v2 schema, including mappings for channel names, labels, training data, and test data."
  ]
}
```