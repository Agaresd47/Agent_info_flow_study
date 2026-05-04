# Implementation Spec: nnU-Net v2 Dataset JSON Generator

## 1. Context & Objective
The worker is to generate a Python script (or equivalent) that creates a `dataset.json` file for a specific nnU-Net v2 project configuration. The project involves training a segmentation model on lung right lower lobe data.

## 2. Input Data Structure
The worker must operate on the following directory structure, which is provided as context:
*   **Root:** `<dataset_root>/Dataset001_LungLobeRight/`
*   **Training Images:** `<dataset_root>/Dataset001_LungLobeRight/imagesTr/`
*   **Training Labels:** `<dataset_root>/Dataset001_LungLobeRight/labelsTr/`
*   **Test Images:** `<dataset_root>/Dataset001_LungLobeRight/imagesTs/` (Note: The prompt mentions this directory exists, but the request text does not explicitly state whether test data should be included in the JSON).

## 3. Configuration Parameters
*   **Modality:** DRR (Digital Radiography). The worker must map this to the standard nnU-Net modality string.
*   **Task Name:** Lung Right Lower Lobe Segmentation.
*   **Modality Name:** `lung_lower_lobe_right`.
*   **Dataset ID:** `001`.

## 4. Required Implementation Details

### 4.1. Schema Compliance (nnU-Net v2)
The worker must generate a JSON file adhering to the `dataset.json` schema. The spec must explicitly define the following fields based on the v2 standard:
*   `name`: Task name.
*   `description`: Description of the task.
*   `tensorImageSize`: Must be determined or marked as open if the input images are not standard 3D volumes (e.g., 2D slices or variable dimensions).
*   `modality`: Dictionary mapping modality keys (e.g., `0`) to the string "DRR".
*   `labels`: Dictionary mapping integer keys (e.g., `0`) to the string "lung_lower_lobe_right".
*   `numTraining`: Total number of training cases.
*   `training`: List of dictionaries containing `image` and `label` paths.
*   `test`: List of dictionaries containing `image` paths for the test set (if included).

### 4.2. File Naming & Alignment
*   **Case ID Convention:** The worker must determine the case ID format. The prompt does not specify the naming convention (e.g., `case_001`, `001`, `case1`). The worker must list this as an open question if the convention is not visible in the provided directory structure.
*   **File Extension Handling:** The worker must handle file extensions. The prompt does not specify the exact extensions (e.g., `.nii.gz`, `.nii`, `.png`). The worker must list this as an open question.

### 4.3. Path Construction
*   **Relative vs. Absolute Paths:** The prompt provides a `<dataset_root>` placeholder. The worker must decide whether to write absolute paths (using the provided placeholder) or relative paths. The spec must list this decision as an open question if not specified.
*   **Directory Traversal:** The worker must traverse the `imagesTr` and `labelsTr` directories to find files.

### 4.4. Test Set Inclusion
*   **Decision Point:** The prompt mentions the existence of `imagesTs` but the request text says "write a script to generate dataset.json" without explicitly asking to include test data. The worker must list this as an open question: "Should the `test` field in `dataset.json` be populated with paths from `imagesTs`?"

### 4.5. Write Safety
*   **Overwrite Policy:** The worker must determine the behavior if `dataset.json` already exists in the target directory. The spec must list this as an open question (e.g., overwrite, append, error, or skip).

## 5. Open Questions (To be listed in the final JSON)
1.  **File Extensions:** What are the exact file extensions for images and labels in `imagesTr` and `labelsTr`?
2.  **Case ID Format:** What is the naming convention for the case IDs (e.g., `case_001`, `001`)?
3.  **Path Format:** Should the paths in `dataset.json` be relative to the dataset root or absolute?
4.  **Test Set Inclusion:** Should the `test` field be populated with data from `imagesTs`?
5.  **Existing File Handling:** What should the script do if `dataset.json` already exists in the target directory?
6.  **Tensor Image Size:** What is the dimensionality and size of the input images (e.g., 3D volume size)?

```json
{
  "assumptions": [
    "The input directory structure `<dataset_root>/Dataset001_LungLobeRight/` exists and contains the subdirectories `imagesTr`, `labelsTr`, and `imagesTs`.",
    "The modality 'DRR' maps to the standard nnU-Net string 'DRR' in the modality dictionary.",
    "The label name 'lung_lower_lobe_right' maps to a unique integer key (e.g., 0) in the labels dictionary.",
    "The dataset ID is 001.",
    "The script will be run from a context where the dataset root is known or can be inferred."
  ],
  "risks": [
    "Incorrect file extension handling could lead to FileNotFoundError when nnU-Net tries to load the data.",
    "Misalignment between image and label filenames (e.g., different case IDs) will cause training failures.",
    "Writing absolute paths that are not resolvable on the target machine will break the pipeline.",
    "Overwriting an existing `dataset.json` without user confirmation could lose previous configuration."
  ],
  "open_questions": [
    "What are the exact file extensions for the training images and labels (e.g., .nii.gz, .png)?",
    "What is the specific naming convention for case IDs (e.g., 'case_001', '001', 'case1')?",
    "Should the `test` field in `dataset.json` be populated with paths from `imagesTs`?",
    "Should the paths in `dataset.json` be relative to the dataset root or absolute?",
    "What should the script do if `dataset.json` already exists in the target directory (overwrite, append, error, or skip)?",
    "What is the `tensorImageSize` (e.g., '3D', '2D', or specific dimensions like '128x128x128') for the input data?"
  ]
}
```