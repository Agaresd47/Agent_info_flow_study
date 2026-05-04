# Chat_test

This bundle is the formal 6-task `read_only` chat set after promoting the three rework tasks and switching to the 4-tier condition plan:

- `A0_strict`
- `A0_interactive`
- `A1`
- `A2`

Promoted task set:

- `t1_cxr14_subset_extraction`
- `t1_heart_mask_merge_cleanup`
- `t1_totalseg_mask_quarantine`
- `t1_code_export_zip_sanitizer`
- `t1_drr_quality_quarantine_inventory`
- `t1_nnunet_cli_inference_plan`

Canonical inputs:

- `input/chat_test_assets.yaml`
- `input/chat_test_matrix_A0_strict.yaml`
- `input/chat_test_matrix_A0_interactive.yaml`
- `input/chat_test_matrix_A1.yaml`
- `input/chat_test_matrix_A2.yaml`

Canonical run summary:

- `progressive_summary.json`

Execution policy:

1. run conditions in difficulty order
   - `A0_strict -> A0_interactive -> A1 -> A2`
2. if a `(runner, task)` cell reaches full score at a harder condition, mark the easier conditions as inherited full-score cells and skip rerunning them

Output layout:

- `output/A0_strict/`
- `output/A0_interactive/`
- `output/A1/`
- `output/A2/`

Current note:

- the progressive run executed `93` cells and short-circuited `3` cells
- the summary file records both executed cells and inherited short-circuit cells
