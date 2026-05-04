# Implementation Spec: nnU-Net Dataset Assembly with Symlink-Based Split

## Overview
Assemble a multi-organ medical imaging dataset from pre-processed DRR images and organ-specific masks, split into train/test/validation (8:1:1), and organize via symlinks into nnU-Net directory structure.

---

## Observed Facts

1. **Input Structure**
   - Root directory contains subdirectories per organ type: `CT_no_bed/`, `Heart/`, `Lung/`, `Rib_clean/`, `Spine/`, `Bones/`
   - DRR images: `CT_no_bed/<patient_id>.jpg`
   - Organ masks: `<organ>/<patient_id>_<organ_variant>/<part>.jpg`
   - Organ-part mapping defined in `organ_list.txt` (location and format not specified)

2. **Output Structure**
   - Three split directories: `train/`, `test/`, `validation/`
   - Split ratio: 8:1:1 (80% train, 10% test, 10% validation)
   - Output uses symlinks (not copies)

3. **Multi-part Organ Handling**
   - Each organ can have multiple parts
   - Parts are stored as separate `.jpg` files within organ-specific subdirectories
   - Mapping between organs and parts is externalized in `organ_list.txt`

---

## Constraints & Risks

### **CRITICAL: Symlink Safety**
- **Risk**: Symlinks may break if source files are moved/deleted after linking
- **Risk**: Circular symlink creation if output directory is nested within input
- **Constraint**: Worker must validate that all source files exist before creating symlinks
- **Constraint**: Worker must handle symlink creation atomically or with rollback capability

### **Data Integrity**
- **Risk**: Patient ID extraction from filenames is fragile (underscore-delimited, but exact format unclear)
- **Risk**: Duplicate patient IDs across organs could cause silent overwrites in output structure
- **Constraint**: Worker must detect and report naming collisions before proceeding

### **Split Determinism**
- **Risk**: 8:1:1 split on non-integer patient counts will have remainder handling ambiguity
- **Constraint**: Worker must document how remainders are assigned (e.g., to train, or distributed)
- **Constraint**: Worker must use a seeded random process if reproducibility is required

### **File Organization**
- **Risk**: nnU-Net convention for multi-part organs is not specified (flat list? subdirectories? concatenated?)
- **Risk**: Naming collision between DRR images and mask files in output
- **Constraint**: Worker must clarify output naming scheme before symlinking

---

## Assumptions

1. `organ_list.txt` is a text file in the input root, with one organ per line or a structured format (exact schema assumed to be clarified)
2. Patient IDs are consistently extractable from filenames (e.g., `<patient_id>` is the first component before `_`)
3. All `.jpg` files in organ subdirectories are valid mask parts; no filtering by filename pattern is needed
4. Symlinks should point to absolute or relative paths (policy not specified; assumed relative for portability)
5. Output directory structure is flat per split (no nested organ subdirectories in output)
6. No existing files in output directories; behavior on collision not specified

---

## Missing Information (Open Questions)

### **organ_list.txt Format**
- Location: Is it at `<input_root>/organ_list.txt` or elsewhere?
- Schema: One organ per line? JSON? CSV? Mapping of organ→parts?
- Example content needed to validate parsing logic

### **Patient ID Extraction**
- Exact delimiter and position in filenames (e.g., is `<patient_id>` always the prefix before first `_`?)
- Are patient IDs guaranteed unique across all organs?
- Should patient IDs be validated against a whitelist?

### **Output Directory Naming Convention**
- nnU-Net expects specific naming (e.g., `imagesTr/`, `labelsTr/`, `imagesTs/`, `labelsTs/`)?
- Or flat structure with split-based subdirectories?
- How should multi-part masks be named/organized in output? (e.g., `<patient_id>_<organ>_<part>.jpg` or `<patient_id>_<part>.jpg`?)

