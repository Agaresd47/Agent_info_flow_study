### Implementation Plan: Affine Alignment Worker

#### Observed Facts:
- The task involves correcting affine transformations in medical imaging data (CT scans and masks).
- Each patient has a `ct.nii.gz` file with an affine matrix.
- Other mask files in the same directory need their affines corrected to match the reference CT's affine.
- The correction process includes:
  - Using QR decomposition on the CT affine to remove rotation noise.
  - Aligning the signs of the resulting affine to match the original CT affine.
  - Applying the cleaned affine to all mask files in the same directory.

#### Assumptions:
- All input files are in NIfTI format (`*.nii.gz`).
- The directory structure is consistent per patient, with one `ct.nii.gz` and multiple mask files.
- The `ct.nii.gz` file contains a valid affine matrix.
- Mask files have corresponding spatial data that can be updated with a new affine.
- The worker will use libraries capable of reading/writing NIfTI files and performing linear algebra operations (e.g., NiBabel, NumPy).

#### Constraints:
- Must preserve the integrity of the original data; no overwrite without backup or clear flag.
- Parallel processing is required due to ~3000 patients.
- The worker must handle potential errors gracefully (e.g., missing files, invalid affine matrices).
- No modification of the `ct.nii.gz` file itself — only other mask files should be modified.

#### Risks:
- Incorrect application of affine changes may lead to misalignment between images and masks.
- Sign mismatch after QR decomposition could cause incorrect orientation if not handled carefully.
- Parallel execution introduces race conditions if not managed properly (e.g., shared resources, logging).
- If any step fails during processing, it should not halt the entire pipeline unless explicitly designed to do so.

#### Open Questions:
1. Should the worker log progress or errors to a specific output location?
2. Is there a predefined naming convention for mask files (e.g., all `.nii.gz` files except `ct.nii.gz`)?
3. Are there known edge cases where the affine matrix might be singular or degenerate?
4. How should the worker handle directories with no mask files or only `ct.nii.gz`?
5. What level of parallelism is acceptable (e.g., number of concurrent processes)?