### **Symlink Strategy**
- Absolute or relative paths?
- Should symlinks be validated after creation?
- Behavior if source file is deleted after symlink creation?

### **Split Remainder Handling**
- If total patient count is not divisible by 10, how are remainders assigned?
- Should split be deterministic (seeded) or random?
- Is a split log/manifest required for reproducibility?

### **Error Handling & Rollback**
- If symlink creation fails partway through, should the worker clean up partial output?
- Should the worker create a checkpoint/manifest to resume from failure?

### **Validation & Reporting**
- Should the worker verify that all source files exist before starting?
- Should output include a manifest of created symlinks?
- Should the worker report statistics (e.g., files per split, organs per patient)?

---

## Recommended First Actions

1. **Validate Input**
   - Confirm `organ_list.txt` exists and parse its format
   - Enumerate all patient IDs from `CT_no_bed/` and organ directories
   - Detect and report any naming collisions or malformed filenames

2. **Plan Output Structure**
   - Clarify nnU-Net directory naming with stakeholder
   - Define symlink naming scheme for multi-part organs
   - Decide on absolute vs. relative symlink paths

3. **Implement Split Logic**
   - Define remainder handling for 8:1:1 split
   - Implement seeded random assignment if reproducibility required
   - Generate split manifest before creating symlinks

4. **Create Symlinks Safely**
   - Validate all source files exist
   - Create output directories
   - Create symlinks with error handling and logging
   - Verify symlink integrity post-creation

---

```json
{
  "assumptions": [
    "organ_list.txt is located at <input_root>/organ_list.txt",
    "Patient IDs are consistently extractable as the first underscore-delimited component of filenames",
    "Patient IDs are globally unique across all organs",
    "All .jpg files in organ subdirectories are valid mask parts requiring no additional filtering",
    "Output directory structure is flat per split (no nested organ subdirectories)",
    "No existing files in output directories; collision behavior undefined",
    "Symlinks should be created (not file copies)",
    "nnU-Net directory naming follows standard convention (imagesTr, labelsTr, imagesTs, labelsTs, imagesVal, labelsVal) or is clarified separately"
  ],
  "risks": [
    "CRITICAL: Symlinks will break if source files are moved/deleted after creation; no validation of source persistence",
    "CRITICAL: Symlink creation is not atomic; partial failure could leave inconsistent state",
    "Patient ID extraction from filenames is fragile; underscore-delimited format not formally specified",
    "Duplicate patient IDs across organs could cause silent overwrites in output structure",
    "8:1:1 split on non-integer patient counts has undefined remainder handling",
    "nnU-Net output naming convention for multi-part organs is not specified (flat list vs. subdirectories vs. concatenation)",
    "Naming collision between DRR images and mask files in output is possible but unaddressed",
    "No rollback or checkpoint mechanism specified for partial failures",
    "Reproducibility of split assignment depends on seeding policy, which is not specified"
  ],
  "open_questions": [
    "What is the exact format and location of organ_list.txt? (one organ per line? JSON? CSV? Does it map organ→parts?)",
    "What is the exact patient ID extraction rule? (e.g., prefix before first underscore? validated against a list?)",
    "What is the nnU-Net output directory naming convention? (imagesTr/labelsTr/imagesTs/labelsTs/imagesVal/labelsVal?)",
    "How should multi-part masks be named/organized in output? (e.g., <patient_id>_<organ>_<part>.jpg or <patient_id>_<part>.jpg?)",
    "Should symlinks use absolute or relative paths?",
    "How should 8:1:1 split remainders be handled if total patient count is not divisible by 10?",
    "Should split assignment be deterministic (seeded) or random?",
    "Is a split manifest or checkpoint file required for reproducibility or resumption?",
    "What is the policy for handling symlink creation failures? (rollback? partial output? error log?)",
    "Should the worker validate source file existence before creating symlinks?",
    "Should output include a manifest of created symlinks and split statistics?"
  ]
}
```